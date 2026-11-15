function MetricBar({ score, label, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100))
  const color =
    pct >= 85
      ? 'var(--accent-success)'
      : pct >= 70
      ? 'var(--accent-warning)'
      : 'var(--accent-error)'

  return (
    <div className="metric-bar-component">
      <div className="metric-bar-header">
        <span className="metric-bar-label">{label}</span>
        <span className="metric-bar-value" style={{ color }}>{score}%</span>
      </div>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

export default MetricBar

