import { useState, useEffect } from 'react'
import './EvaluationDashboard.css' // We can reuse the same styles or add custom ones

export default function MemoryMetrics() {
  const [accuracyReport, setAccuracyReport] = useState(null)
  const [feedbackScores, setFeedbackScores] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const [accRes, feedRes] = await Promise.all([
          fetch('http://localhost:8001/improve/accuracy-report'),
          fetch('http://localhost:8001/improve/feedback-scores')
        ])
        
        if (!accRes.ok || !feedRes.ok) {
          throw new Error('Failed to fetch from memory agent')
        }
        
        const accData = await accRes.json()
        const feedData = await feedRes.json()
        
        setAccuracyReport(accData)
        setFeedbackScores(feedData)
      } catch (err) {
        console.error(err)
        setError('Memory Agent is not running on port 8001 or there was an error fetching data.')
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [])

  if (loading) return <div className="tab-content"><div className="log-empty">Loading memory metrics...</div></div>
  if (error) return <div className="tab-content"><div className="log-empty" style={{color: '#ff3366'}}>{error}</div></div>
  if (!accuracyReport || !feedbackScores) return null

  const overallAccuracy = accuracyReport.latest_run?.overall_accuracy || accuracyReport.metrics?.overall_accuracy?.average || 0;

  return (
    <div className="tab-content">
      <div className="insights-grid">
        
        {/* Overall Accuracy */}
        <div className="insights-metrics-card">
          <div className="card-section-title">Memory Agent Accuracy</div>
          <div className="insights-metrics">
            <div className="ins-metric">
              <div className="ins-metric-val" style={{ color: overallAccuracy >= 0.7 ? '#00ff88' : '#ffaa00' }}>
                {(overallAccuracy * 100).toFixed(1)}%
              </div>
              <div className="ins-metric-label">Overall Accuracy</div>
            </div>
            <div className="ins-metric">
              <div className="ins-metric-val" style={{ color: '#00d9ff' }}>
                {accuracyReport.total_runs}
              </div>
              <div className="ins-metric-label">Total Runs Evaluated</div>
            </div>
          </div>
          <div className="ins-domain-row" style={{ marginTop: '20px' }}>
             <span className="ins-domain-label">Strongest Layer</span>
             <span className="ins-domain-val" style={{ color: '#00ff88' }}>{accuracyReport.strongest_layer || 'N/A'}</span>
          </div>
          <div className="ins-domain-row">
             <span className="ins-domain-label">Weakest Layer</span>
             <span className="ins-domain-val" style={{ color: '#ff6b35' }}>{accuracyReport.weakest_layer || 'N/A'}</span>
          </div>
        </div>

        {/* Retrieval Weights */}
        <div className="insights-results-card">
          <div className="card-section-title">Retrieval Weights (Feedback)</div>
          <div className="num-results-table">
            {Object.entries(feedbackScores.retrieval_weights || {}).map(([key, weight]) => (
              <div key={key} className="num-result-row">
                <span className="nr-key">{key}</span>
                <span className="nr-val">{(weight).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Metrics */}
        <div className="all-bars-card" style={{ gridColumn: '1 / -1' }}>
          <div className="card-section-title">Accuracy by Layer</div>
          <div className="all-bars">
            {Object.entries(accuracyReport.metrics || {}).map(([metricName, metricData], i) => {
              if (metricName === 'overall_accuracy') return null;
              const s = metricData.latest || 0;
              const c = s >= 0.9 ? '#00ff88' : s >= 0.8 ? '#00d9ff' : s >= 0.7 ? '#ffaa00' : '#ff3366';
              return (
                <div key={metricName} className="bar-row">
                  <span className="bar-layer-name">{metricName.replace('_', ' ')}</span>
                  <div className="anim-bar-bg" style={{flex: 1, margin: '0 10px', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px'}}>
                     <div className="anim-bar-fill" style={{ width: `${s * 100}%`, background: c, height: '100%', borderRadius: '4px' }} />
                  </div>
                  <span className="bar-layer-score" style={{ color: c, minWidth: '40px' }}>{(s * 100).toFixed(1)}%</span>
                </div>
              )
            })}
          </div>
        </div>

      </div>
    </div>
  )
}
