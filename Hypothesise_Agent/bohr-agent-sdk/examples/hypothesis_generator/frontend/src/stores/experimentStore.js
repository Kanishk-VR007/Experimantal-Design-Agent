import { create } from 'zustand'

export const useExperimentStore = create((set, get) => ({
  // Active Experiment Identity & Provenance
  currentRunId: null,
  runSequence: 0,
  runStartTime: null,
  runElapsedTime: null,
  dataProvenance: 'Awaiting Formulation',

  // Core Inputs
  topic: '',
  maxPapers: 3,
  useMockData: false,
  domain: null,

  // Execution Lifecycle State
  generating: false,
  simulating: false,
  streaming: false,
  complete: false,
  error: null,
  stage: '',
  executionStage: 'idle', // 'idle' | 'prompt_refinement' | 'visual_analysis' | 'literature_search' | 'experimental_design' | 'ode_simulation' | 'scientific_validation' | 'memory_update' | 'complete' | 'error'

  // Results & Artifacts
  papers: [],
  design: '',
  refinement: null,
  simulation: null,
  validationReport: null,
  designCompleteness: null,
  showSimulationRunner: false,

  // Telemetry & Logs
  agentEvents: [],
  modelStatus: null,

  // Setters
  setTopic: (topic) => set({ topic }),
  setMaxPapers: (n) => set({ maxPapers: n }),
  setUseMockData: (v) => set({ useMockData: v }),
  setDomain: (d) => set({ domain: d }),
  setSelectedDomain: (d) => set({ domain: d }),
  setGenerating: (v) => set({ generating: v }),
  setSimulating: (v) => set({ simulating: v }),
  setExecutionStage: (stage) => set({ executionStage: stage, stage }),
  setModelStatus: (modelStatus) => set({ modelStatus }),
  setShowSimulationRunner: (v) => set({ showSimulationRunner: v }),

  // Set authoritative simulation results (automatically updates validationReport)
  setSimulation: (sim) => set({
    simulation: sim,
    validationReport: sim?.validation || null,
    dataProvenance: sim?.engine_used || 'Deterministic Domain Engine',
  }),

  // Start an authoritative new run
  startNewRun: (topic, domain) => {
    const nextSeq = get().runSequence + 1
    const runId = `RUN-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`
    set({
      currentRunId: runId,
      runSequence: nextSeq,
      runStartTime: Date.now(),
      runElapsedTime: null,
      topic: topic || get().topic,
      domain: domain || get().domain,
      generating: true,
      simulating: false,
      streaming: true,
      complete: false,
      error: null,
      stage: 'Formulating hypothesis...',
      executionStage: 'prompt_refinement',
      dataProvenance: 'Live Run in Progress',
      papers: [],
      design: '',
      refinement: null,
      simulation: null,
      validationReport: null,
      designCompleteness: null,
      agentEvents: [
        {
          id: Date.now(),
          run_id: runId,
          timestamp: new Date().toISOString(),
          type: 'run_init',
          message: `Run ${runId} initialized for domain [${domain || 'multi-physics'}]`,
        }
      ],
    })
    return runId
  },

  // Partial output update with stale event guard
  updateOutput: (partial) => {
    // If incoming payload has run_id and doesn't match current run, drop it
    if (partial.run_id && get().currentRunId && partial.run_id !== get().currentRunId) {
      console.warn(`[experimentStore] Stale event dropped for run ${partial.run_id} (active: ${get().currentRunId})`)
      return
    }
    set((s) => ({
      ...s,
      ...partial,
      validationReport: partial.simulation?.validation || s.validationReport,
    }))
  },

  // Reset output
  resetOutput: () => set({
    papers: [],
    design: '',
    stage: '',
    executionStage: 'idle',
    refinement: null,
    streaming: false,
    complete: false,
    error: null,
    simulation: null,
    validationReport: null,
    designCompleteness: null,
  }),

  // Append real-time agent event
  addAgentEvent: (event) => set((s) => {
    const runId = event.run_id || s.currentRunId
    // Guard against stale run events if specified
    if (event.run_id && s.currentRunId && event.run_id !== s.currentRunId) {
      return s
    }
    const newEvt = {
      ...event,
      id: Date.now() + Math.random(),
      run_id: runId,
      timestamp: event.timestamp || new Date().toISOString(),
    }
    return {
      agentEvents: [...s.agentEvents.slice(-249), newEvt],
    }
  }),

  clearAgentEvents: () => set({ agentEvents: [] }),
}))
