import React from 'react'
import { useExperimentStore } from '../stores/experimentStore'

export default function DataFreshnessIndicator({ compact = false }) {
  const currentRunId = useExperimentStore((s) => s.currentRunId)
  const runStartTime = useExperimentStore((s) => s.runStartTime)
  const runElapsedTime = useExperimentStore((s) => s.runElapsedTime)
  const dataProvenance = useExperimentStore((s) => s.dataProvenance)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const complete = useExperimentStore((s) => s.complete)

  if (!currentRunId) {
    if (compact) return null
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-container-low border border-surface-container-high text-[11px] text-outline font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-outline" />
        <span>Awaiting Experiment Execution</span>
      </div>
    )
  }

  const statusLabel = generating
    ? 'SYNTHESIZING DESIGN'
    : simulating
    ? 'CALCULATING ODE SOLVER'
    : complete
    ? 'VERIFIED RUN'
    : 'IDLE'

  if (compact) {
    return (
      <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-surface-container-low border border-surface-container-high text-[11px] font-mono">
        <span
          className={`w-2 h-2 rounded-full ${
            generating || simulating
              ? 'bg-amber-500 animate-pulse'
              : 'bg-emerald-500'
          }`}
        />
        <span className="text-on-surface font-bold">{currentRunId}</span>
        {runElapsedTime && <span className="text-outline">({runElapsedTime}s)</span>}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm text-[12px]">
      <div className="flex items-center gap-2.5">
        <span
          className={`w-2 h-2 rounded-full ${
            generating || simulating
              ? 'bg-amber-500 animate-pulse'
              : 'bg-emerald-500'
          }`}
        />
        <div className="flex items-center gap-2">
          <span className="text-outline font-mono uppercase text-[10px] font-bold">ACTIVE RUN:</span>
          <span className="font-mono font-bold text-on-surface">{currentRunId}</span>
        </div>
        <span className="text-outline">|</span>
        <div className="flex items-center gap-1.5 text-on-surface-variant font-medium">
          <span className="text-outline font-mono text-[10px]">SOURCE:</span>
          <span className="text-[11px] font-semibold text-primary">{dataProvenance}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 font-mono text-[11px]">
        {runElapsedTime && (
          <span className="text-outline">Latency: {runElapsedTime}s</span>
        )}
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
            generating || simulating
              ? 'bg-amber-100 text-amber-800'
              : 'bg-emerald-100 text-emerald-800'
          }`}
        >
          {statusLabel}
        </span>
      </div>
    </div>
  )
}

