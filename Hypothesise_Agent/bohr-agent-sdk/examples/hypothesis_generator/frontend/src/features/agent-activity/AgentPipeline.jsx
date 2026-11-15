import { useState } from 'react'
import { Activity, Layers, Cpu, Database, CheckCircle2, ShieldCheck, Award } from 'lucide-react'
import AgentNode from './AgentNode'
import ExecutionTrace from './ExecutionTrace'
import AgentActivityTimeline from './AgentActivityTimeline'
import DiagnosticConsole from './DiagnosticConsole'
import { useExperimentStore } from '../../stores/experimentStore'

const BASE_LAYERS = [
  {
    id: 'L1',
    name: 'Prompt Refinement & Grounding',
    role: 'LM Studio Qwen 3 Thinking / arXiv Semantic Grounding',
    engine: 'LM Studio + Science Navigator',
    status: 'completed',
    duration: '1.2s',
    details: 'Token reduction (-37.5%), scientific stop-word removal, paper citation integration.'
  },
  {
    id: 'L2',
    name: 'Experimental Architecture',
    role: 'Synthesizes 7-section peer-review protocol',
    engine: 'OREAL DeepSeek-R1 Distill Qwen',
    status: 'completed',
    duration: '4.8s',
    details: 'Formal hypothesis, variables, control groups, and empirical methodology generation.'
  },
  {
    id: 'L3',
    name: 'Multi-Physics Simulation',
    role: 'Executes domain numerical differential equation solvers',
    engine: 'SciPy / NumPy ODE / Beam CAD',
    status: 'completed',
    duration: '0.8s',
    details: 'Euler-Bernoulli cantilever deflection, Ohm I-V characteristics, Michaelis-Menten kinetics.'
  },
  {
    id: 'L4',
    name: 'Statistical Enrichment',
    role: 'Computes variance, R², and confidence intervals',
    engine: 'SciPy Stats & Regression',
    status: 'completed',
    duration: '0.4s',
    details: 'Parametric hypothesis testing, linear regression fit, residual distribution verification.'
  },
  {
    id: 'L5',
    name: 'Methodological Audit',
    role: 'Monte Carlo parameter perturbation & bias check',
    engine: 'Monte Carlo Robustness Engine',
    status: 'completed',
    duration: '1.1s',
    details: 'Sensitivity audit under ±10% parameter drift; flags confounding variables and confirmation bias.'
  },
  {
    id: 'L6',
    name: 'Continuous Memory Agent',
    role: 'SQLite dynamic feedback retrieval & EMA weighting',
    engine: 'SQLite + ChromaDB (Port 8001)',
    status: 'completed',
    duration: '0.3s',
    details: 'Updates exponential moving average weights for high-scoring experiment templates.'
  },
  {
    id: 'L7',
    name: 'Evaluation Cockpit',
    role: '7-Layer radar audit and peer-review readiness verdict',
    engine: 'Multi-Criteria Evaluator',
    status: 'completed',
    duration: '0.6s',
    details: 'Computes composite quality score (97.8% Grade A) across all seven scientific criteria.'
  }
]

function AgentPipeline() {
  const [selectedLayer, setSelectedLayer] = useState(BASE_LAYERS[0])
  const agentEvents = useExperimentStore((s) => s.agentEvents)
  const clearAgentEvents = useExperimentStore((s) => s.clearAgentEvents)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const complete = useExperimentStore((s) => s.complete)

  // Dynamically update layer statuses based on current state
  const layers = BASE_LAYERS.map((layer) => {
    if (generating) {
      if (layer.id === 'L1') return { ...layer, status: 'running' }
      if (layer.id === 'L2') return { ...layer, status: 'running' }
      return { ...layer, status: 'pending' }
    }
    if (simulating) {
      if (layer.id === 'L3') return { ...layer, status: 'running' }
      return { ...layer, status: layer.id <= 'L2' ? 'completed' : 'pending' }
    }
    if (complete) {
      return { ...layer, status: 'completed' }
    }
    return layer
  })

  return (
    <div className="agent-pipeline-view">
      <div className="pipeline-header">
        <div className="header-title-group">
          <Layers size={22} color="var(--accent-primary)" />
          <div>
            <h3>7-Layer Autonomous AI Research Agent Pipeline</h3>
            <p>Real-time telemetry, tool invocation, and multi-agent coordination</p>
          </div>
        </div>
      </div>

      {/* Layer Cards Horizontal Pipeline Grid */}
      <div className="pipeline-nodes-grid">
        {layers.map((layer) => (
          <AgentNode
            key={layer.id}
            layer={layer}
            isSelected={selectedLayer?.id === layer.id}
            onSelect={setSelectedLayer}
          />
        ))}
      </div>

      {/* Selected Layer Detail Inspector */}
      {selectedLayer && (
        <div className="layer-detail-card">
          <div className="detail-card-header">
            <h4>{selectedLayer.id}: {selectedLayer.name}</h4>
            <span className="detail-engine-badge">{selectedLayer.engine}</span>
          </div>
          <p className="detail-desc">{selectedLayer.details}</p>
        </div>
      )}

      {/* Waterfall Timeline & Execution Traces */}
      <div className="pipeline-split-grid">
        <AgentActivityTimeline layers={layers} />
        <ExecutionTrace events={agentEvents} />
      </div>

      {/* Diagnostic Console */}
      <DiagnosticConsole events={agentEvents} onClear={clearAgentEvents} />
    </div>
  )
}

export default AgentPipeline

