import React, { useState, useEffect } from 'react'
import {
  Sparkles, Eye, Cpu, Database, CheckCircle2, AlertCircle,
  RefreshCw, Globe, Shield, Zap, ExternalLink, Image as ImageIcon, ChevronRight
} from 'lucide-react'
import {
  streamVisualizationPipeline,
  runVisualizationPipeline,
  fetchModelStatus,
  fetchReferenceSources
} from '../../services/apiClient'

const STAGE_DEFINITIONS = [
  { id: 'refining_prompt', label: '1. Prompt Refinement & Stop Words', model: 'Qwen 4B Thinking', icon: Sparkles },
  { id: 'reference_selected', label: '2. Open Reference Search', model: 'Free Search Adapter', icon: Globe },
  { id: 'image_in_ram', label: '3. Temporary RAM Acquisition', model: 'Zero-Disk Buffer', icon: Shield },
  { id: 'loading_vision_model', label: '4. Sequential VRAM Switch', model: 'LM Studio Lifecycle', icon: RefreshCw },
  { id: 'analyzing_image', label: '5. Visual Structure & Joints', model: 'Qwen3-VL-2B', icon: Eye },
  { id: 'releasing_image_buffers', label: '6. Purge RAM & Unload Vision', model: 'Memory Cleanup', icon: Database },
  { id: 'loading_main_model', label: '7. Load Reasoning Model', model: 'LM Studio Lifecycle', icon: RefreshCw },
  { id: 'synthesizing_scene', label: '8. 3D Scene Specification', model: 'DeepSeek R1 7B', icon: Cpu },
  { id: 'complete', label: '9. 3D WebGL Visualization', model: 'React Three Fiber', icon: CheckCircle2 },
]

