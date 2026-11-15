import { create } from 'zustand'

export const useWorkspaceStore = create((set) => ({
  activeView: 'overview',
  sidebarCollapsed: false,
  inspectorCollapsed: true,
  diagnosticDrawerOpen: false,
  diagnosticDrawerHeight: 200,
  setActiveView: (view) => set({ activeView: view }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleInspector: () => set((s) => ({ inspectorCollapsed: !s.inspectorCollapsed })),
  toggleDiagnosticDrawer: () => set((s) => ({ diagnosticDrawerOpen: !s.diagnosticDrawerOpen })),
  setDiagnosticDrawerHeight: (h) => set({ diagnosticDrawerHeight: h }),
}))
