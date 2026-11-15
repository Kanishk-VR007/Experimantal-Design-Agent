import { CheckCircle2, Clock, AlertTriangle, XCircle, Loader2 } from 'lucide-react'

const STATUS_ICONS = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  warning: AlertTriangle,
  failed: XCircle,
}

const STATUS_COLORS = {
  pending: 'var(--text-muted)',
  running: 'var(--accent-primary)',
  completed: 'var(--accent-success)',
  warning: 'var(--accent-warning)',
  failed: 'var(--accent-error)',
}

function AgentNode({ layer, isSelected, onSelect }) {
  const Icon = STATUS_ICONS[layer.status] || Clock
  const statusColor = STATUS_COLORS[layer.status] || 'var(--text-muted)'

  return (
    <div
      className={`agent-node-card ${layer.status} ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(layer)}
    >
      <div className="agent-node-header">
        <span className="agent-layer-tag">{layer.id}</span>
        <div className="agent-status-indicator" style={{ color: statusColor }}>
          <Icon size={14} className={layer.status === 'running' ? 'spinner-rotate' : ''} />
          <span className="status-name">{layer.status}</span>
        </div>
      </div>

      <h4 className="agent-node-title">{layer.name}</h4>
      <p className="agent-node-role">{layer.role}</p>

      <div className="agent-node-footer">
        <span className="agent-engine-tag">{layer.engine}</span>
        {layer.duration && <span className="agent-duration">{layer.duration}</span>}
      </div>
    </div>
  )
}

export default AgentNode

