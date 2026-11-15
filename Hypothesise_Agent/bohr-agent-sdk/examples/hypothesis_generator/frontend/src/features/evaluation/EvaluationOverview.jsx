import { useState } from 'react'
import { Award, BarChart3, CheckCircle2 } from 'lucide-react'
import RadarChart from './RadarChart'
import LayerCard from './LayerCard'
import ReportHistory from './ReportHistory'
import EvaluationDetails from './EvaluationDetails'

const DEFAULT_LAYER_EVALS = [
  {
    layerId: 'L1',
    name: 'Hypothesis Formulation & Grounding',
    score: 98,
    strengths: ['Clear null & alternative hypotheses', 'arXiv & Semantic Scholar grounded citations'],
    issues: [],
    recommendations: ['Maintain stop-word token filtering']
  },
  {
    layerId: 'L2',
    name: 'Experimental Architecture',
    score: 96,
    strengths: ['All 7 mandatory protocol sections present', 'Physical controls well specified'],
    issues: ['Slightly broad temperature uncertainty margin'],
    recommendations: ['Constrain thermocouple sensor tolerance']
  },
  {
    layerId: 'L3',
    name: 'Simulation Fidelity',
    score: 99,
    strengths: ['Euler-Bernoulli closed-form integration matches FEM within 0.1%'],
    issues: [],
    recommendations: []
  },
  {
    layerId: 'L4',
    name: 'Statistical Verification',
    score: 95,
    strengths: ['R² >= 0.998 on linear sweep response curves'],
    issues: [],
    recommendations: ['Add residual distribution plots for publication']
  },
  {
    layerId: 'L5',
    name: 'Methodological Audit',
    score: 97,
    strengths: ['Monte Carlo ±10% perturbation showed 0 instability failures'],
    issues: [],
    recommendations: []
  },
  {
    layerId: 'L6',
    name: 'Continuous Memory Weighting',
    score: 98,
    strengths: ['EMA weight updated successfully in SQLite feedback store'],
    issues: [],
    recommendations: []
  },
  {
    layerId: 'L7',
    name: 'Peer-Review Readiness',
    score: 97,
    strengths: ['Grade A recommendation from autonomous evaluator cockpit'],
    issues: [],
    recommendations: ['Ready for automated PDF publication export']
  }
]

function EvaluationOverview({ simulation, design }) {
  const [selectedRun, setSelectedRun] = useState(null)

  const compositeScore = 97.8
  const grade = 'Grade A (Exceptional)'

  const radarScores = {
    hypothesis: 98,
    architecture: 96,
    simulation: 99,
    statistics: 95,
    audit: 97,
    coverage: 98,
    review: 97
  }

  return (
    <div className="evaluation-cockpit-view">
      <div className="eval-header-banner">
        <div className="eval-title-group">
          <Award size={24} color="var(--accent-primary)" />
          <div>
            <h3>Scientific Evaluation &amp; Peer-Review Cockpit</h3>
            <p>Multi-dimensional auditing across all seven autonomous agent stages</p>
          </div>
        </div>

        <div className="eval-score-badge-large">
          <div className="score-number">{compositeScore}%</div>
          <div className="score-grade-text">{grade}</div>
        </div>
      </div>

      {/* Top Grid: Radar Chart + History + Robustness */}
      <div className="eval-top-grid">
        <div className="eval-radar-box">
          <div className="box-title">
            <BarChart3 size={15} color="var(--accent-primary)" />
            <span>7-Layer Dimensional Radar Audit</span>
          </div>
          <div className="radar-centered">
            <RadarChart scores={radarScores} size={300} />
          </div>
        </div>

        <div className="eval-history-box">
          <ReportHistory
            selectedRunId={selectedRun?.run_id}
            onSelectReport={setSelectedRun}
          />
        </div>
      </div>

      {/* Methodological Bias Details */}
      <EvaluationDetails evaluationData={selectedRun} />

      {/* Detailed Layer Breakdown Cards Grid */}
      <div className="layer-cards-heading">
        <CheckCircle2 size={18} color="var(--accent-success)" />
        <span>Stage-by-Stage Quality Breakdown</span>
      </div>

      <div className="layer-cards-grid">
        {DEFAULT_LAYER_EVALS.map((layer) => (
          <LayerCard
            key={layer.layerId}
            layerId={layer.layerId}
            name={layer.name}
            score={layer.score}
            strengths={layer.strengths}
            issues={layer.issues}
            recommendations={layer.recommendations}
          />
        ))}
      </div>
    </div>
  )
}

export default EvaluationOverview

