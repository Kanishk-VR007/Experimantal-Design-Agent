import { Settings, RefreshCw } from 'lucide-react'
import { useWorkspaceStore } from '../../stores/workspaceStore'

const VIEW_LABELS = {
  overview: 'New Experiment',
  history: 'History',
  papers: 'Research Papers',
  protocols: 'Protocols',
  simulation: 'Simulation',
  'agent-activity': 'Agent Activity',
  evaluation: 'Evaluation',
  memory: 'Memory',
  settings: 'Settings',
}

function HealthDot({ label, healthy }) {
  return (
    <div className="topbar-health-dot" title={`${label}: ${healthy ? 'Connected' : 'Disconnected'}`}>
      <span
        className={`health-indicator ${healthy ? 'healthy' : 'unhealthy'}`}
      />
      <span className="health-label">{label}</span>
    </div>
  )
}

function TopBar({ status, onRefreshHealth }) {
  const activeView = useWorkspaceStore((s) => s.activeView)
  const toggleInspector = useWorkspaceStore((s) => s.toggleInspector)
  const toggleDiagnosticDrawer = useWorkspaceStore((s) => s.toggleDiagnosticDrawer)

  const viewLabel = VIEW_LABELS[activeView] || activeView

  return (
    <header className="topbar glass-strong">
      {/* Left: Branding */}
      <div className="topbar-left">
        <span className="topbar-brand">🔬 Hypothesise Agent</span>
      </div>

      {/* Center: Breadcrumb */}
      <div className="topbar-center">
        <span className="topbar-breadcrumb">
          <span className="topbar-breadcrumb-root">Workspace</span>
          <span className="topbar-breadcrumb-sep">/</span>
          <span className="topbar-breadcrumb-current">{viewLabel}</span>
        </span>
      </div>

      {/* Right: Health + Controls */}
      <div className="topbar-right">
        <div className="topbar-health">
          <HealthDot label="Backend" healthy={status?.healthy} />
          <HealthDot label="LLM" healthy={status?.ollamaAvailable} />
          <HealthDot label="Memory" healthy={!status?.error} />
          <button
            className="topbar-icon-btn"
            onClick={onRefreshHealth}
            title="Refresh health"
          >
            <RefreshCw size={14} strokeWidth={1.5} />
          </button>
        </div>
        <button
          className="topbar-icon-btn"
          onClick={toggleDiagnosticDrawer}
          title="Toggle diagnostic drawer"
        >
          <span style={{ fontSize: '12px' }}>⚡</span>
        </button>
        <button
          className="topbar-icon-btn"
          onClick={toggleInspector}
          title="Toggle inspector"
        >
          <Settings size={14} strokeWidth={1.5} />
        </button>
      </div>
    </header>
  )
}

export default TopBar
