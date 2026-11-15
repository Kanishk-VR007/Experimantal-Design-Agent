import { useState } from 'react'
import {
  Atom, BarChart3, Box, Sliders, Maximize2, Minimize2,
  CheckCircle2, AlertCircle, Info, RefreshCw
} from 'lucide-react'
import Experiment3DViewer from '../../components/visualization/Experiment3DViewer'
import BlueprintVisualizer from '../../components/BlueprintVisualizer'
import CircuitVisualizer from '../../components/CircuitVisualizer'
import MechVisualizer from '../../components/MechVisualizer'
import AlgorithmVisualizer from '../../components/AlgorithmVisualizer'
import ScientificPlotlyChart from './charts/ScientificPlotlyChart'
import ParameterInspector from './ParameterInspector'

import { runSimulation as runSimulationApi } from '../../services/apiClient'
import { useExperimentStore } from '../../stores/experimentStore'

function SimulationWorkspace({ simulation, onSimulationUpdated }) {
  const [activeTab, setActiveTab] = useState('split') // 'split' | '3d' | '2d' | 'schematic'
  const [fullscreen, setFullscreen] = useState(false)
  const [loadingBenchmark, setLoadingBenchmark] = useState(false)

  const handleRunBenchmark = async (targetDomain) => {
    setLoadingBenchmark(true)
    try {
      const topicMap = {
        cs: "Compare convergence speed and accuracy between CNN and Vision Transformer on CIFAR-10",
        civil: "Analyze deflection and bending stress of a 4-meter structural steel cantilever beam under 20 kN tip load",
        mechanical: "Simulate torque multiplication and angular velocity in a 20T to 60T spur gear train",
        electronics: "Verify Ohm's Law (V = IR) and LED current-limiting resistor on breadboard"
      }
      const chosenTopic = topicMap[targetDomain] || topicMap.cs
      const res = await runSimulationApi(chosenTopic, `Experimental protocol for ${chosenTopic}`, targetDomain)
      if (res && onSimulationUpdated) {
        onSimulationUpdated(res)
      }
    } catch (e) {
      console.error('Benchmark execution error:', e)
    } finally {
      setLoadingBenchmark(false)
    }
  }

  if (!simulation) {
    return (
      <div className="simulation-workspace-empty" style={{ padding: '40px 20px', textAlign: 'center', maxWidth: '680px', margin: '0 auto' }}>
        <Atom size={52} color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Interactive Scientific Simulation Workspace
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.6, marginBottom: '24px' }}>
          Execute multi-physics numerical solvers, inspect interactive 3D WebGL scenes (React Three Fiber), analyze 2D response curves, and examine physical parameter bounds.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'stretch' }}>
          <button
            type="button"
            className="btn-quick-sim"
            data-testid="btn-sim-cs"
            onClick={() => handleRunBenchmark('cs')}
            disabled={loadingBenchmark}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              padding: '12px 20px',
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25))',
              border: '1px solid #8b5cf6',
              borderRadius: '8px',
              color: '#f8fafc',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: loadingBenchmark ? 'wait' : 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {loadingBenchmark ? <RefreshCw size={16} className="spinner-rotate" /> : <Box size={16} color="#8b5cf6" />}
            <span>💻 Launch Computer Science Simulation (3D Neural Net &amp; Algorithm DAG)</span>
          </button>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            <button
              type="button"
              className="btn-quick-sim-sub"
              data-testid="btn-sim-civil"
              onClick={() => handleRunBenchmark('civil')}
              disabled={loadingBenchmark}
              style={{
                padding: '10px',
                background: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: '#cbd5e1',
                fontSize: '0.78rem',
                fontWeight: 500,
                cursor: loadingBenchmark ? 'wait' : 'pointer'
              }}
            >
              🏗️ Civil Beam Deflection
            </button>
            <button
              type="button"
              className="btn-quick-sim-sub"
              data-testid="btn-sim-mechanical"
              onClick={() => handleRunBenchmark('mechanical')}
              disabled={loadingBenchmark}
              style={{
                padding: '10px',
                background: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: '#cbd5e1',
                fontSize: '0.78rem',
                fontWeight: 500,
                cursor: loadingBenchmark ? 'wait' : 'pointer'
              }}
            >
              ⚙️ Mechanical Spur Gears
            </button>
            <button
              type="button"
              className="btn-quick-sim-sub"
              data-testid="btn-sim-electronics"
              onClick={() => handleRunBenchmark('electronics')}
              disabled={loadingBenchmark}
              style={{
                padding: '10px',
                background: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: '#cbd5e1',
                fontSize: '0.78rem',
                fontWeight: 500,
                cursor: loadingBenchmark ? 'wait' : 'pointer'
              }}
            >
              ⚡ Electronics Circuit
            </button>
          </div>
        </div>
      </div>
    )
  }

  const {
    domain,
    engine_used,
    hypothesis,
    numerical_results = {},
    plot_data = [],
    observations = [],
    confidence_score,
    visualization_type = 'graph',
    visual_data,
    visualization_spec,
    simulation_log = []
  } = simulation

  // Render appropriate domain SVG visualizer
  const renderDomainVisualizer = () => {
    switch (visualization_type) {
      case 'circuit':
        return <CircuitVisualizer data={visual_data} visualData={visual_data} />
      case 'blueprint':
        return <BlueprintVisualizer data={visual_data} visualData={visual_data} />
      case 'mechanical':
      case '3d_model':
        return <MechVisualizer data={visual_data} visualData={visual_data} />
      case 'algorithm':
      case 'neural_network':
      case 'cs':
      case 'graph':
        return <AlgorithmVisualizer data={visual_data} visualData={visual_data} />
      default:
        if (domain === 'cs' || domain === 'computer_science') {
          return <AlgorithmVisualizer data={visual_data} visualData={visual_data} />
        }
        return null
    }
  }

  return (
    <div className={`simulation-workspace-container ${fullscreen ? 'fullscreen-mode' : ''}`}>
      {/* Workspace Top Bar */}
      <div className="workspace-control-bar">
        <div className="workspace-meta-left">
          <div className="domain-pill-badge">
            <span className="dot" />
            <span>{domain ? domain.toUpperCase() : 'PHYSICS'}</span>
          </div>
          <span className="engine-name-label">Solver: {engine_used || 'SciPy ODE Engine'}</span>
          {confidence_score && (
            <span className="confidence-pill">
              Confidence: {(confidence_score * 100).toFixed(1)}%
            </span>
          )}
        </div>

        <div className="workspace-tabs-group">
          <button
            type="button"
            data-tab="split"
            className={`tab-btn ${activeTab === 'split' ? 'active' : ''}`}
            onClick={() => setActiveTab('split')}
          >
            Split View
          </button>
          <button
            type="button"
            data-tab="3d"
            className={`tab-btn ${activeTab === '3d' ? 'active' : ''}`}
            onClick={() => setActiveTab('3d')}
          >
            3D WebGL Studio
          </button>
          <button
            type="button"
            data-tab="2d"
            className={`tab-btn ${activeTab === '2d' ? 'active' : ''}`}
            onClick={() => setActiveTab('2d')}
          >
            2D Response Curves
          </button>
          {visual_data && (
            <button
              type="button"
              data-tab="schematic"
              className={`tab-btn ${activeTab === 'schematic' ? 'active' : ''}`}
              onClick={() => setActiveTab('schematic')}
            >
              Domain Schematic
            </button>
          )}
          <button
            type="button"
            className="btn-icon-fullscreen"
            onClick={() => setFullscreen(!fullscreen)}
            title={fullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {fullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        </div>
      </div>

      {/* Main Workspace Canvas Area */}
      <div className="workspace-main-content">
        <div className="canvas-view-container">
          {/* Split Mode: 3D Viewport + 2D Plot */}
          {activeTab === 'split' && (
            <div className="split-layout-grid">
              <div className="viewport-box primary-3d">
                <div className="box-header">
                  <Box size={14} color="var(--accent-primary)" />
                  <span>Interactive 3D WebGL Scene (React Three Fiber)</span>
                </div>
                <div className="viewer-inner-frame">
                  <Experiment3DViewer
                    visualizationSpec={visualization_spec}
                    domain={domain}
                    simulationId={simulation.simulation_id}
                  />
                </div>
              </div>

              <div className="viewport-box secondary-2d">
                <div className="box-header">
                  <BarChart3 size={14} color="var(--accent-secondary)" />
                  <span>Numerical 2D Plotly Curves</span>
                </div>
                <div className="plot-inner-frame">
                  {plot_data && plot_data.length > 0 ? (
                    <ScientificPlotlyChart plot={plot_data[0]} />
                  ) : renderDomainVisualizer() ? (
                    renderDomainVisualizer()
                  ) : (
                    <div className="no-plot-notice">No secondary 2D curves generated.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 3D Only Mode */}
          {activeTab === '3d' && (
            <div className="fullscreen-3d-box">
              <Experiment3DViewer
                visualizationSpec={visualization_spec}
                domain={domain}
                simulationId={simulation.simulation_id}
              />
            </div>
          )}

          {/* 2D Only Mode */}
          {activeTab === '2d' && (
            <div className="full-2d-plots-grid">
              {plot_data && plot_data.map((plot, i) => (
                <div key={i} className="standalone-plot-card">
                  <ScientificPlotlyChart plot={plot} expanded />
                </div>
              ))}
            </div>
          )}

          {/* Domain Schematic Only Mode */}
          {activeTab === 'schematic' && (
            <div className="schematic-viewport-box">
              {renderDomainVisualizer() || <div className="no-plot-notice">No domain schematic available.</div>}
            </div>
          )}
        </div>

        {/* Right Sidebar: Physical Parameter Controls */}
        <div className="workspace-parameter-drawer">
          <ParameterInspector
            simulation={simulation}
            onSimulationUpdated={onSimulationUpdated}
          />
        </div>
      </div>

      {/* Numerical Metrics Summary Bar */}
      {numerical_results && Object.keys(numerical_results).length > 0 && (
        <div className="numerical-metrics-summary-bar">
          <div className="metrics-label">
            <CheckCircle2 size={14} color="var(--accent-success)" />
            <span>Numerical Metrics:</span>
          </div>
          <div className="metrics-cards-row">
            {Object.entries(numerical_results).flatMap(([k, val]) => {
              if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
                return Object.entries(val).map(([subK, subVal]) => (
                  <div key={`${k}-${subK}`} className="metric-tag-chip">
                    <span className="metric-k">{subK.replace(/_/g, ' ')}:</span>
                    <span className="metric-v">
                      {typeof subVal === 'number' ? (Number.isInteger(subVal) ? subVal : subVal.toFixed(4)) : String(subVal)}
                    </span>
                  </div>
                ))
              }
              return (
                <div key={k} className="metric-tag-chip">
                  <span className="metric-k">{k.replace(/_/g, ' ')}:</span>
                  <span className="metric-v">
                    {typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(4)) : String(val)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Observations Box */}
      {observations && observations.length > 0 && (
        <div className="observations-banner">
          <Info size={16} color="var(--accent-secondary)" />
          <div className="obs-content">
            <span className="obs-title">Empirical Solver Observations:</span>
            <ul className="obs-list">
              {observations.map((obs, i) => (
                <li key={i}>{obs}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default SimulationWorkspace

