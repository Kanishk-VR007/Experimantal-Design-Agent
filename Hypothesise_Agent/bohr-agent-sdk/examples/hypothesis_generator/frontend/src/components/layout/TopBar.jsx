import { useWorkspaceStore } from '../../stores/workspaceStore'

const VIEW_TITLES = {
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

function TopBar({ status, onRefreshHealth }) {
  const activeView = useWorkspaceStore((s) => s.activeView)
  const setActiveView = useWorkspaceStore((s) => s.setActiveView)
  const toggleInspector = useWorkspaceStore((s) => s.toggleInspector)
  const toggleDiagnosticDrawer = useWorkspaceStore((s) => s.toggleDiagnosticDrawer)

  const viewTitle = VIEW_TITLES[activeView] || activeView

  return (
    <header className="topbar h-16 bg-surface/90 backdrop-blur-xl z-40 flex items-center justify-between px-6 border-b border-surface-container-high shadow-[0_1px_8px_rgba(0,0,0,0.03)]">
      {/* Left: Branding & Breadcrumb */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-headline-sm text-[16px] text-on-surface font-bold tracking-tight">
            HYPOTHESISE
          </span>
          <span className="text-[10px] text-primary bg-surface-container-high px-2 py-0.5 rounded font-mono font-semibold">
            Agent OS v4.2
          </span>
        </div>

        <div className="h-4 w-[1px] bg-outline-variant"></div>
        <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-medium">
          Quantum Dynamics Lab
        </span>

        <div className="h-4 w-[1px] bg-outline-variant hidden xl:block"></div>
        <nav className="hidden xl:flex items-center gap-1.5 text-on-surface-variant text-[12px]">
          <span
            onClick={() => setActiveView('overview')}
            className="hover:text-on-surface cursor-pointer transition-colors"
          >
            Workspace
          </span>
          <span className="material-symbols-outlined text-[14px] text-outline">chevron_right</span>
          <span className="text-on-surface font-semibold">{viewTitle}</span>
        </nav>
      </div>

      {/* Right: Telemetry, Search, Actions & Profile */}
      <div className="flex items-center gap-3">
        {/* Live Cluster Pills */}
        <div className="hidden 2xl:flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <div
              className={`w-2 h-2 rounded-full ${
                status?.healthy ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'
              }`}
            ></div>
            <span className="font-medium">
              Backend {status?.healthy ? 'Online 14ms' : 'Connecting'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <span className="material-symbols-outlined text-[14px] text-secondary">cognition</span>
            <span className="font-medium">LM Studio 3-Model</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <span className="material-symbols-outlined text-[14px] text-primary">sync_alt</span>
            <span className="font-medium">Memory Sync 99.8%</span>
          </div>
        </div>

        {/* Global Search Box */}
        <div className="relative flex items-center">
          <span className="material-symbols-outlined absolute left-2.5 text-outline text-[17px]">
            search
          </span>
          <input
            className="w-44 lg:w-56 pl-8 pr-9 py-1.5 rounded-lg bg-surface-container-low text-on-surface placeholder:text-outline text-[12px] focus:outline-none focus:bg-surface-container-lowest focus:ring-1 focus:ring-primary transition-all border border-transparent focus:border-primary/40"
            placeholder="Search hypotheses, agents..."
            type="text"
          />
          <span className="absolute right-2 text-[10px] text-outline border border-outline-variant px-1 rounded bg-surface-container-lowest font-mono">
            ⌘K
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={onRefreshHealth}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            title="Refresh System Status"
          >
            <span className="material-symbols-outlined text-[19px]">sync</span>
          </button>

          <button
            onClick={toggleDiagnosticDrawer}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            title="Toggle Live Diagnostics"
          >
            <span className="material-symbols-outlined text-[19px]">bolt</span>
          </button>

          <button
            onClick={toggleInspector}
            className="relative w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            title="Inspector Settings"
          >
            <span className="material-symbols-outlined text-[19px]">tune</span>
          </button>
        </div>

        {/* New Experiment CTA */}
        <button
          onClick={() => setActiveView('overview')}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-container text-white rounded-lg text-[12px] font-semibold hover:bg-primary transition-all shadow-sm"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          <span>New Experiment</span>
        </button>

        {/* User Badge */}
        <div className="flex items-center gap-2 pl-2 border-l border-surface-container-high">
          <div className="hidden md:flex flex-col text-right">
            <span className="text-[12px] text-on-surface font-semibold leading-tight">
              Dr. Investigator
            </span>
            <span className="text-[10px] text-on-surface-variant font-medium">Lead AI Scientist</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white shadow-sm">
            <span className="material-symbols-outlined text-[18px]">person</span>
          </div>
        </div>
      </div>
    </header>
  )
}

export default TopBar
