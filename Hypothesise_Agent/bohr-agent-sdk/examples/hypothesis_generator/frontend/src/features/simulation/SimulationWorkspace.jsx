import { useState } from 'react'
import {
  Atom, BarChart3, Box, Sliders, Maximize2, Minimize2,
  CheckCircle2, AlertCircle, Info, RefreshCw, Maximize, Minimize,
  ChevronDown, ChevronUp
} from 'lucide-react'
import Experiment3DViewer from '../../components/visualization/Experiment3DViewer'
import BlueprintVisualizer from '../../components/BlueprintVisualizer'
import CircuitVisualizer from '../../components/CircuitVisualizer'
import MechVisualizer from '../../components/MechVisualizer'
import AlgorithmVisualizer from '../../components/AlgorithmVisualizer'
import ScientificPlotlyChart from './charts/ScientificPlotlyChart'
import ParameterInspector from './ParameterInspector'
import MultiModelPipelinePanel from './MultiModelPipelinePanel'

import { runSimulation as runSimulationApi } from '../../services/apiClient'
import { useExperimentStore } from '../../stores/experimentStore'

function SimulationWorkspace({ simulation, onSimulationUpdated }) {
  const [activeTab, setActiveTab] = useState('split') // 'split' | '3d' | '2d' | 'schematic'
  const [fullscreen, setFullscreen] = useState(false)
  const [isExpanded3D, setIsExpanded3D] = useState(false)
  const [showDrawer, setShowDrawer] = useState(true)
  const [showBottomPanels, setShowBottomPanels] = useState(false)
  const [loadingBenchmark, setLoadingBenchmark] = useState(false)

  const handlePipelineComplete = (result) => {
    if (!result) return
    const newSim = {
      simulation_id: `sim_vision_${Date.now()}`,
      domain: result.refined_prompt?.domain || simulation?.domain || 'general',
      engine_used: 'Deterministic Domain Engine + Multi-Model 3D Pipeline',
      hypothesis: result.refined_prompt?.refined_experiment_prompt || simulation?.hypothesis || '',
      numerical_results: result.simulation_results?.numerical_results || {},
      plot_data: result.simulation_results?.plot_data || [],
      procedure: result.simulation_results?.procedure || {},
      visualization_spec: result.scene_specification,
      visualization_type: '3d_model',
      observations: [
        `Multi-model vision guidance incorporated from ${result.selected_reference?.source_name || 'Open Scientific Repository'}.`,
        `Scene validated with SceneValidator (allowlisted primitives: ${result.scene_specification?.objects?.length || 0} objects).`,
      ],
      confidence_score: 0.96,
      visual_reconstruction_instructions: result.visual_reconstruction_instructions,
      selected_reference: result.selected_reference,
    }
    if (onSimulationUpdated) {
      onSimulationUpdated(newSim)
    }
  }

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
    const currentTopic = useExperimentStore.getState().topic || ''
    const currentDomain = useExperimentStore.getState().domain || null

    return (
      <div className="simulation-workspace-empty" style={{ padding: '24px 20px', maxWidth: '820px', margin: '0 auto' }}>
        <MultiModelPipelinePanel
          topic={currentTopic}
          domain={currentDomain}
          onPipelineComplete={handlePipelineComplete}
        />

        <div style={{ textAlign: 'center', marginTop: '20px', marginBottom: '24px' }}>
          <Atom size={44} color="var(--accent-primary)" style={{ marginBottom: '12px' }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Interactive Scientific Simulation Workspace
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
            Or immediately run pre-computed domain solver benchmarks:
          </p>
        </div>

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
            onClick={() => {
              setActiveTab('split')
              setIsExpanded3D(false)
            }}
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
            onClick={() => {
              setActiveTab('2d')
              setIsExpanded3D(false)
            }}
          >
            2D Response Curves
          </button>
          {visual_data && (
            <button
              type="button"
              data-tab="schematic"
              className={`tab-btn ${activeTab === 'schematic' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('schematic')
                setIsExpanded3D(false)
              }}
            >
              Domain Schematic
            </button>
          )}

          {/* Quick Expand Toggle for 3D Studio */}
          {activeTab === '3d' && (
            <button
              type="button"
              className={`tab-btn expand-tab-btn ${isExpanded3D ? 'active' : ''}`}
              onClick={() => setIsExpanded3D((p) => !p)}
              title={isExpanded3D ? 'Restore Standard Height' : 'Expand 3D Studio to Full Screen Height'}
              style={{
                color: isExpanded3D ? '#00f0ff' : '#94a3b8',
                borderColor: isExpanded3D ? 'rgba(0, 240, 255, 0.4)' : undefined,
                background: isExpanded3D ? 'rgba(0, 240, 255, 0.12)' : undefined,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              {isExpanded3D ? <Minimize size={13} /> : <Maximize size={13} />}
              <span>{isExpanded3D ? 'Standard Height' : 'Expand 3D View'}</span>
            </button>
          )}

          {/* Sidebar Drawer Toggle Button */}
          <button
            type="button"
            className={`tab-btn drawer-toggle-btn ${!showDrawer ? 'active' : ''}`}
            onClick={() => setShowDrawer((p) => !p)}
            title={showDrawer ? 'Hide Parameter Drawer (Wider 3D View)' : 'Show Parameter Drawer'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Sliders size={13} />
            <span>{showDrawer ? 'Hide Drawer' : 'Show Drawer'}</span>
          </button>

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
          <MultiModelPipelinePanel
            topic={hypothesis || useExperimentStore.getState().topic}
            domain={domain}
            compact={activeTab === '3d' || isExpanded3D}
            onPipelineComplete={handlePipelineComplete}
          />

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
                    isExpanded={false}
                    onToggleExpand={() => {
                      setActiveTab('3d')
                      setIsExpanded3D(true)
                    }}
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
            <div className={`fullscreen-3d-box ${isExpanded3D ? 'is-expanded' : ''}`}>
              <Experiment3DViewer
                visualizationSpec={visualization_spec}
                domain={domain}
                simulationId={simulation.simulation_id}
                isExpanded={isExpanded3D}
                onToggleExpand={() => setIsExpanded3D((p) => !p)}
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
        <div className={`workspace-parameter-drawer ${!showDrawer ? 'is-collapsed' : ''}`}>
          <div className="drawer-close-bar" style={{ padding: '6px 12px', display: 'flex', justifyContent: 'flex-end', borderBottom: '1px solid var(--border)' }}>
            <button
              type="button"
              onClick={() => setShowDrawer(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.72rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
              title="Collapse Drawer for Maximum Canvas Width"
            >
              <span>Collapse Sidebar ✕</span>
            </button>
          </div>
          <ParameterInspector
            simulation={simulation}
            onSimulationUpdated={onSimulationUpdated}
          />
        </div>
      </div>

      {/* Collapsible Ribbon for Metrics & Solver Observations */}
      {((numerical_results && Object.keys(numerical_results).length > 0) || (observations && observations.length > 0)) && (
        <div className="bottom-panels-toggle-bar">
          <button
            type="button"
            className="bottom-panels-toggle-btn"
            onClick={() => setShowBottomPanels((p) => !p)}
            title="Toggle visibility of metrics and solver observations"
          >
            {showBottomPanels ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <ChevronDown size={13} />
                Hide Numerical Metrics &amp; Observations Panel ▾
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <ChevronUp size={13} />
                Show Numerical Metrics &amp; Solver Observations ({Object.keys(numerical_results || {}).length} metrics) ▴
              </span>
            )}
          </button>
        </div>
      )}

      {/* Collapsible Content Area */}
      {showBottomPanels && (
        <div className="workspace-bottom-details-group">
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
      )}
    </div>
  )
}

export default SimulationWorkspace

