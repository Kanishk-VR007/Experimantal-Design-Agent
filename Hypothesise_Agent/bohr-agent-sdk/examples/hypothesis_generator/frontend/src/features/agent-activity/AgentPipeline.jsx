import { useState } from 'react'
import { useExperimentStore } from '../../stores/experimentStore'
import { useModelStatus } from '../../hooks/useModelStatus'
import ModelRuntimeStatus from '../../components/ModelRuntimeStatus'
import ExperimentExecutionLog from '../../components/ExperimentExecutionLog'
import DataFreshnessIndicator from '../../components/DataFreshnessIndicator'

const AGENT_TEMPLATES = [
  {
    id: 'L1',
    code: 'AGT-01',
    name: 'Prompt Refinement & Grounding',
    role: 'Qwen 3 Thinking (2507) // Semantic Grounding',
    model: 'qwen/qwen3-4b-thinking-2507',
    roleKey: 'prompt_refiner',
    vram: '2.1 GB',
    stageMatch: 'prompt_refinement',
    details: 'Token reduction, scientific stop-word removal, paper citation integration.',
  },
  {
    id: 'L2',
    code: 'AGT-02',
    name: 'Visual Structure Analysis',
    role: 'Qwen 3 VL Thinking // Diagram Analyzer',
    model: 'qwen3-vl-4b-thinking',
    roleKey: 'vision_analyzer',
    vram: '2.4 GB',
    stageMatch: 'visual_analysis',
    details: 'Extracts geometric constraints, bounding topologies, and experimental coordinate apparatus.',
  },
  {
    id: 'L3',
    code: 'AGT-03',
    name: 'Experimental Architecture Synthesizer',
    role: 'DeepSeek R1 (0528) // Main Reasoner',
    model: 'deepseek/deepseek-r1-0528-qwen3-8b',
    roleKey: 'main_reasoner',
    vram: '4.8 GB',
    stageMatch: 'experimental_design',
    details: 'Synthesizes formal hypothesis, variables, control groups, and empirical methodology.',
  },
  {
    id: 'L4',
    code: 'AGT-04',
    name: 'Multi-Physics Differential Solver',
    role: 'SciPy / NumPy ODE // Numerical Continuum',
    model: 'Deterministic Domain Engine',
    roleKey: null,
    vram: '0.4 GB',
    stageMatch: 'ode_simulation',
    details: 'Executes Euler-Bernoulli cantilever deflection, Ohm I-V characteristics, and Michaelis-Menten kinetics.',
  },
  {
    id: 'L5',
    code: 'AGT-05',
    name: 'Statistical & Verification Auditor',
    role: 'SciPy Stats // Student-t Confidence Bounds',
    model: 'Scientific Validator Module',
    roleKey: null,
    vram: '0.2 GB',
    stageMatch: 'scientific_validation',
    details: 'Calculates empirical variance, R², dimensional consistency, and enforces strict anti-hallucination bounds.',
  },
  {
    id: 'L6',
    code: 'AGT-06',
    name: 'Continuous Memory & EMA Feedback',
    role: 'SQLite + ChromaDB // Port 8001 Enclave',
    model: 'Bohr Vector Memory Engine',
    roleKey: null,
    vram: '0.6 GB',
    stageMatch: 'memory_update',
    details: 'Updates exponential moving average weights for high-scoring experiment templates.',
  },
  {
    id: 'L7',
    code: 'AGT-07',
    name: 'Evaluation & Peer Readiness Cockpit',
    role: 'Multi-Criteria 7-Axis Auditor',
    model: 'Evaluation Engine v4.2',
    roleKey: null,
    vram: '0.3 GB',
    stageMatch: 'complete',
    details: 'Computes composite quality score across all seven scientific criteria.',
  },
]

