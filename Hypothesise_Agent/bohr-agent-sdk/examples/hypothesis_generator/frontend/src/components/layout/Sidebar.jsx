import { useWorkspaceStore } from '../../stores/workspaceStore'

const NAV_SECTIONS = [
  {
    title: 'Workspace',
    items: [
      { id: 'overview', label: 'New Experiment', icon: 'add_circle' },
      { id: 'history', label: 'History', icon: 'history' },
      { id: 'papers', label: 'Research Papers', icon: 'menu_book' },
      { id: 'protocols', label: 'Protocols', icon: 'biotech' },
    ]
  },
  {
    title: 'Intelligence',
    items: [
      { id: 'simulation', label: 'Simulation', icon: 'psychology' },
      { id: 'agent-activity', label: 'Agent Activity', icon: 'multimodal_hand_eye' },
      { id: 'evaluation', label: 'Evaluation', icon: 'analytics' },
      { id: 'memory', label: 'Memory', icon: 'memory' },
    ]
  },
  {
    title: 'System',
    items: [
      { id: 'settings', label: 'Settings', icon: 'tune' },
    ]
  }
]

function Sidebar() {
  const activeView = useWorkspaceStore((s) => s.activeView)
  const collapsed = useWorkspaceStore((s) => s.sidebarCollapsed)
  const setActiveView = useWorkspaceStore((s) => s.setActiveView)
  const toggleSidebar = useWorkspaceStore((s) => s.toggleSidebar)

  return (
    <aside
      className={`sidebar-panel ${collapsed ? 'collapsed w-[72px] min-w-[72px]' : 'w-72 min-w-[288px]'} bg-surface-container-lowest flex flex-col justify-between border-r border-surface-container-high transition-all duration-200 select-none shadow-[0_1px_8px_rgba(0,0,0,0.04)]`}
    >
      <div className="flex flex-col">
        {/* Logo Header */}
        <div className="h-16 px-4 flex items-center justify-between bg-surface-container-low border-b border-surface-container-high">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center shrink-0 shadow-sm">
              <span className="material-symbols-outlined text-white text-[18px]">hub</span>
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span className="font-headline-sm text-[13px] font-bold text-on-surface uppercase tracking-wider">
                  Hypothesise
                </span>
                <span className="text-[10px] text-on-surface-variant font-medium">
                  Quantum Dynamics
                </span>
              </div>
            )}
          </div>
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <span className="material-symbols-outlined text-[20px]">
              {collapsed ? 'dock_to_right' : 'dock_to_left'}
            </span>
          </button>
        </div>

        {/* Swarm Compute Card */}
        {!collapsed && (
          <div className="p-3">
            <div className="p-3 rounded-xl bg-surface-container-low border border-surface-container-high/60">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-on-surface-variant font-semibold tracking-wider uppercase">
                  Swarm Compute
                </span>
                <span className="text-[11px] text-primary font-bold">94.2%</span>
              </div>
              <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full bg-primary-container rounded-full" style={{ width: '94.2%' }}></div>
              </div>
              <div className="flex justify-between items-center mt-1.5 text-[10px]">
                <span className="text-outline">Allocated: 384/400</span>
                <span className="text-secondary font-semibold">ACTIVE</span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation list */}
        <nav className="px-2.5 flex flex-col gap-0.5 overflow-y-auto max-h-[calc(100vh-270px)] py-1">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="flex flex-col mb-1.5">
              {!collapsed && (
                <div className="px-2 pt-2 pb-1">
                  <span className="text-[10px] text-outline font-bold tracking-wider uppercase">
                    {section.title}
                  </span>
                </div>
              )}
              {section.items.map((item) => {
                const isActive = activeView === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveView(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all ${
                      isActive
                        ? 'bg-primary-container text-white font-semibold shadow-sm'
                        : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined text-[19px] shrink-0 ${
                        isActive ? 'text-white' : 'text-on-surface-variant'
                      }`}
                    >
                      {item.icon}
                    </span>
                    {!collapsed && (
                      <span className="text-[13px] tracking-tight">{item.label}</span>
                    )}
                  </button>
                )
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom Secure Enclave */}
      <div className="p-3 bg-surface-container-lowest border-t border-surface-container-high">
        {!collapsed ? (
          <div className="p-2.5 rounded-xl bg-surface-container-low flex flex-col gap-1 border border-surface-container-high/60">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-outline font-medium">Latency Cycle</span>
              <span className="text-secondary font-semibold font-mono">0.42 ms</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-outline font-medium">Session</span>
              <span className="text-on-surface-variant font-mono font-medium">#0x4F88A</span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-secondary-container animate-pulse"></div>
              <span className="text-[10px] text-on-secondary-container font-semibold tracking-wider uppercase">
                SECURE ENCLAVE
              </span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-2 h-2 rounded-full bg-secondary-container animate-pulse" title="SECURE ENCLAVE"></div>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
