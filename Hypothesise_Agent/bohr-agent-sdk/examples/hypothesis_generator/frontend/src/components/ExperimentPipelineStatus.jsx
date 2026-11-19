import React from 'react'
import { useExperimentStore } from '../stores/experimentStore'

const PIPELINE_STAGES = [
  {
    id: 'prompt_refinement',
    label: '1. Prompt Refinement',
    agent: 'Qwen3-4B-Thinking',
    icon: 'psychology',
  },
  {
    id: 'literature_search',
    label: '2. Literature Synthesis',
    agent: 'arXiv + Semantic Scholar',
    icon: 'menu_book',
  },
  {
    id: 'experimental_design',
    label: '3. Protocol Reasoning',
    agent: 'DeepSeek-R1-0528',
    icon: 'hub',
  },
  {
    id: 'ode_simulation',
    label: '4. Deterministic ODE',
    agent: 'Domain Simulation Engine',
    icon: 'precision_manufacturing',
  },
  {
    id: 'scientific_validation',
    label: '5. Validation & Audit',
    agent: 'Scientific Validator Suite',
    icon: 'verified',
  },
]

export default function ExperimentPipelineStatus() {
  const executionStage = useExperimentStore((s) => s.executionStage)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const complete = useExperimentStore((s) => s.complete)
  const error = useExperimentStore((s) => s.error)

  const getStageStatus = (stageId, index) => {
    if (error) {
      if (executionStage === stageId) return 'error'
    }
    if (complete) return 'completed'

    // Determine current index
    const stageOrder = [
      'prompt_refinement',
      'literature_search',
      'experimental_design',
      'ode_simulation',
      'scientific_validation',
    ]
    const currentIndex = stageOrder.indexOf(executionStage)

    if (currentIndex === -1) {
      return generating ? (index === 0 ? 'active' : 'pending') : 'pending'
    }

    if (index < currentIndex) return 'completed'
    if (index === currentIndex) return generating || simulating ? 'active' : 'completed'
    return 'pending'
  }

  return (
    <div className="p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-primary">linear_scale</span>
          <h4 className="font-headline-sm text-sm font-bold text-on-surface">
            Autonomous Pipeline Progression
          </h4>
        </div>
        <span className="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded bg-surface-container-high text-primary">
          {error ? 'PIPELINE ERROR' : complete ? 'ALL STAGES VERIFIED' : generating || simulating ? 'ACTIVE EXECUTION' : 'IDLE'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
        {PIPELINE_STAGES.map((stg, i) => {
          const status = getStageStatus(stg.id, i)
          const isActive = status === 'active'
          const isCompleted = status === 'completed'
          const isError = status === 'error'

          return (
            <div
              key={stg.id}
              className={`p-2.5 rounded-xl border flex flex-col justify-between gap-1.5 transition-all ${
                isActive
                  ? 'bg-primary-container text-white border-primary shadow-sm ring-2 ring-primary/20'
                  : isCompleted
                  ? 'bg-surface-container-low border-surface-container-high text-on-surface'
                  : isError
                  ? 'bg-red-50 border-red-200 text-red-900'
                  : 'bg-surface-container-lowest/60 border-surface-container-high/60 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between">
                <span
                  className={`material-symbols-outlined text-[17px] ${
                    isActive ? 'text-white' : isCompleted ? 'text-emerald-600' : 'text-outline'
                  }`}
                >
                  {isCompleted ? 'check_circle' : stg.icon}
                </span>
                {isActive && <span className="w-2 h-2 rounded-full bg-white animate-ping" />}
              </div>

              <div className="flex flex-col">
                <span className="text-[11px] font-bold leading-tight">{stg.label}</span>
                <span
                  className={`text-[9px] font-mono truncate mt-0.5 ${
                    isActive ? 'text-white/80' : 'text-outline'
                  }`}
                >
                  {stg.agent}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

