import React from 'react'

export function MeasurementOverlay({
  overlays = [],
  currentTime = 0,
  animationController,
  hoveredObject,
  templateMeta,
  isSimulationBacked = true,
}) {
  return (
    <div className="vis-hud-container">
      {/* Top Left: Experiment Badge & Status */}
      <div className="vis-hud-header">
        <div className="vis-hud-title-badge">
          <span className="vis-hud-icon">{templateMeta?.icon || '🔬'}</span>
          <div>
            <div className="vis-hud-title">{templateMeta?.label || 'Experiment'}</div>
            <div className="vis-hud-badge-row">
              <span className={`vis-badge ${isSimulationBacked ? 'vis-badge-sim' : 'vis-badge-illus'}`}>
                {isSimulationBacked ? '● Numerical Solver Backed' : '○ Illustrative Model'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Right: Real-time Telemetry & Scientific Overlays */}
      {overlays && overlays.length > 0 && (
        <div className="vis-hud-metrics">
          <div className="vis-hud-metrics-title">📊 Live Telemetry</div>
          <div className="vis-hud-metrics-grid">
            {overlays.map((item) => {
              let displayVal = item.value
              if (item.is_dynamic && item.time_series && animationController) {
                const sampled = animationController.getDynamicMeasurement(item.time_series, currentTime)
                if (sampled !== null && sampled !== undefined) {
                  displayVal = typeof sampled === 'number' ? sampled.toFixed(3) : sampled
                }
              }

              return (
                <div key={item.id} className="vis-hud-metric-card">
                  <span className="vis-metric-label">{item.label}</span>
                  <span className="vis-metric-val">
                    {displayVal} {item.unit && <small>{item.unit}</small>}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Bottom Center Hover Tooltip */}
      {hoveredObject && (
        <div className="vis-hover-tooltip">
          <div className="vis-tooltip-title">{hoveredObject.name}</div>
          <div className="vis-tooltip-type">Type: {hoveredObject.type}</div>
          {hoveredObject.metadata && Object.keys(hoveredObject.metadata).length > 0 && (
            <div className="vis-tooltip-props">
              {Object.entries(hoveredObject.metadata).map(([k, v]) => (
                <span key={k} className="vis-tooltip-prop">
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

