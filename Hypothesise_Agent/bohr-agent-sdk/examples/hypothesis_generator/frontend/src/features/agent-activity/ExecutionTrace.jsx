import { useState } from 'react'
import { Activity, Filter, Terminal } from 'lucide-react'

function ExecutionTrace({ events = [] }) {
  const [filterType, setFilterType] = useState('all')

  const filtered = events.filter((ev) => {
    if (filterType === 'all') return true
    return ev.type === filterType
  })

  return (
    <div className="execution-trace-container">
      <div className="trace-header">
        <div className="trace-title">
          <Terminal size={16} color="var(--accent-primary)" />
          <span>Agent Execution Trace ({events.length} events)</span>
        </div>
        <div className="trace-filters">
          {['all', 'start', 'papers', 'refinement', 'simulation', 'complete', 'error'].map((t) => (
            <button
              key={t}
              type="button"
              className={`filter-btn ${filterType === t ? 'active' : ''}`}
              onClick={() => setFilterType(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="trace-list">
        {filtered.length === 0 ? (
          <div className="empty-trace">No execution events recorded for this filter.</div>
        ) : (
          filtered.map((item, idx) => (
            <div key={item.id || idx} className={`trace-row ${item.severity || 'info'}`}>
              <span className="trace-time">
                {new Date(item.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className="trace-type">[{item.type}]</span>
              <span className="trace-message">{item.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ExecutionTrace

