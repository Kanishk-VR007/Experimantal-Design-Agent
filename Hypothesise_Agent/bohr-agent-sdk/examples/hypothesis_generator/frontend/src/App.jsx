import { useEffect } from 'react'
import AppShell from './app/AppShell'
import { useWorkspaceStore } from './stores/workspaceStore'
import { useExperimentStore } from './stores/experimentStore'
import { useBackendHealth } from './hooks/useBackendHealth'
import { useDesignStream } from './hooks/useDesignStream'
import { useSimulation } from './hooks/useSimulation'

// Feature Components
import ExperimentComposer from './features/experiments/ExperimentComposer'
import ResearchPanel from './features/research/ResearchPanel'
import RefinementPanel from './features/research/RefinementPanel'
import ProtocolStream from './features/protocols/ProtocolStream'
import ProtocolEditor from './features/protocols/ProtocolEditor'
import SimulationWorkspace from './features/simulation/SimulationWorkspace'
import AgentPipeline from './features/agent-activity/AgentPipeline'
import EvaluationOverview from './features/evaluation/EvaluationOverview'
import MemoryDashboard from './features/memory/MemoryDashboard'
import SystemHealthMonitor from './features/system-monitor/SystemHealthMonitor'
import ReportHistory from './features/evaluation/ReportHistory'
import SimulationRunner from './components/SimulationRunner'
import LiquidLoader from './components/LiquidLoader'

import './App.css'

function App() {
  const activeView = useWorkspaceStore((s) => s.activeView)
  const setActiveView = useWorkspaceStore((s) => s.setActiveView)

  const { status, refresh: refreshHealth } = useBackendHealth()
  const { startStream } = useDesignStream()
  const { runSimulation } = useSimulation()

  // Experiment store state
  const topic = useExperimentStore((s) => s.topic)
  const setTopic = useExperimentStore((s) => s.setTopic)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const simulation = useExperimentStore((s) => s.simulation)
  const setSimulation = useExperimentStore((s) => s.setSimulation)
  const papers = useExperimentStore((s) => s.papers)
  const design = useExperimentStore((s) => s.design)
  const stage = useExperimentStore((s) => s.stage)
  const refinement = useExperimentStore((s) => s.refinement)
  const streaming = useExperimentStore((s) => s.streaming)
  const complete = useExperimentStore((s) => s.complete)
  const showSimulationRunner = useExperimentStore((s) => s.showSimulationRunner)
  const setShowSimulationRunner = useExperimentStore((s) => s.setShowSimulationRunner)

  // Handle Generate Submission
  const handleGenerate = (formData) => {
    setTopic(formData.topic)
    setActiveView('protocols')

    startStream(formData, (finishedTopic, finishedDesign, refData) => {
      // Auto-run simulation on protocol synthesis completion
      runSimulation(finishedTopic, finishedDesign, refData, formData.domain)
    })
  }

  // Handle Manual Re-run Simulation
  const handleRunSimulation = () => {
    if (!design || !complete) {
      alert('Please formulate an experimental design protocol first!')
      return
    }
    setShowSimulationRunner(true)
  }

  const handleSimulationComplete = (simData) => {
    setSimulation(simData)
    setShowSimulationRunner(false)
    setActiveView('simulation')
  }

  // Render view corresponding to current activeView in workspace
  const renderWorkspaceContent = () => {
    // While generating and no design chunks arrived yet, show animated LiquidLoader
    if (generating && !design) {
      return (
        <div className="workspace-loader-container">
          <LiquidLoader message={stage || 'Synthesizing Experimental Protocol via Multi-Agent LLMs...'} />
          <button
            type="button"
            className="loader-cancel-btn"
            style={{
              marginTop: '1.5rem',
              padding: '0.5rem 1.25rem',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '8px',
              color: '#fca5a5',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
            onClick={() => {
              useExperimentStore.getState().setGenerating(false)
              useExperimentStore.getState().updateOutput({ streaming: false, error: 'Operation cancelled by user.' })
              setActiveView('overview')
            }}
          >
            Cancel & Return to Studio
          </button>
          {refinement && <RefinementPanel refinement={refinement} />}
        </div>
      )
    }

    switch (activeView) {
      case 'overview':
        return (
          <div className="view-page-container">
            <ExperimentComposer
              onGenerate={handleGenerate}
              generating={generating}
              disabled={!status?.healthy}
            />
          </div>
        )

      case 'protocols':
        return (
          <div className="view-page-container">
            {refinement && <RefinementPanel refinement={refinement} />}
            <ProtocolStream
              design={design}
              streaming={streaming}
              complete={complete}
              topic={topic}
              papers={papers}
              onRunSimulation={handleRunSimulation}
              hasSimulation={simulation !== null}
              simulating={simulating}
            />
            {complete && (
              <ProtocolEditor
                design={design}
                topic={topic}
                papers={papers}
              />
            )}
          </div>
        )

      case 'simulation':
        return (
          <div className="view-page-container no-padding">
            <SimulationWorkspace
              simulation={simulation}
              onSimulationUpdated={setSimulation}
            />
          </div>
        )

      case 'papers':
        return (
          <div className="view-page-container">
            <ResearchPanel papers={papers} />
          </div>
        )

      case 'agent-activity':
        return (
          <div className="view-page-container">
            <AgentPipeline />
          </div>
        )

      case 'evaluation':
        return (
          <div className="view-page-container">
            <EvaluationOverview
              simulation={simulation}
              design={design}
            />
          </div>
        )

      case 'memory':
        return (
          <div className="view-page-container">
            <MemoryDashboard />
          </div>
        )

      case 'history':
        return (
          <div className="view-page-container">
            <ReportHistory
              onSelectReport={(r) => {
                setTopic(r.topic || '')
                setActiveView('evaluation')
              }}
            />
          </div>
        )

      case 'settings':
        return (
          <div className="view-page-container">
            <SystemHealthMonitor
              status={status}
              onRefresh={refreshHealth}
            />
          </div>
        )

      default:
        return (
          <div className="view-page-container">
            <ExperimentComposer
              onGenerate={handleGenerate}
              generating={generating}
              disabled={!status?.healthy}
            />
          </div>
        )
    }
  }

  return (
    <AppShell status={status} onRefreshHealth={refreshHealth}>
      {renderWorkspaceContent()}

      {/* Simulation Runner Modal */}
      {showSimulationRunner && (
        <SimulationRunner
          topic={topic}
          design={design}
          domain={useExperimentStore.getState().domain}
          onSimulationComplete={handleSimulationComplete}
          onClose={() => setShowSimulationRunner(false)}
        />
      )}
    </AppShell>
  )
}

export default App
