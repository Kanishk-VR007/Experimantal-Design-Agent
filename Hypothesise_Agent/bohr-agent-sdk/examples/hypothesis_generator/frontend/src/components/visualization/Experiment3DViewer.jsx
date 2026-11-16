import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Maximize, Minimize, Maximize2, Minimize2 } from 'lucide-react'
import { validateSceneSpecification } from '../../visualization/sceneSchema'
import { AnimationController } from '../../visualization/animationController'
import { getTemplateMeta } from '../../visualization/sceneRegistry'
import { ExperimentScene } from './ExperimentScene'
import { ExperimentTimeline } from './ExperimentTimeline'
import { ParameterControls } from './ParameterControls'
import { MeasurementOverlay } from './MeasurementOverlay'
import { SceneControls } from './SceneControls'
import { VisualizationFallback } from './VisualizationFallback'
import './Experiment3DViewer.css'

export function Experiment3DViewer({
  visualizationSpec,
  domain,
  topic,
  procedure,
  onSimulationUpdated,
  isExpanded,
  onToggleExpand,
}) {
  // Validate specification
  const validationResult = useMemo(
    () => validateSceneSpecification(visualizationSpec),
    [visualizationSpec]
  )

  const spec = validationResult.valid ? validationResult.spec : null
  const templateMeta = useMemo(() => getTemplateMeta(spec?.scene_template), [spec?.scene_template])

  // Animation state
  const animationController = useMemo(
    () => (spec?.animation ? new AnimationController(spec.animation) : null),
    [spec?.animation]
  )

  const duration = spec?.animation?.duration_s || 0
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0)
  const [loop, setLoop] = useState(true)

  // Viewport / Camera controls
  const [showGrid, setShowGrid] = useState(true)
  const [showAxes, setShowAxes] = useState(true)
  const [showVectors, setShowVectors] = useState(true)
  const [resetCameraTrigger, setResetCameraTrigger] = useState(0)
  const [zoomTrigger, setZoomTrigger] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [internalExpanded, setInternalExpanded] = useState(false)
  const [showParamsInViewer, setShowParamsInViewer] = useState(false)

  const effectiveExpanded = isExpanded !== undefined ? isExpanded : internalExpanded

  const handleToggleExpand = () => {
    if (onToggleExpand) {
      onToggleExpand(!effectiveExpanded)
    } else {
      setInternalExpanded((prev) => !prev)
    }
  }

  const handleZoomIn = () => setZoomTrigger((prev) => (prev > 0 ? prev + 1 : 1))
  const handleZoomOut = () => setZoomTrigger((prev) => (prev < 0 ? prev - 1 : -1))

  // Object picking & tooltips
  const [hoveredObject, setHoveredObject] = useState(null)
  const [selectedObjectId, setSelectedObjectId] = useState(null)

  // Parameter update loading state
  const [isUpdatingParams, setIsUpdatingParams] = useState(false)

  const containerRef = useRef(null)
  const animFrameRef = useRef(null)
  const lastTimeRef = useRef(null)

  // Initialize playback on mount or when spec changes
  useEffect(() => {
    setCurrentTime(0)
    if (spec?.animation?.has_animation && duration > 0) {
      setIsPlaying(true)
    } else {
      setIsPlaying(false)
    }
  }, [spec, duration])

  // Animation Clock Loop
  useEffect(() => {
    if (!isPlaying || duration <= 0) {
      lastTimeRef.current = null
      return
    }

    const tick = (timestamp) => {
      if (lastTimeRef.current === null) {
        lastTimeRef.current = timestamp
      }
      const dt = (timestamp - lastTimeRef.current) / 1000.0
      lastTimeRef.current = timestamp

      setCurrentTime((prev) => {
        let next = prev + dt * playbackSpeed
        if (next >= duration) {
          if (loop) {
            next = 0
          } else {
            next = duration
            setIsPlaying(false)
          }
        }
        return next
      })

      animFrameRef.current = requestAnimationFrame(tick)
    }

    animFrameRef.current = requestAnimationFrame(tick)

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [isPlaying, duration, playbackSpeed, loop])

  // Timeline handlers
  const handlePlayPause = () => {
    setIsPlaying((prev) => !prev)
  }

  const handleReset = () => {
    setCurrentTime(0)
  }

  const handleScrub = (time) => {
    setCurrentTime(Math.max(0, Math.min(time, duration)))
  }

  const handleStep = (delta) => {
    setCurrentTime((prev) => Math.max(0, Math.min(prev + delta, duration)))
  }

  const handleResetCamera = () => {
    setResetCameraTrigger((prev) => prev + 1)
  }

  const handleToggleFullscreen = () => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {})
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {})
    }
  }

  // Handle Fullscreen change event from browser escape
  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement))
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    return () => document.removeEventListener('fullscreenchange', handleFsChange)
  }, [])

  // Live Parameter Modification & Synchronization with Backend
  const handleUpdateParameters = async (updatedValues) => {
    setIsUpdatingParams(true)
    try {
      const response = await fetch('/api/visualization/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          experiment_id: spec?.experiment_id || 'experiment',
          domain: spec?.domain || domain || 'general',
          parameters: updatedValues,
          current_procedure: procedure || null,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`)
      }

      const data = await response.json()
      if (data.success && data.simulation) {
        if (onSimulationUpdated) {
          onSimulationUpdated(data.simulation)
        }
      }
    } catch (err) {
      console.error('Parameter update failed:', err)
      alert(`Could not update parameters: ${err.message}`)
    } finally {
      setIsUpdatingParams(false)
    }
  }

  // Fallback state
  if (!validationResult.valid || !spec) {
    return (
      <VisualizationFallback
        domain={domain}
        reason={validationResult.error}
        onRetry={async () => {
          try {
            const resp = await fetch('/api/visualization/generate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                topic: topic || 'Custom Experiment',
                procedure: procedure || {},
              }),
            })
            const data = await resp.json()
            if (data.visualization_spec && onSimulationUpdated) {
              onSimulationUpdated((prev) => ({
                ...prev,
                visualization_spec: data.visualization_spec,
              }))
            }
          } catch (e) {
            console.error('Fallback generation error:', e)
          }
        }}
      />
    )
  }

  return (
    <div
      ref={containerRef}
      className={`experiment-3d-viewer-container ${isFullscreen ? 'is-fullscreen' : ''} ${effectiveExpanded ? 'is-expanded' : ''}`}
    >
      {/* Top Header Bar */}
      <div className="vis-top-bar">
        <div className="vis-title-group">
          <span className="vis-title-icon">{templateMeta.icon}</span>
          <div>
            <h3 className="vis-title-text">{spec.title || '3D Scientific Experiment Simulation'}</h3>
            <span className="vis-template-tag">{spec.scene_template}</span>
          </div>
        </div>
        <div className="vis-top-bar-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            className="vis-header-action-btn"
            onClick={handleToggleExpand}
            title={effectiveExpanded ? "Minimize Studio View" : "Expand 3D Studio (Maximize Inspection Viewport)"}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              background: effectiveExpanded ? 'rgba(56, 189, 248, 0.2)' : 'rgba(30, 41, 59, 0.8)',
              border: effectiveExpanded ? '1px solid #38bdf8' : '1px solid #475569',
              borderRadius: '6px',
              color: effectiveExpanded ? '#38bdf8' : '#f1f5f9',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {effectiveExpanded ? <Minimize size={13} /> : <Maximize size={13} />}
            <span>{effectiveExpanded ? 'Standard View' : 'Expand 3D Studio'}</span>
          </button>
          <button
            type="button"
            className="vis-header-action-btn"
            onClick={handleToggleFullscreen}
            title={isFullscreen ? "Exit Fullscreen" : "True Fullscreen Mode"}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid #475569',
              borderRadius: '6px',
              color: '#94a3b8',
              fontSize: '0.78rem',
              cursor: 'pointer',
            }}
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Main 3D Viewport with HUD Overlays */}
      <div className="vis-viewport-area">
        <ExperimentScene
          spec={spec}
          currentTime={currentTime}
          animationController={animationController}
          showGrid={showGrid}
          showAxes={showAxes}
          showVectors={showVectors}
          resetCameraTrigger={resetCameraTrigger}
          zoomTrigger={zoomTrigger}
          onObjectHover={setHoveredObject}
          onObjectClick={(obj) => setSelectedObjectId(obj?.id || null)}
          selectedObjectId={selectedObjectId}
        />

        {/* Floating Telemetry & Measurement Badges */}
        <MeasurementOverlay
          overlays={spec.measurement_overlays}
          currentTime={currentTime}
          animationController={animationController}
          hoveredObject={hoveredObject}
          templateMeta={templateMeta}
          isSimulationBacked={spec.is_simulation_backed}
        />

        {/* Scene Navigation & Toggle Controls */}
        <SceneControls
          showGrid={showGrid}
          showAxes={showAxes}
          showVectors={showVectors}
          isFullscreen={isFullscreen}
          isExpanded={effectiveExpanded}
          hasVectors={Boolean(spec.vectors && spec.vectors.length > 0)}
          onToggleGrid={() => setShowGrid((p) => !p)}
          onToggleAxes={() => setShowAxes((p) => !p)}
          onToggleVectors={() => setShowVectors((p) => !p)}
          onResetCamera={handleResetCamera}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onToggleFullscreen={handleToggleFullscreen}
          onToggleExpand={handleToggleExpand}
        />
      </div>

      {/* Timeline Scrubber Bar */}
      {duration > 0 && (
        <ExperimentTimeline
          currentTime={currentTime}
          duration={duration}
          isPlaying={isPlaying}
          playbackSpeed={playbackSpeed}
          loop={loop}
          onPlayPause={handlePlayPause}
          onReset={handleReset}
          onScrub={handleScrub}
          onStep={handleStep}
          onChangeSpeed={setPlaybackSpeed}
          onToggleLoop={() => setLoop((p) => !p)}
        />
      )}

      {/* Live Physical Parameter Controls - Collapsible to prevent squeezing 3D canvas */}
      {spec.parameters && spec.parameters.length > 0 && (
        <div className="vis-inline-parameters-container">
          <div style={{ padding: '6px 12px', background: 'rgba(15, 23, 42, 0.9)', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'center' }}>
            <button
              type="button"
              onClick={() => setShowParamsInViewer((p) => !p)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.74rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>{showParamsInViewer ? 'Hide Inline Parameters ▴' : 'Show Inline Parameters ▾'}</span>
            </button>
          </div>
          {showParamsInViewer && (
            <ParameterControls
              parameters={spec.parameters}
              onUpdateParameters={handleUpdateParameters}
              isUpdating={isUpdatingParams}
            />
          )}
        </div>
      )}
    </div>
  )
}

export default Experiment3DViewer

