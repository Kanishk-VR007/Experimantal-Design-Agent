import { Clock } from 'lucide-react'

function AgentActivityTimeline({ layers = [] }) {
  return (
    <div className="activity-timeline-card">
      <div className="timeline-card-header">
        <Clock size={16} color="var(--accent-secondary)" />
        <span>Agent Pipeline Execution Waterfall</span>
      </div>

      <div className="waterfall-bars">
        {layers.map((l) => {
          const widthPct = l.status === 'completed' ? 100 : l.status === 'running' ? 55 : 5
          const barColor =
            l.status === 'completed'
              ? 'var(--accent-success)'
              : l.status === 'running'
              ? 'var(--accent-primary)'
              : 'var(--border)'

          return (
            <div key={l.id} className="waterfall-row">
              <div className="row-meta">
                <span className="row-layer-id">{l.id}</span>
                <span className="row-layer-name">{l.name}</span>
                <span className="row-duration">{l.duration || (l.status === 'running' ? 'Active...' : 'Queued')}</span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${widthPct}%`, background: barColor }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AgentActivityTimeline

