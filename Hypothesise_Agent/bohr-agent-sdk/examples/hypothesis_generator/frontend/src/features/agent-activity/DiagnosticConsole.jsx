import { useState } from 'react'
import { Terminal, Trash2, Download, Search } from 'lucide-react'

function DiagnosticConsole({ events = [], onClear }) {
  const [query, setQuery] = useState('')

  const filtered = events.filter((e) =>
    (e.message || '').toLowerCase().includes(query.toLowerCase()) ||
    (e.type || '').toLowerCase().includes(query.toLowerCase())
  )

  const handleExport = () => {
    const text = JSON.stringify(events, null, 2)
    const blob = new Blob([text], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `diagnostic_logs_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="diagnostic-console-panel">
      <div className="console-toolbar">
        <div className="console-title">
          <Terminal size={15} color="var(--accent-primary)" />
          <span>Diagnostic Console Logs</span>
        </div>

        <div className="console-actions">
          <div className="console-search">
            <Search size={13} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search logs..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button type="button" className="btn-icon-tool" onClick={handleExport} title="Export JSON logs">
            <Download size={14} />
          </button>
          <button type="button" className="btn-icon-tool" onClick={onClear} title="Clear logs">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="console-logs-window">
        {filtered.length === 0 ? (
          <div className="console-empty">No log records matched.</div>
        ) : (
          filtered.map((item, idx) => (
            <div key={idx} className="console-log-line">
              <span className="log-time">
                {new Date(item.timestamp).toISOString().split('T')[1].slice(0, 12)}
              </span>
              <span className={`log-badge ${item.severity || 'info'}`}>
                {item.type}
              </span>
              <span className="log-text">{item.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default DiagnosticConsole

