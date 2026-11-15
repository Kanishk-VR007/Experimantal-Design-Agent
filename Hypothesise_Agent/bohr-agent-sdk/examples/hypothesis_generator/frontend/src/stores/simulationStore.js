import { create } from 'zustand'

export const useSimulationStore = create((set) => ({
  // Timeline controls
  timelinePosition: 0,
  timelinePlaying: false,
  timelineSpeed: 1,
  timelineDuration: 10,

  // Camera presets
  cameraPreset: 'perspective',
  cameraPresets: ['perspective', 'top', 'front', 'side', 'isometric'],

  // Display toggles
  showGrid: true,
  showAxes: true,
  showVectors: true,
  showLabels: true,
  showWireframe: false,
  showBoundingBox: false,

  // Scene state
  selectedObject: null,
  highlightedObject: null,
  sceneReady: false,

  // Timeline actions
  setTimelinePosition: (pos) => set({ timelinePosition: pos }),
  toggleTimelinePlaying: () => set((s) => ({ timelinePlaying: !s.timelinePlaying })),
  setTimelineSpeed: (speed) => set({ timelineSpeed: speed }),
  setTimelineDuration: (dur) => set({ timelineDuration: dur }),

  // Camera actions
  setCameraPreset: (preset) => set({ cameraPreset: preset }),

  // Display toggle actions
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleAxes: () => set((s) => ({ showAxes: !s.showAxes })),
  toggleVectors: () => set((s) => ({ showVectors: !s.showVectors })),
  toggleLabels: () => set((s) => ({ showLabels: !s.showLabels })),
  toggleWireframe: () => set((s) => ({ showWireframe: !s.showWireframe })),
  toggleBoundingBox: () => set((s) => ({ showBoundingBox: !s.showBoundingBox })),

  // Scene actions
  setSelectedObject: (obj) => set({ selectedObject: obj }),
  setHighlightedObject: (obj) => set({ highlightedObject: obj }),
  setSceneReady: (v) => set({ sceneReady: v }),

  // Reset
  resetSimulationView: () => set({
    timelinePosition: 0,
    timelinePlaying: false,
    timelineSpeed: 1,
    cameraPreset: 'perspective',
    showGrid: true,
    showAxes: true,
    showVectors: true,
    showLabels: true,
    showWireframe: false,
    showBoundingBox: false,
    selectedObject: null,
    highlightedObject: null,
  }),
}))
