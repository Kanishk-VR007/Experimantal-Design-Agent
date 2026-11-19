import React from 'react'
import { useModelStatus } from '../hooks/useModelStatus'

const ROLE_METADATA = {
  prompt_refiner: {
    title: 'Prompt Refinement & Grounding',
    modelName: 'Qwen3-4B-Thinking',
    modelId: 'qwen/qwen3-4b-thinking-2507',
    stage: '1. Semantic Grounding',
    icon: 'psychology',
    color: '#004ac6',
  },
  vision_analyzer: {
    title: 'Visual Topology Analysis',
    modelName: 'Qwen3-VL-4B-Thinking',
    modelId: 'qwen3-vl-4b-thinking',
    stage: '2. Diagram / Vision Guidance',
    icon: 'visibility',
    color: '#006591',
  },
  main_reasoner: {
    title: 'Experimental Architecture Synthesizer',
    modelName: 'DeepSeek-R1-0528-Qwen3-8B',
    modelId: 'deepseek/deepseek-r1-0528-qwen3-8b',
    stage: '3. Hypothesis & Methodology',
    icon: 'hub',
    color: '#6a1edb',
  },
}

export default function ModelRuntimeStatus({ compact = false }) {
  const { modelStatus, serverOnline, activeRole, roles, singleActivePolicy } = useModelStatus(3000)

  // Map roles array by role_key
  const roleMap = {}
  if (roles && Array.isArray(roles)) {
    roles.forEach((r) => {
      roleMap[r.role_key] = r
    })
  }

  if (compact) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-container-low border border-surface-container-high text-[11px]">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              serverOnline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
            }`}
          />
          <span className="font-semibold text-on-surface">LM Studio</span>
        </div>

        <span className="text-outline">|</span>

        {Object.keys(ROLE_METADATA).map((key) => {
          const meta = ROLE_METADATA[key]
          const liveRole = roleMap[key]
          const isLoaded = Boolean(liveRole?.loaded || liveRole?.current_instance_id)
          const isActive = activeRole === key

          return (
            <div
              key={key}
              title={`${meta.modelName} (${liveRole?.configured_model_id || meta.modelId}): ${
                isActive ? 'ACTIVE IN GPU' : isLoaded ? 'RESIDENT' : 'STANDBY'
              }`}
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono transition-all ${
                isActive
                  ? 'bg-primary-container text-white font-bold shadow-sm'
                  : isLoaded
                  ? 'bg-surface-container-high text-primary font-semibold'
                  : 'bg-surface-container text-outline opacity-60'
              }`}
            >
              <span>{meta.modelName.split('-')[0]}</span>
              {isActive && <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-container-high pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[19px]">developer_board</span>
          </div>
          <div className="flex flex-col">
            <h3 className="font-headline-sm text-sm font-bold text-on-surface">
              LM Studio Sequential Model Runtime
            </h3>
            <span className="text-[11px] text-on-surface-variant font-mono">
              Port 1234 • Strict Single-Active Model Policy: {singleActivePolicy ? 'ENFORCED' : 'OFF'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold ${
              serverOnline
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                serverOnline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            {serverOnline ? 'SERVER ONLINE' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Sequential Model Transition Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {Object.entries(ROLE_METADATA).map(([roleKey, meta]) => {
          const liveRole = roleMap[roleKey]
          const isLoaded = Boolean(liveRole?.loaded || liveRole?.current_instance_id)
          const isActive = activeRole === roleKey

          return (
            <div
              key={roleKey}
              className={`p-3.5 rounded-xl border flex flex-col justify-between gap-2 transition-all ${
                isActive
                  ? 'bg-surface-container-low border-primary ring-2 ring-primary/20 shadow-sm'
                  : isLoaded
                  ? 'bg-surface-container-lowest border-surface-container-high'
                  : 'bg-surface-container-lowest/60 border-surface-container-high/60 opacity-75'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]" style={{ color: meta.color }}>
                    {meta.icon}
                  </span>
                  <span className="text-[11px] font-bold text-on-surface">{meta.stage}</span>
                </div>
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                    isActive
                      ? 'bg-primary text-white'
                      : isLoaded
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-surface-container text-outline'
                  }`}
                >
                  {isActive ? 'ACTIVE IN GPU' : isLoaded ? 'RESIDENT' : 'STANDBY'}
                </span>
              </div>

              <div className="flex flex-col gap-0.5">
                <span className="font-mono text-[13px] font-bold text-on-surface">
                  {meta.modelName}
                </span>
                <span className="font-mono text-[10px] text-outline truncate" title={liveRole?.configured_model_id || meta.modelId}>
                  {liveRole?.configured_model_id || meta.modelId}
                </span>
              </div>

              <div className="pt-2 border-t border-surface-container-high/60 flex items-center justify-between text-[10px] font-mono">
                <span className="text-outline">Health:</span>
                <span className="text-on-surface font-semibold">
                  {liveRole?.health_status || (serverOnline ? 'READY' : 'OFFLINE')}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

