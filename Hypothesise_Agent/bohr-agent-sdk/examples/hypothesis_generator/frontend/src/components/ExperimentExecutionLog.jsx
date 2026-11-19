import React, { useRef, useEffect } from 'react'
import { useExperimentStore } from '../stores/experimentStore'

export default function ExperimentExecutionLog({ maxHeight = '260px' }) {
  const agentEvents = useExperimentStore((s) => s.agentEvents)
  const clearAgentEvents = useExperimentStore((s) => s.clearAgentEvents)
  const currentRunId = useExperimentStore((s) => s.currentRunId)
  const logEndRef = useRef(null)

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [agentEvents.length])

  return (
    <div className="p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-primary">terminal</span>
          <h4 className="font-headline-sm text-sm font-bold text-on-surface">
            Live Agent Execution Trace
          </h4>
          {currentRunId && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-primary font-bold">
              {currentRunId}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-outline font-mono">
            {agentEvents.length} EVENT(S)
          </span>
          {agentEvents.length > 0 && (
            <button
              type="button"
              onClick={clearAgentEvents}
              className="text-[10px] text-outline hover:text-red-600 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div
        className="bg-surface-container-low rounded-xl p-3 border border-surface-container-high/60 font-mono text-[11px] flex flex-col gap-1.5 overflow-y-auto"
        style={{ maxHeight }}
      >
        {agentEvents.length === 0 ? (
          <div className="text-outline text-center py-6">
            Awaiting execution events. Initialize an experiment to observe the multi-agent stream.
          </div>
        ) : (
          agentEvents.map((evt) => {
            const timeStr = evt.timestamp
              ? new Date(evt.timestamp).toLocaleTimeString()
              : ''
            const isError = evt.severity === 'error' || evt.type === 'error'
            const isSuccess = evt.severity === 'success' || evt.type === 'complete'

            return (
              <div
                key={evt.id}
                className={`flex items-start gap-2 leading-relaxed ${
                  isError
                    ? 'text-red-600 font-semibold'
                    : isSuccess
                    ? 'text-emerald-600 font-semibold'
                    : 'text-on-surface'
                }`}
              >
                {timeStr && <span className="text-outline shrink-0">[{timeStr}]</span>}
                {evt.stage && (
                  <span className="text-primary font-bold uppercase shrink-0">
                    [{evt.stage}]
                  </span>
                )}
                <span>{evt.message || JSON.stringify(evt)}</span>
              </div>
            )
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

