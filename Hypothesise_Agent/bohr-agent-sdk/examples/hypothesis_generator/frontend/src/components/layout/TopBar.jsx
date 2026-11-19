import { useState } from 'react'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useExperimentStore } from '../../stores/experimentStore'
import DataFreshnessIndicator from '../DataFreshnessIndicator'

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
  const [searchTerm, setSearchTerm] = useState('')

  const viewTitle = VIEW_TITLES[activeView] || activeView

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter' && searchTerm.trim()) {
      const q = searchTerm.toLowerCase()
      if (q.includes('sim') || q.includes('3d') || q.includes('ode')) {
        setActiveView('simulation')
      } else if (q.includes('agent') || q.includes('model') || q.includes('vram')) {
        setActiveView('agent-activity')
      } else if (q.includes('eval') || q.includes('score') || q.includes('audit')) {
        setActiveView('evaluation')
      } else if (q.includes('memo') || q.includes('vector') || q.includes('weight')) {
        setActiveView('memory')
      } else if (q.includes('paper') || q.includes('arxiv') || q.includes('ref')) {
        setActiveView('papers')
      } else if (q.includes('hist') || q.includes('run')) {
        setActiveView('history')
      } else {
        setActiveView('overview')
      }
    }
  }

  const latencyStr = status?.backendHealthy
    ? `Online ${status.latencyMs ?? 14}ms`
    : 'Connecting'

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
          Autonomous Lab
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

      {/* Right: Telemetry, Run Badge, Search, Actions */}
      <div className="flex items-center gap-3">
        {/* Compact Freshness Badge */}
        <DataFreshnessIndicator compact />

        {/* Live Cluster Pills */}
        <div className="hidden 2xl:flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <div
              className={`w-2 h-2 rounded-full ${
                status?.healthy ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'
              }`}
            ></div>
            <span className="font-medium font-mono">Backend {latencyStr}</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <span className="material-symbols-outlined text-[14px] text-secondary">cognition</span>
            <span className="font-medium truncate max-w-[150px]">
              {status?.activeModel ? status.activeModel.split('/')[1] || status.activeModel : 'LM Studio 3-Model'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container text-on-surface text-[11px]">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                status?.memoryHealthy ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            ></span>
            <span className="font-medium">
              {status?.memoryHealthy ? 'Memory Synced' : 'Memory Standby'}
            </span>
          </div>
        </div>

        {/* Functional Search Box */}
        <div className="relative flex items-center">
          <span className="material-symbols-outlined absolute left-2.5 text-outline text-[17px]">
            search
          </span>
          <input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="w-44 lg:w-56 pl-8 pr-9 py-1.5 rounded-lg bg-surface-container-low text-on-surface placeholder:text-outline text-[12px] focus:outline-none focus:bg-surface-container-lowest focus:ring-1 focus:ring-primary transition-all border border-transparent focus:border-primary/40"
            placeholder="Jump to view... (Enter)"
            type="text"
          />
          <span className="absolute right-2 text-[10px] text-outline border border-outline-variant px-1 rounded bg-surface-container-lowest font-mono">
            ↵
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
      </div>
    </header>
  )
}

export default TopBar