function AgentPipeline() {
  const [selectedAgentId, setSelectedAgentId] = useState('L1')
  const executionStage = useExperimentStore((s) => s.executionStage)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const complete = useExperimentStore((s) => s.complete)
  const currentRunId = useExperimentStore((s) => s.currentRunId)

  const { modelStatus, serverOnline, activeRole } = useModelStatus(3000)

  // Compute live agent swarm states based on executionStage and LM Studio model manager
  const agentSwarm = AGENT_TEMPLATES.map((agent) => {
    let status = 'STANDBY'
    let progress = 0

    if (agent.roleKey && activeRole === agent.roleKey) {
      status = 'ACTIVE IN GPU'
      progress = 75
    } else if (executionStage === agent.stageMatch) {
      status = 'ACTIVE'
      progress = 50
    } else if (complete) {
      status = 'COMPLETED'
      progress = 100
    } else if (serverOnline && agent.roleKey) {
      const liveRole = modelStatus?.roles?.find((r) => r.role_key === agent.roleKey)
      if (liveRole?.loaded) {
        status = 'RESIDENT'
        progress = 100
      }
    }

    return {
      ...agent,
      status,
      progress,
    }
  })

  const selectedAgent = agentSwarm.find((a) => a.id === selectedAgentId) || agentSwarm[0]
  const activeCount = agentSwarm.filter((a) => a.status.includes('ACTIVE')).length

  return (
    <div className="flex flex-col w-full p-4 lg:p-6 pb-20 select-none gap-6">
      {/* ── Top Data Freshness Bar ────────────────────────────────────────── */}
      <DataFreshnessIndicator />

      {/* ── Title Banner ──────────────────────────────────────────────────── */}
      <section className="flex flex-col gap-3 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-primary-fixed/20 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 relative z-10">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-outline font-mono uppercase">
                Autonomous Swarm Architecture // {currentRunId || 'SYS-STANDBY'}
              </span>
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  generating || simulating ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
                }`}
              ></span>
            </div>
            <h1 className="font-headline-sm text-2xl lg:text-3xl font-bold text-on-surface tracking-tight">
              Autonomous Swarm Intelligence Engine
            </h1>
            <p className="text-[13px] text-on-surface-variant max-w-2xl">
              Live neural execution graph across 7 specialized autonomous research agents actively resolving non-equilibrium stochastic quantum manifolds.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
            <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high text-right">
              <span className="text-[10px] text-outline uppercase font-semibold block">Swarm State</span>
              <span className="text-[12px] font-bold text-primary font-mono">
                {generating || simulating ? 'EXECUTING RUN' : 'STANDBY IDLE'}
              </span>
            </div>

            <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high text-right">
              <span className="text-[10px] text-outline uppercase font-semibold block">Active Agents</span>
              <span className="text-[12px] font-bold text-secondary font-mono">
                {activeCount > 0 ? `${activeCount} Executing` : '7 Ready'}
              </span>
            </div>

            <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high text-right">
              <span className="text-[10px] text-outline uppercase font-semibold block">LM Studio</span>
              <span className="text-[12px] font-bold text-on-surface font-mono">
                {serverOnline ? 'ONLINE (Port 1234)' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── LM Studio Sequential Model Telemetry Panel ─────────────────────── */}
      <ModelRuntimeStatus />

      {/* ── 12-Column Mesh Grid ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column (8 cols): Inter-Agent Topology Graph */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-container-high pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-primary">polyline</span>
                <span className="font-headline-sm text-base font-bold text-on-surface">
                  Hyperbolic Latent Topology (nD-MDS)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-outline font-mono">
                  {currentRunId || 'GLOBAL MESH'}
                </span>
              </div>
            </div>

            {/* Interactive Graph Canvas / SVG Simulation Mesh */}
            <div className="relative w-full h-[440px] rounded-xl bg-surface-container-low border border-surface-container-high/60 overflow-hidden flex items-center justify-center p-4">
              <svg className="w-full h-full" viewBox="0 0 800 440" fill="none">
                <defs>
                  <pattern id="mesh-grid-ap" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#dce9ff" strokeWidth="0.8" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#mesh-grid-ap)" opacity="0.6" />

                {/* Connecting Inter-Agent Edges */}
                <path d="M 120 180 L 260 120" stroke="#2563eb" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
                <path d="M 260 120 L 420 160" stroke="#006591" strokeWidth="2.5" />
                <path d="M 420 160 L 560 120" stroke="#6a1edb" strokeWidth="2" />
                <path d="M 560 120 L 700 220" stroke="#16a34a" strokeWidth="2.5" />
                <path d="M 420 160 L 420 320" stroke="#39b8fd" strokeWidth="1.8" strokeDasharray="4 4" />
                <path d="M 420 320 L 260 300" stroke="#004ac6" strokeWidth="2" />
                <path d="M 260 300 L 120 180" stroke="#2563eb" strokeWidth="1.5" />

                {/* Agent Nodes */}
                {[
                  { id: 'L1', cx: 120, cy: 180, label: 'AGT-01 Qwen Thinking', color: '#2563eb', role: 'Refiner' },
                  { id: 'L2', cx: 260, cy: 120, label: 'AGT-02 Qwen VL', color: '#006591', role: 'Vision' },
                  { id: 'L3', cx: 420, cy: 160, label: 'AGT-03 DeepSeek R1', color: '#6a1edb', role: 'Reasoning' },
                  { id: 'L4', cx: 560, cy: 120, label: 'AGT-04 Physics Solver', color: '#16a34a', role: 'Continuum' },
                  { id: 'L5', cx: 700, cy: 220, label: 'AGT-05 Stat Validator', color: '#004ac6', role: 'Verification' },
                  { id: 'L6', cx: 420, cy: 320, label: 'AGT-06 ChromaDB', color: '#0284c7', role: 'Memory EMA' },
                  { id: 'L7', cx: 260, cy: 300, label: 'AGT-07 Evaluator', color: '#8343f4', role: 'Cockpit' },
                ].map((node) => {
                  const isSelected = selectedAgentId === node.id
                  return (
                    <g key={node.id} className="cursor-pointer group" onClick={() => setSelectedAgentId(node.id)}>
                      <circle
                        cx={node.cx}
                        cy={node.cy}
                        r={isSelected ? 30 : 26}
                        fill="#ffffff"
                        stroke={node.color}
                        strokeWidth={isSelected ? 4 : 2.5}
                        filter="drop-shadow(0 2px 8px rgba(0,0,0,0.06))"
                      />
                      <circle cx={node.cx} cy={node.cy} r={isSelected ? 12 : 10} fill={node.color} opacity="0.9" />
                      <text x={node.cx} y={node.cy + 42} textAnchor="middle" fill="#0b1c30" fontSize="11" fontWeight="700" fontFamily="Space Grotesk">
                        {node.label}
                      </text>
                      <text x={node.cx} y={node.cy + 55} textAnchor="middle" fill="#737686" fontSize="9" fontFamily="Inter">
                        {node.role}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>

            {/* Selected Node Inspector Details */}
            {selectedAgent && (
              <div className="p-4 rounded-xl bg-surface-container-low border border-surface-container-high/60 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary text-white">
                      {selectedAgent.code}
                    </span>
                    <span className="font-headline-sm text-sm font-bold text-on-surface">
                      {selectedAgent.name}
                    </span>
                  </div>
                  <span className="text-[11px] text-primary font-mono font-bold">
                    STATUS: {selectedAgent.status}
                  </span>
                </div>
                <div className="text-[12px] text-on-surface-variant font-medium">
                  Model: <span className="font-mono text-primary font-semibold">{selectedAgent.model}</span>
                </div>
                <p className="text-[12px] text-on-surface-variant leading-relaxed">
                  {selectedAgent.details}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column (4 cols): Swarm Roster & System Resources */}
        <div className="xl:col-span-4 flex flex-col gap-4">
          {/* Swarm Roster Card */}
          <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-secondary">groups</span>
                <span className="font-headline-sm text-sm font-bold text-on-surface">Swarm Roster</span>
              </div>
              <span className="text-[10px] font-mono text-outline">7 ROLES CONFIGURED</span>
            </div>

            <div className="flex flex-col gap-2.5 max-h-[380px] overflow-y-auto pr-1">
              {agentSwarm.map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => setSelectedAgentId(agent.id)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-1.5 ${
                    selectedAgentId === agent.id
                      ? 'bg-surface-container-low border-primary shadow-sm'
                      : 'bg-surface-container-lowest border-surface-container-high hover:bg-surface-container-low/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] font-bold text-on-surface truncate">{agent.name}</span>
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                        agent.status.includes('ACTIVE')
                          ? 'bg-primary text-white'
                          : agent.status === 'COMPLETED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-surface-container-high text-outline'
                      }`}
                    >
                      {agent.status}
                    </span>
                  </div>
                  <span className="text-[11px] text-outline font-mono truncate">{agent.model}</span>
                  <div className="w-full h-1 bg-surface-container-highest rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-300"
                      style={{ width: `${agent.progress}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Real-Time Event Log Stream ────────────────────────────────────── */}
      <section>
        <ExperimentExecutionLog maxHeight="260px" />
      </section>
    </div>
  )
}

export default AgentPipeline
