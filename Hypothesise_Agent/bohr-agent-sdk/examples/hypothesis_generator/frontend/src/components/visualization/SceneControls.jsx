import React from 'react'
import {
  RotateCcw, Grid, Compass, ArrowUpRight, Maximize, Minimize,
  ZoomIn, ZoomOut, Maximize2, Minimize2, Eye
} from 'lucide-react'

export function SceneControls({
  showGrid,
  showAxes,
  showVectors,
  isFullscreen,
  isExpanded,
  hasVectors = true,
  onToggleGrid,
  onToggleAxes,
  onToggleVectors,
  onResetCamera,
  onToggleFullscreen,
  onToggleExpand,
  onZoomIn,
  onZoomOut,
}) {
  return (
    <div className="vis-scene-controls-toolbar">
      {/* Zoom In & Zoom Out Controls */}
      {onZoomIn && (
        <button
          type="button"
          className="vis-toolbar-btn"
          title="Zoom In (or use Mouse Wheel)"
          onClick={onZoomIn}
        >
          <ZoomIn size={14} />
          <span>Zoom +</span>
        </button>
      )}
      {onZoomOut && (
        <button
          type="button"
          className="vis-toolbar-btn"
          title="Zoom Out (or use Mouse Wheel)"
          onClick={onZoomOut}
        >
          <ZoomOut size={14} />
          <span>Zoom -</span>
        </button>
      )}

      {/* Reset Camera View */}
      <button
        type="button"
        className="vis-toolbar-btn"
        title="Reset Camera View to Origin"
        onClick={onResetCamera}
      >
        <RotateCcw size={13} />
        <span>Reset View</span>
      </button>

      {/* Toggle Grid */}
      <button
        type="button"
        className={`vis-toolbar-btn ${showGrid ? 'is-active' : ''}`}
        title="Toggle Ground Grid"
        onClick={onToggleGrid}
      >
        <Grid size={13} />
        <span>Grid</span>
      </button>

      {/* Toggle Coordinate Axes */}
      <button
        type="button"
        className={`vis-toolbar-btn ${showAxes ? 'is-active' : ''}`}
        title="Toggle XYZ Axes"
        onClick={onToggleAxes}
      >
        <Compass size={13} />
        <span>Axes</span>
      </button>

      {/* Toggle Force / Velocity Vectors */}
      {hasVectors && (
        <button
          type="button"
          className={`vis-toolbar-btn ${showVectors ? 'is-active' : ''}`}
          title="Toggle Physical Vectors"
          onClick={onToggleVectors}
        >
          <ArrowUpRight size={13} />
          <span>Vectors</span>
        </button>
      )}

      {/* Expand / Theater Mode Toggle */}
      {onToggleExpand && (
        <button
          type="button"
          className={`vis-toolbar-btn ${isExpanded ? 'is-active' : ''}`}
          title={isExpanded ? 'Restore Standard Layout' : 'Expand 3D Viewport to Maximum Size'}
          onClick={onToggleExpand}
          style={{
            borderColor: isExpanded ? '#38bdf8' : undefined,
            color: isExpanded ? '#38bdf8' : undefined,
          }}
        >
          {isExpanded ? <Minimize size={13} /> : <Maximize size={13} />}
          <span>{isExpanded ? 'Collapse' : 'Expand 3D'}</span>
        </button>
      )}

      {/* Fullscreen Toggle */}
      <button
        type="button"
        className={`vis-toolbar-btn ${isFullscreen ? 'is-active' : ''}`}
        title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen (Edge-to-Edge)'}
        onClick={onToggleFullscreen}
      >
        {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        <span>{isFullscreen ? 'Exit' : 'Fullscreen'}</span>
      </button>
    </div>
  )
}


