import { useState, useRef, useCallback } from 'react'
import { X, AlertTriangle, Radio, Activity, Cpu } from 'lucide-react'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useExperimentStore } from '../../stores/experimentStore'

const TABS = [
  { id: 'agent', label: 'Agent Events', icon: Activity },
  { id: 'sse', label: 'SSE Logs', icon: Radio },
  { id: 'simulation', label: 'Simulation', icon: Cpu },
  { id: 'warnings', label: 'Warnings', icon: AlertTriangle },
]

const SEVERITY_COLORS = {
  info: 'var(--accent-secondary)',
  success: 'var(--accent-success)',
  warning: 'var(--accent-warning)',
  error: 'var(--accent-error)',
}

const SEVERITY_ICONS = {
  info: '●',
  success: '✓',
  warning: '⚠',
  error: '✕',
}

function DiagnosticDrawer() {
  const [activeTab, setActiveTab] = useState('agent')
  const toggleDiagnosticDrawer = useWorkspaceStore((s) => s.toggleDiagnosticDrawer)
  const drawerHeight = useWorkspaceStore((s) => s.diagnosticDrawerHeight)
  const setDrawerHeight = useWorkspaceStore((s) => s.setDiagnosticDrawerHeight)
  const agentEvents = useExperimentStore((s) => s.agentEvents)
  const clearAgentEvents = useExperimentStore((s) => s.clearAgentEvents)

  const dragRef = useRef(null)
  const startYRef = useRef(0)
  const startHeightRef = useRef(0)

  const handleDragStart = useCallback((e) => {
    e.preventDefault()
    startYRef.current = e.clientY
    startHeightRef.current = drawerHeight

    const handleDrag = (ev) => {
      const delta = startYRef.current - ev.clientY
      const newHeight = Math.max(120, Math.min(500, startHeightRef.current + delta))
      setDrawerHeight(newHeight)
    }

    const handleDragEnd = () => {
      document.removeEventListener('mousemove', handleDrag)
      document.removeEventListener('mouseup', handleDragEnd)
    }

    document.addEventListener('mousemove', handleDrag)
    document.addEventListener('mouseup', handleDragEnd)
  }, [drawerHeight, setDrawerHeight])

  const filteredEvents = agentEvents.filter((ev) => {
    if (activeTab === 'agent') return true
    if (activeTab === 'sse') return ev.type === 'start' || ev.type === 'status' || ev.type === 'chunk' || ev.type === 'complete' || ev.type === 'error'
    if (activeTab === 'simulation') return ev.type === 'simulation'
    if (activeTab === 'warnings') return ev.severity === 'warning' || ev.severity === 'error'
    return true
  })

  return (
    <div
      className="diagnostic-drawer glass-strong"
      style={{ height: drawerHeight }}
    >
      {/* Drag handle */}
      <div
        className="diagnostic-drawer-handle"
        onMouseDown={handleDragStart}
        ref={dragRef}
      >
        <div className="diagnostic-drawer-handle-bar" />
      </div>

      {/* Tab bar */}
      <div className="diagnostic-drawer-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              className={`diagnostic-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={12} />
              <span>{tab.label}</span>
            </button>
          )
        })}
        <div className="diagnostic-drawer-actions">
          <button className="diagnostic-action-btn" onClick={clearAgentEvents} title="Clear logs">
            Clear
          </button>
          <button className="diagnostic-action-btn" onClick={toggleDiagnosticDrawer} title="Close">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Log entries */}
      <div className="diagnostic-drawer-content">
        {filteredEvents.length === 0 ? (
          <div className="diagnostic-empty">No events recorded yet</div>
        ) : (
          filteredEvents.map((event) => (
            <div key={event.id} className="diagnostic-log-entry">
              <span className="log-timestamp">
                {new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span
                className="log-severity-icon"
                style={{ color: SEVERITY_COLORS[event.severity] || SEVERITY_COLORS.info }}
              >
                {SEVERITY_ICONS[event.severity] || SEVERITY_ICONS.info}
              </span>
              <span className="log-type">[{event.type}]</span>
              <span className="log-message">{event.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default DiagnosticDrawer
