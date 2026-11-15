import { CheckCircle2, AlertTriangle, Lightbulb } from 'lucide-react'
import MetricBar from './MetricBar'

function LayerCard({ layerId, name, score, strengths = [], issues = [], recommendations = [] }) {
  return (
    <div className="layer-evaluation-card">
      <div className="card-top">
        <span className="layer-badge">{layerId}</span>
        <h4 className="layer-title">{name}</h4>
      </div>

      <MetricBar score={score} label="Layer Quality Score" />

      {strengths.length > 0 && (
        <div className="eval-detail-section strengths">
          <div className="detail-label">
            <CheckCircle2 size={13} color="var(--accent-success)" />
            <span>Strengths</span>
          </div>
          <ul>
            {strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {issues.length > 0 && (
        <div className="eval-detail-section issues">
          <div className="detail-label">
            <AlertTriangle size={13} color="var(--accent-warning)" />
            <span>Issues &amp; Vulnerabilities</span>
          </div>
          <ul>
            {issues.map((iss, i) => (
              <li key={i}>{iss}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="eval-detail-section recommendations">
          <div className="detail-label">
            <Lightbulb size={13} color="var(--accent-secondary)" />
            <span>Recommendations</span>
          </div>
          <ul>
            {recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default LayerCard

