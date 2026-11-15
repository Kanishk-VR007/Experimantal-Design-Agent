import React from 'react'

export function SceneControls({
  showGrid,
  showAxes,
  showVectors,
  isFullscreen,
  hasVectors = true,
  onToggleGrid,
  onToggleAxes,
  onToggleVectors,
  onResetCamera,
  onToggleFullscreen,
}) {
  return (
    <div className="vis-scene-controls-toolbar">
      {/* Reset Camera */}
      <button
        className="vis-toolbar-btn"
        title="Reset Camera View"
        onClick={onResetCamera}
      >
        🎯 Reset View
      </button>

      {/* Toggle Grid */}
      <button
        className={`vis-toolbar-btn ${showGrid ? 'is-active' : ''}`}
        title="Toggle Ground Grid"
        onClick={onToggleGrid}
      >
        📐 Grid
      </button>

      {/* Toggle Coordinate Axes */}
      <button
        className={`vis-toolbar-btn ${showAxes ? 'is-active' : ''}`}
        title="Toggle XYZ Axes"
        onClick={onToggleAxes}
      >
        🧭 Axes
      </button>

      {/* Toggle Force / Velocity Vectors */}
      {hasVectors && (
        <button
          className={`vis-toolbar-btn ${showVectors ? 'is-active' : ''}`}
          title="Toggle Physical Vectors"
          onClick={onToggleVectors}
        >
          ↗️ Vectors
        </button>
      )}

      {/* Fullscreen Toggle */}
      <button
        className={`vis-toolbar-btn ${isFullscreen ? 'is-active' : ''}`}
        title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
        onClick={onToggleFullscreen}
      >
        {isFullscreen ? '🗗 Exit Fullscreen' : '⛶ Fullscreen'}
      </button>
    </div>
  )
}

