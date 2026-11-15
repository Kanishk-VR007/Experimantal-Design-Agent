import {
  Beaker, FlaskConical, BookOpen, FileText, Atom,
  BarChart3, Brain, Settings, ChevronLeft, ChevronRight,
  Plus, History, Layers, Activity
} from 'lucide-react'
import { useWorkspaceStore } from '../../stores/workspaceStore'

const NAV_ITEMS = [
  { id: 'overview', label: 'New Experiment', icon: Plus, group: 'main' },
  { id: 'history', label: 'History', icon: History, group: 'main' },
  { id: 'papers', label: 'Research Papers', icon: BookOpen, group: 'main' },
  { id: 'protocols', label: 'Protocols', icon: FileText, group: 'main' },
  { id: 'simulation', label: 'Simulation', icon: Atom, group: 'analysis' },
  { id: 'agent-activity', label: 'Agent Activity', icon: Activity, group: 'analysis' },
  { id: 'evaluation', label: 'Evaluation', icon: BarChart3, group: 'analysis' },
  { id: 'memory', label: 'Memory', icon: Brain, group: 'analysis' },
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system' },
]

function Sidebar() {
  const activeView = useWorkspaceStore((s) => s.activeView)
  const collapsed = useWorkspaceStore((s) => s.sidebarCollapsed)
  const setActiveView = useWorkspaceStore((s) => s.setActiveView)
  const toggleSidebar = useWorkspaceStore((s) => s.toggleSidebar)

  const mainItems = NAV_ITEMS.filter((i) => i.group === 'main')
  const analysisItems = NAV_ITEMS.filter((i) => i.group === 'analysis')
  const systemItems = NAV_ITEMS.filter((i) => i.group === 'system')

  const renderItem = (item) => {
    const Icon = item.icon
    const isActive = activeView === item.id
    return (
      <button
        key={item.id}
        data-view={item.id}
        className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
        onClick={() => setActiveView(item.id)}
        title={collapsed ? item.label : undefined}
      >
        <Icon size={18} strokeWidth={1.5} />
        {!collapsed && <span className="sidebar-nav-label">{item.label}</span>}
      </button>
    )
  }

  return (
    <aside className={`sidebar-panel ${collapsed ? 'collapsed' : ''}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <FlaskConical size={collapsed ? 20 : 22} strokeWidth={1.5} />
        </div>
        {!collapsed && <span className="sidebar-logo-text">Hypothesise</span>}
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-group">
          {mainItems.map(renderItem)}
        </div>

        <div className="sidebar-nav-separator" />

        <div className="sidebar-nav-group">
          {!collapsed && <div className="sidebar-nav-group-label">Analysis</div>}
          {analysisItems.map(renderItem)}
        </div>

        <div className="sidebar-nav-separator" />

        <div className="sidebar-nav-group">
          {systemItems.map(renderItem)}
        </div>
      </nav>

      {/* Collapse toggle */}
      <button className="sidebar-collapse-btn" onClick={toggleSidebar}>
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  )
}

export default Sidebar
