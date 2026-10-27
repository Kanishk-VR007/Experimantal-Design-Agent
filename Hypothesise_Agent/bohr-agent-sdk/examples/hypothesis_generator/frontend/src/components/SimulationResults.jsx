import { useState } from 'react'
import Plot from 'react-plotly.js'
import CircuitVisualizer from './CircuitVisualizer'
import BlueprintVisualizer from './BlueprintVisualizer'
import MechVisualizer from './MechVisualizer'
import SampleTestVisualizer from './SampleTestVisualizer'
import './SimulationResults.css'

function SimulationResults({ simulation }) {
  const [expandedPlot, setExpandedPlot] = useState(null)

  if (!simulation) return null

  const {
    status,
    engine_used,
    domain,
    hypothesis,
    numerical_results,
    plot_data,
    observations,
    confidence_score,
    simulation_log,
    visualization_type = 'graph',
    visual_data,
  } = simulation

  // Build Plotly traces — supports single series and multi-series (extra_series)
  const getPlotlyTraces = (plot) => {
    const COLORS = ['#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

    const baseMode = plot.plot_type === 'line' ? 'lines' : 'markers'
    const traces = [
      {
        x: plot.x,
        y: plot.y,
        type: plot.plot_type === 'bar' ? 'bar' : 'scatter',
        mode: baseMode,
        name: plot.series_name || 'Data',
        line: { color: COLORS[0], width: 2.5 },
        marker: { color: COLORS[0], size: plot.plot_type === 'scatter' ? 6 : 4 },
      },
    ]

    if (plot.extra_series && plot.extra_series.length) {
      plot.extra_series.forEach((s, idx) => {
        traces.push({
          x: plot.x,
          y: s.y,
          type: 'scatter',
          mode: baseMode,
          name: s.name,
          line: { color: s.color || COLORS[(idx + 1) % COLORS.length], width: 2.5 },
          marker: { color: s.color || COLORS[(idx + 1) % COLORS.length], size: 4 },
        })
      })
    }
    return traces
  }

  const getPlotLayout = (plot, expanded = false) => ({
    title: { text: plot.title, font: { size: 13, color: '#e2e8f0' } },
    xaxis: { title: plot.x_label, showgrid: true, gridcolor: '#1e293b', color: '#94a3b8' },
    yaxis: { title: plot.y_label, showgrid: true, gridcolor: '#1e293b', color: '#94a3b8' },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(15,23,42,1)',
    font: { color: '#cbd5e1', size: 11 },
    legend: { font: { color: '#cbd5e1', size: 10 }, bgcolor: 'rgba(0,0,0,0)' },
    width: expanded ? 900 : undefined,
    height: expanded ? 520 : 380,
    margin: { l: 60, r: 30, t: 45, b: 60 },
    hovermode: 'closest',
  })

  const confidenceColor =
    confidence_score >= 0.8 ? '#10b981' :
    confidence_score >= 0.6 ? '#f59e0b' : '#ef4444'

  const domainIcon = {
    electronics: '⚡', circuit: '⚡', arduino: '⚡',
    chemistry: '🧪', biology: '🧬', biological: '🧬', physics: '⚛',
    computer_science: '🤖', cs: '🤖', machine_learning: '🤖',
    civil_engineering: '🏗', civil: '🏗', structural: '🏗',
    mechanical_engineering: '⚙️', mechanical: '⚙️', mech: '⚙️',
    general: '🔬',
  }[domain] || '🔬'

  return (
    <div className="simulation-results">
      <div className="results-header">
        <h2>🔬 Simulation Results</h2>
        <div className="results-badges">
          <span className={`status-badge status-${status}`}>
            {status === 'success' ? '✅' : status === 'fallback' ? '⚠️' : '❌'} {status}
          </span>
          <span className="engine-badge">⚙️ {engine_used.replace(/_/g, ' ')}</span>
          <span className="domain-badge">{domainIcon} {domain}</span>
        </div>
      </div>

      {/* Hypothesis */}
      <div className="sim-section hypothesis-section">
        <h3>💡 Hypothesis</h3>
        <p>{hypothesis}</p>
      </div>

      {/* Confidence Score */}
      <div className="sim-section confidence-section">
        <h3>📊 Confidence Score</h3>
        <div className="confidence-bar-container">
          <div className="confidence-bar"
            style={{ width: `${confidence_score * 100}%`, backgroundColor: confidenceColor }}>
            <span className="confidence-value">{(confidence_score * 100).toFixed(0)}%</span>
          </div>
        </div>
        <p className="confidence-description">
          {confidence_score >= 0.8 ? 'High confidence — results are reliable' :
           confidence_score >= 0.6 ? 'Moderate confidence — review assumptions' :
           'Low confidence — consider experimental validation'}
        </p>
      </div>

      {/* ── Interactive Circuit View (Electronics) ── */}
      {visualization_type === 'circuit' && visual_data && (
        <div className="sim-section">
          <h3>⚡ Virtual Circuit  <span style={{fontSize:'0.75rem', color:'#64748b', fontWeight:400}}>— hover components for details</span></h3>
          <CircuitVisualizer visualData={visual_data} />
        </div>
      )}

      {/* ── Blueprint View (Civil Engineering) ── */}
      {visualization_type === 'blueprint' && visual_data && (
        <div className="sim-section">
          <h3>🏗 Blueprint  <span style={{fontSize:'0.75rem', color:'#64748b', fontWeight:400}}>— hover elements for details</span></h3>
          <BlueprintVisualizer visualData={visual_data} />
        </div>
      )}

      {/* ── CAD / 3D Model View (Mechanical Engineering) ── */}
      {visualization_type === '3d_model' && visual_data && (
        <div className="sim-section">
          <h3>⚙️ Mechanical CAD  <span style={{fontSize:'0.75rem', color:'#64748b', fontWeight:400}}>— hover parts for specs</span></h3>
          <MechVisualizer visualData={visual_data} />
        </div>
      )}

      {/* ── Sample Testing View (Biology) ── */}
      {visualization_type === 'sample_testing' && visual_data && (
        <div className="sim-section">
          <h3>🧪 Sample Testing  <span style={{fontSize:'0.75rem', color:'#64748b', fontWeight:400}}>— hover wells for OD600 readings</span></h3>
          <SampleTestVisualizer visualData={visual_data} />
        </div>
      )}

      {/* Numerical Results */}
      {Object.keys(numerical_results).length > 0 && (
        <div className="sim-section numerical-section">
          <h3>📈 Numerical Results</h3>
          <div className="numerical-grid">
            {Object.entries(numerical_results).map(([key, value]) => (
              <div key={key} className="numerical-card">
                <div className="numerical-key">{key.replace(/_/g, ' ')}</div>
                <div className="numerical-value">
                  {typeof value === 'object' ? (
                    <dl className="num-nested">
                      {Object.entries(value).map(([k, v]) => (
                        <div key={k} className="num-row">
                          <dt>{k.replace(/_/g, ' ')}</dt>
                          <dd>{typeof v === 'number' ? v.toLocaleString() : String(v)}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <span>{typeof value === 'number' ? value.toFixed(4) : value}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plots (graphs for all domains, also shown alongside circuit for electronics) */}
      {plot_data && plot_data.length > 0 && (
        <div className="sim-section plots-section">
          <h3>📊 {visualization_type === 'circuit' ? 'Signal Analysis' : visualization_type === 'sample_testing' ? 'Growth Curves' : 'Visualization'}</h3>
          <div className="plots-grid">
            {plot_data.map((plot, index) => (
              <div key={index} className="plot-card">
                <Plot
                  data={getPlotlyTraces(plot)}
                  layout={getPlotLayout(plot, expandedPlot === index)}
                  config={{ displayModeBar: true, displaylogo: false,
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'] }}
                  style={{ width: '100%' }}
                />
                <button className="expand-plot-btn"
                  onClick={() => setExpandedPlot(expandedPlot === index ? null : index)}>
                  {expandedPlot === index ? '⬇ Collapse' : '⬆ Expand'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Observations */}
      {observations && observations.length > 0 && (
        <div className="sim-section observations-section">
          <h3>🔍 Observations</h3>
          <ul className="observations-list">
            {observations.map((obs, index) => (
              <li key={index}>{obs}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Simulation Log */}
      <details className="sim-section log-section">
        <summary>
          <h3>📝 Simulation Log ({simulation_log.length} entries)</h3>
        </summary>
        <div className="log-content">
          {simulation_log.map((entry, index) => (
            <div key={index} className="log-entry">
              <span className="log-index">{index + 1}</span>
              <span className="log-text">{entry}</span>
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}

export default SimulationResults
