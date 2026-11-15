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
        <span>⚠️ {status.error || 'Backend / Local LLM server is not available'}</span>
        <button onClick={onRefresh} className="btn-refresh">
          🔄 Retry
        </button>
      </div>
    )
  }

  if (!status.ollamaAvailable) {
    return (
      <div className="status-bar status-warning">
        <span>⚠️ LM Studio / Local LLM is not running</span>
        <span className="status-help">
          Start LM Studio server: <code>lms server start</code> &amp; load <code>oreal-deepseek-r1-distill-qwen-7b</code>
        </span>
        <button onClick={onRefresh} className="btn-refresh">
          🔄 Retry
        </button>
      </div>
    )
  }

  const providerLabel = status.provider === 'lmstudio' ? 'LM Studio' : 'Ollama'
  const modelText = status.activeModel || (status.models || []).join(', ')
  const refinerText = status.refinerAvailable && status.refinerModel
    ? ` | Prompt Refiner: Ollama (${status.refinerModel})`
    : ''

  return (
    <div className="status-bar status-success">
      <span>✅ System Ready</span>
      <span className="status-details">
        {providerLabel}: {modelText}{refinerText}
      </span>
      <button onClick={onRefresh} className="btn-refresh">
        🔄
      </button>
    </div>
  )
}

export default StatusBar
