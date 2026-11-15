import { useWorkspaceStore } from '../stores/workspaceStore'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import DiagnosticDrawer from '../components/layout/DiagnosticDrawer'
import InspectorPanel from '../components/layout/InspectorPanel'

function AppShell({ children, status, onRefreshHealth }) {
  const sidebarCollapsed = useWorkspaceStore((s) => s.sidebarCollapsed)
  const inspectorCollapsed = useWorkspaceStore((s) => s.inspectorCollapsed)
  const diagnosticDrawerOpen = useWorkspaceStore((s) => s.diagnosticDrawerOpen)
  const diagnosticDrawerHeight = useWorkspaceStore((s) => s.diagnosticDrawerHeight)

  return (
    <div className="app-shell">
      {/* Top Bar */}
      <TopBar status={status} onRefreshHealth={onRefreshHealth} />

      <div className="app-shell-body">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Workspace Area */}
        <div className="app-shell-workspace">
          {/* Center Content */}
          <div
            className="app-shell-center"
            style={{
              paddingBottom: diagnosticDrawerOpen ? diagnosticDrawerHeight : 0,
            }}
          >
            {children}
          </div>

          {/* Diagnostic Drawer (bottom) */}
          {diagnosticDrawerOpen && <DiagnosticDrawer />}
        </div>

        {/* Inspector Panel (right) */}
        {!inspectorCollapsed && <InspectorPanel />}
      </div>
    </div>
  )
}

export default AppShell
