import React from 'react'

export function VisualizationFallback({ domain, reason, onRetry }) {
  return (
    <div className="vis-fallback-container">
      <div className="vis-fallback-card">
        <div className="vis-fallback-icon">🔬</div>
        <h3 className="vis-fallback-title">3D Visualization Mode</h3>
        <p className="vis-fallback-reason">
          {reason || `No direct 3D template available for domain: "${domain}". Numerical results and 2D charts are displayed below.`}
        </p>
        <div className="vis-fallback-notice">
          ℹ️ Scientific integrity note: We do not fabricate speculative 3D meshes when an authoritative geometric model is not yet configured.
        </div>
        {onRetry && (
          <button className="vis-btn vis-btn-rerun" onClick={onRetry}>
            🔄 Generate Generic 3D Apparatus
          </button>
        )}
      </div>
    </div>
  )
}

