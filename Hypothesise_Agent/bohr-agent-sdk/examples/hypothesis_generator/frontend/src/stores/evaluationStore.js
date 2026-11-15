import { create } from 'zustand'

export const useEvaluationStore = create((set) => ({
  // Reports state
  reports: [],
  selectedReportId: null,
  selectedReport: null,
  loadingReports: false,
  loadingReport: false,

  // Accuracy
  accuracyReport: null,
  loadingAccuracy: false,

  // Feedback
  feedbackSubmitting: false,
  feedbackSuccess: false,

  // Filters
  sortBy: 'date',
  sortOrder: 'desc',
  filterDomain: null,

  // Actions
  setReports: (reports) => set({ reports }),
  setSelectedReportId: (id) => set({ selectedReportId: id }),
  setSelectedReport: (report) => set({ selectedReport: report }),
  setLoadingReports: (v) => set({ loadingReports: v }),
  setLoadingReport: (v) => set({ loadingReport: v }),
  setAccuracyReport: (report) => set({ accuracyReport: report }),
  setLoadingAccuracy: (v) => set({ loadingAccuracy: v }),
  setFeedbackSubmitting: (v) => set({ feedbackSubmitting: v }),
  setFeedbackSuccess: (v) => set({ feedbackSuccess: v }),
  setSortBy: (sortBy) => set({ sortBy }),
  setSortOrder: (order) => set({ sortOrder: order }),
  setFilterDomain: (domain) => set({ filterDomain: domain }),

  // Reset
  resetEvaluation: () => set({
    reports: [],
    selectedReportId: null,
    selectedReport: null,
    accuracyReport: null,
    feedbackSuccess: false,
  }),
}))