export default function MultiModelPipelinePanel({
  topic,
  domain,
  onPipelineComplete,
  compact = false,
  onToggleCompact,
}) {
  const [isRunning, setIsRunning] = useState(false)
  const [customRefUrl, setCustomRefUrl] = useState('')
  const [currentStageId, setCurrentStageId] = useState('')
  const [events, setEvents] = useState([])
  const [modelTelemetry, setModelTelemetry] = useState(null)
  const [referenceSources, setReferenceSources] = useState(null)
  const [pipelineResult, setPipelineResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [isMinimized, setIsMinimized] = useState(compact)

  // Sync internal minimized state with prop
  useEffect(() => {
    setIsMinimized(compact)
  }, [compact])

  // Poll model telemetry on mount and when running
  useEffect(() => {
    let mounted = true
    const updateStatus = async () => {
      const status = await fetchModelStatus()
      if (mounted) setModelTelemetry(status)
    }
    updateStatus()
    const timer = setInterval(updateStatus, isRunning ? 3000 : 8000)
    return () => {
      mounted = false
      clearInterval(timer)
    }
  }, [isRunning])

  useEffect(() => {
    fetchReferenceSources().then(setReferenceSources).catch(() => {})
  }, [])

  const handleStartPipeline = async () => {
    if (isRunning) return
    setIsRunning(true)
    setErrorMsg(null)
    setEvents([])
    setPipelineResult(null)
    setCurrentStageId('refining_prompt')
    setExpanded(true)

    try {
      // Use SSE streaming for real-time stage updates
      const response = await streamVisualizationPipeline(
        topic || 'Interactive scientific experiment simulation',
        domain || undefined,
        customRefUrl.trim() || undefined
      )

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep trailing incomplete chunk

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const data = JSON.parse(trimmed.slice(6))
            if (data.type === 'progress') {
              setCurrentStageId(data.stage)
              setEvents((prev) => [...prev, data])
            } else if (data.type === 'complete') {
              setPipelineResult(data.result)
              setCurrentStageId('complete')
              if (onPipelineComplete && data.result) {
                // Pass new scene specification and simulation data upward
                onPipelineComplete(data.result)
              }
            } else if (data.type === 'error') {
              setErrorMsg(data.message)
            }
          } catch (e) {
            // ignore JSON parse errors in stream
          }
        }
      }
    } catch (err) {
      console.warn('Streaming pipeline error, falling back to sync endpoint:', err)
      try {
        const res = await runVisualizationPipeline(
          topic || 'Interactive scientific experiment simulation',
          domain || undefined,
          customRefUrl.trim() || undefined
        )
        if (res.success) {
          setPipelineResult(res)
          setEvents(res.timeline_events || [])
          setCurrentStageId('complete')
          if (onPipelineComplete) onPipelineComplete(res)
        } else {
          setErrorMsg(res.error || 'Pipeline execution failed')
        }
      } catch (fallbackErr) {
        setErrorMsg(fallbackErr.message)
      }
    } finally {
      setIsRunning(false)
    }
  }

  const activeModelDisplay = () => {
    if (!modelTelemetry) return 'Connecting...'
    const loaded = modelTelemetry.loaded_instances || {}
    const keys = Object.keys(loaded)
    if (keys.length === 0) return 'None (VRAM Free)'
    return keys[0]
  }

  const selectedRef = pipelineResult?.selected_reference
  const visualInstr = pipelineResult?.visual_reconstruction_instructions

  if (isMinimized) {
    return (
      <div
        className="multi-model-pipeline-card is-compact"
        style={{
          background: 'linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9))',
          border: '1px solid rgba(139, 92, 246, 0.3)',
          borderRadius: '8px',
          padding: '6px 14px',
          marginBottom: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="#c084fc" />
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f8fafc' }}>
            3-Model Vision Pipeline:
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: modelTelemetry?.status === 'online' ? '#22c55e' : '#ef4444',
                display: 'inline-block',
              }}
            />
            {activeModelDisplay()}
          </span>
          {currentStageId && currentStageId !== 'complete' && (
            <span style={{ fontSize: '0.72rem', color: '#a78bfa', marginLeft: '6px' }}>
              • {currentStageId.replace(/_/g, ' ')}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            onClick={handleStartPipeline}
            disabled={isRunning}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              background: isRunning ? 'rgba(100, 116, 139, 0.4)' : 'linear-gradient(135deg, #7c3aed, #2563eb)',
              border: '1px solid #8b5cf6',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: isRunning ? 'wait' : 'pointer',
            }}
          >
            {isRunning ? <RefreshCw size={12} className="spinner-rotate" /> : <Zap size={12} />}
            <span>{isRunning ? 'Sequencing...' : 'Run Pipeline'}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setIsMinimized(false)
              if (onToggleCompact) onToggleCompact(false)
            }}
            style={{
              padding: '4px 8px',
              background: 'rgba(51, 65, 85, 0.5)',
              border: '1px solid rgba(100, 116, 139, 0.4)',
              borderRadius: '6px',
              color: '#cbd5e1',
              fontSize: '0.72rem',
              cursor: 'pointer',
            }}
            title="Expand Full Pipeline Monitor"
          >
            Expand Panel ▾
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className="multi-model-pipeline-card"
      style={{
        background: 'linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9))',
        border: '1px solid rgba(139, 92, 246, 0.4)',
        borderRadius: '12px',
        padding: '12px 18px',
        marginBottom: '12px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
      }}
    >
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={18} color="#fff" />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.94rem', fontWeight: 600, color: '#f8fafc' }}>
              Multi-Model Vision-Assisted 3D Pipeline
            </h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '2px', fontSize: '0.73rem', color: '#94a3b8' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: modelTelemetry?.status === 'online' ? '#22c55e' : '#ef4444',
                    display: 'inline-block',
                  }}
                />
                LM Studio: {modelTelemetry?.status || 'offline'}
              </span>
              <span>•</span>
              <span>GPU Active: <strong style={{ color: '#cbd5e1' }}>{activeModelDisplay()}</strong></span>
              <span>•</span>
              <span style={{ color: '#a78bfa' }}>Single Active Model Policy Enforced</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            style={{
              padding: '5px 10px',
              background: 'rgba(51, 65, 85, 0.6)',
              border: '1px solid rgba(100, 116, 139, 0.4)',
              borderRadius: '6px',
              color: '#cbd5e1',
              fontSize: '0.78rem',
              cursor: 'pointer',
            }}
          >
            {expanded ? 'Hide Details' : 'Inspect Pipeline'}
          </button>
          <button
            type="button"
            onClick={() => {
              setIsMinimized(true)
              if (onToggleCompact) onToggleCompact(true)
            }}
            style={{
              padding: '5px 8px',
              background: 'rgba(51, 65, 85, 0.6)',
              border: '1px solid rgba(100, 116, 139, 0.4)',
              borderRadius: '6px',
              color: '#94a3b8',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
            title="Minimize to Compact Bar"
          >
            Minimize ▴
          </button>
          <button
            type="button"
            onClick={handleStartPipeline}
            disabled={isRunning}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 18px',
              background: isRunning
                ? 'rgba(100, 116, 139, 0.4)'
                : 'linear-gradient(135deg, #7c3aed, #2563eb)',
              border: '1px solid #8b5cf6',
              borderRadius: '8px',
              color: '#ffffff',
              fontSize: '0.84rem',
              fontWeight: 600,
              cursor: isRunning ? 'wait' : 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: isRunning ? 'none' : '0 0 16px rgba(124, 58, 237, 0.4)',
            }}
          >
            {isRunning ? (
              <>
                <RefreshCw size={14} className="spinner-rotate" />
                <span>Sequencing Models...</span>
              </>
            ) : (
              <>
                <Zap size={14} />
                <span>Run 3-Model 3D Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Expanded controls & progress */}
      {expanded && (
        <div style={{ marginTop: '16px', borderTop: '1px solid rgba(51, 65, 85, 0.6)', paddingTop: '16px' }}>
          {/* Optional Reference URL Input */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>
              Optional Reference Image/Diagram URL:
            </span>
            <input
              type="url"
              placeholder="https://commons.wikimedia.org/... (Leave blank for autonomous Qwen search)"
              value={customRefUrl}
              onChange={(e) => setCustomRefUrl(e.target.value)}
              disabled={isRunning}
              style={{
                flex: 1,
                padding: '6px 12px',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(71, 85, 105, 0.5)',
                borderRadius: '6px',
                color: '#e2e8f0',
                fontSize: '0.8rem',
              }}
            />
            {customRefUrl && (
              <button
                type="button"
                onClick={() => setCustomRefUrl('')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Sequential Stage Progress Flow */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '8px',
              marginBottom: '16px',
            }}
          >
            {STAGE_DEFINITIONS.map((stage, idx) => {
              const Icon = stage.icon
              const isCurrent = currentStageId === stage.id
              const isPast = events.some((e) => e.stage === stage.id) || (currentStageId === 'complete')
              return (
                <div
                  key={stage.id}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: isCurrent
                      ? 'rgba(139, 92, 246, 0.25)'
                      : isPast
                      ? 'rgba(34, 197, 94, 0.12)'
                      : 'rgba(30, 41, 59, 0.5)',
                    border: `1px solid ${
                      isCurrent
                        ? '#8b5cf6'
                        : isPast
                        ? 'rgba(34, 197, 94, 0.4)'
                        : 'rgba(51, 65, 85, 0.5)'
                    }`,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, color: isCurrent ? '#a78bfa' : isPast ? '#86efac' : '#94a3b8' }}>
                      {stage.label}
                    </span>
                    <Icon size={12} color={isCurrent ? '#c084fc' : isPast ? '#4ade80' : '#64748b'} />
                  </div>
                  <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                    {stage.model}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Live Progress Messages Log */}
          {events.length > 0 && (
            <div
              style={{
                background: 'rgba(10, 15, 30, 0.75)',
                border: '1px solid rgba(51, 65, 85, 0.4)',
                borderRadius: '8px',
                padding: '10px 14px',
                maxHeight: '140px',
                overflowY: 'auto',
                fontSize: '0.76rem',
                fontFamily: 'monospace',
                color: '#cbd5e1',
                marginBottom: '14px',
              }}
            >
              {events.map((ev, i) => (
                <div key={i} style={{ marginBottom: '4px', display: 'flex', gap: '8px' }}>
                  <span style={{ color: '#818cf8' }}>[{ev.timestamp || '0.0'}s]</span>
                  <span style={{ color: '#f1f5f9' }}>{ev.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* Error Message banner */}
          {errorMsg && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '6px',
                color: '#fca5a5',
                fontSize: '0.8rem',
                marginBottom: '14px',
              }}
            >
              <AlertCircle size={14} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Reference Attribution & Reconstruction Summary */}
          {selectedRef && (
            <div
              style={{
                background: 'rgba(30, 41, 59, 0.7)',
                border: '1px solid rgba(71, 85, 105, 0.5)',
                borderRadius: '8px',
                padding: '12px 14px',
                fontSize: '0.8rem',
                color: '#cbd5e1',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                  Selected Visual Reference: {selectedRef.source_name || 'Open Scientific'}
                </span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: 'rgba(34, 197, 94, 0.2)',
                    color: '#86efac',
                    border: '1px solid rgba(34, 197, 94, 0.4)',
                  }}
                >
                  License: {selectedRef.license || 'Public Domain / CC'}
                </span>
              </div>
              <p style={{ margin: '0 0 6px 0', fontSize: '0.76rem', color: '#94a3b8' }}>
                Relevance: {selectedRef.relevance_reason}
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b', fontStyle: 'italic' }}>
                🛡️ Privacy &amp; Copyright Compliance: Reference image was loaded into RAM buffer only, analyzed by Qwen3-VL, and immediately purged from memory. Zero permanent image files were created.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

