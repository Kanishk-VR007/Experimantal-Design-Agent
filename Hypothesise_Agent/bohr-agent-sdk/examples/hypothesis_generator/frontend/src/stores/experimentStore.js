import { create } from 'zustand'

export const useExperimentStore = create((set, get) => ({
  topic: '',
  maxPapers: 3,
  useMockData: false,
  domain: null,
  generating: false,
  simulating: false,
  papers: [],
  design: '',
  stage: '',
  refinement: null,
  streaming: false,
  complete: false,
  error: null,
  simulation: null,
  showSimulationRunner: false,
  agentEvents: [],

  setTopic: (topic) => set({ topic }),
  setMaxPapers: (n) => set({ maxPapers: n }),
  setUseMockData: (v) => set({ useMockData: v }),
  setDomain: (d) => set({ domain: d }),
  setSelectedDomain: (d) => set({ domain: d }),
  setGenerating: (v) => set({ generating: v }),
  setSimulating: (v) => set({ simulating: v }),
  setSimulation: (sim) => set({ simulation: sim }),
  setShowSimulationRunner: (v) => set({ showSimulationRunner: v }),

  updateOutput: (partial) => set((s) => ({ ...s, ...partial })),

  resetOutput: () => set({
    papers: [], design: '', stage: '', refinement: null,
    streaming: false, complete: false, error: null, simulation: null,
  }),

  addAgentEvent: (event) => set((s) => ({
    agentEvents: [...s.agentEvents.slice(-199), { ...event, id: Date.now(), timestamp: new Date().toISOString() }]
  })),
  clearAgentEvents: () => set({ agentEvents: [] }),
}))
