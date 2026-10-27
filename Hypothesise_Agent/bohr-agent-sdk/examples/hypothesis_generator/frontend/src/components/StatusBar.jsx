function StatusBar({ status, onRefresh }) {
  if (status.loading) {
    return (
      <div className="status-bar status-loading">
        <span>Checking system status...</span>
      </div>
    )
  }

  if (!status.healthy) {
    return (
      <div className="status-bar status-error">
        <span>⚠️ {status.error || 'Backend server is not available'}</span>
        <button onClick={onRefresh} className="btn-refresh">
          🔄 Retry
        </button>
      </div>
    )
  }

  if (!status.ollamaAvailable) {
    return (
      <div className="status-bar status-warning">
        <span>⚠️ Ollama is not running</span>
        <span className="status-help">
          Start Ollama: <code>ollama serve</code>
        </span>
        <button onClick={onRefresh} className="btn-refresh">
          🔄 Retry
        </button>
      </div>
    )
  }

  return (
    <div className="status-bar status-success">
      <span>✅ System Ready</span>
      <span className="status-details">
        Ollama: {status.models.join(', ')}
      </span>
      <button onClick={onRefresh} className="btn-refresh">
        🔄
      </button>
    </div>
  )
}

export default StatusBar
