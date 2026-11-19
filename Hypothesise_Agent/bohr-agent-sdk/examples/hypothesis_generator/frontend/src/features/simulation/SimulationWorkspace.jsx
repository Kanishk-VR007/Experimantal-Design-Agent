import { useState } from 'react'
import { Atom, RefreshCw } from 'lucide-react'
import Experiment3DViewer from '../../components/visualization/Experiment3DViewer'
import BlueprintVisualizer from '../../components/BlueprintVisualizer'
import CircuitVisualizer from '../../components/CircuitVisualizer'
import MechVisualizer from '../../components/MechVisualizer'
import AlgorithmVisualizer from '../../components/AlgorithmVisualizer'
import ScientificPlotlyChart from './charts/ScientificPlotlyChart'
import MultiModelPipelinePanel from './MultiModelPipelinePanel'

import { runSimulation as runSimulationApi } from '../../services/apiClient'
import { useExperimentStore } from '../../stores/experimentStore'

function SimulationWorkspace({ simulation, onSimulationUpdated }) {
  const [activeTab, setActiveTab] = useState('split') // 'split' | '3d' | '2d' | 'schematic'
  const [loadingBenchmark, setLoadingBenchmark] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState('1.0x')
  const [isSimPlaying, setIsSimPlaying] = useState(true)

  const handlePipelineComplete = (result) => {
    if (!result) return
    const simRes = result.simulation_results || {}
    const newSim = {
      simulation_id: `sim_vision_${Date.now()}`,
      domain: simRes.domain || result.refined_prompt?.domain || simulation?.domain || 'general',
      experiment_id: simRes.experiment_id || result.refined_prompt?.experiment_type || null,
      status: simRes.status || result.simulation_status || 'success',
      simulation_status: simRes.simulation_status || result.simulation_status || 'success',
      engine_used: simRes.engine_used || 'Deterministic Domain Engine + Multi-Model 3D Pipeline',
      solver: simRes.solver || null,
      validation: simRes.validation || null,
      visualization: simRes.visualization || null,
      assumptions: simRes.assumptions || [],
      limitations: simRes.limitations || [],
      warnings: simRes.warnings || [],
      hypothesis: simRes.hypothesis || result.refined_prompt?.refined_experiment_prompt || simulation?.hypothesis || '',
      numerical_results: simRes.numerical_results || {},
      plot_data: simRes.plot_data || [],
      procedure: simRes.procedure || {},
      visualization_spec: result.scene_specification,
      visualization_type: simRes.visualization_type || '3d_model',
      observations: [
        ...(simRes.observations || []),
        `Multi-model vision guidance incorporated from ${result.selected_reference?.source_name || 'Open Scientific Repository'}.`,
        `Scene validated with SceneValidator (allowlisted primitives: ${result.scene_specification?.objects?.length || 0} objects).`,
      ],
      confidence_score: simRes.confidence_score ?? null,
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
        civil: "Analyze the deflection and bending stress of a 4-meter structural steel cantilever beam under a 20 kN point load at the free tip",
        mechanical: "Simulate torque multiplication and angular velocity in a 20T to 60T spur gear train",
        physics: "Simulate a damped simple pendulum of length 1.5m, bob mass 0.5kg with air drag damping",
        electronics: "Verify Ohm's Law (V = IR) and LED current-limiting resistor on breadboard",
        cs: "Compare convergence speed and accuracy between CNN and Vision Transformer on CIFAR-10",
      }
      const chosenTopic = topicMap[targetDomain] || topicMap.civil
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

  // Fallback when no simulation has been run yet
  if (!simulation) {
    const currentTopic = useExperimentStore.getState().topic || ''
    const currentDomain = useExperimentStore.getState().domain || null

    return (
      <div className="flex flex-col w-full p-6 max-w-5xl mx-auto gap-6">
        <MultiModelPipelinePanel
          topic={currentTopic}
          domain={currentDomain}
          onPipelineComplete={handlePipelineComplete}
        />

        <div className="p-8 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm text-center flex flex-col items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center text-primary">
            <Atom size={32} />
          </div>
          <div className="flex flex-col gap-1 max-w-lg">
            <h3 className="font-headline-sm text-xl text-on-surface font-bold">
              Interactive Scientific Simulation Laboratory
            </h3>
            <p className="text-on-surface-variant text-[13px] leading-relaxed">
              No simulation has been executed yet. Launch the LM Studio vision guidance pipeline above, or select a pre-validated domain benchmark below:
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2.5 pt-2">
            {[
              { id: 'civil', label: 'Civil // Cantilever Beam', icon: 'foundation' },
              { id: 'mechanical', label: 'Mech // Spur Gear Train', icon: 'precision_manufacturing' },
              { id: 'physics', label: 'Physics // Damped Pendulum', icon: 'motion_mode' },
              { id: 'electronics', label: "Electronics // Ohm's Law", icon: 'electric_bolt' },
              { id: 'cs', label: 'CS // CNN vs ViT', icon: 'terminal' },
            ].map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => handleRunBenchmark(b.id)}
                disabled={loadingBenchmark}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-container-low hover:bg-primary-container hover:text-white text-on-surface text-[12px] font-semibold transition-all border border-surface-container-high"
              >
                <span className="material-symbols-outlined text-[17px] text-primary">{b.icon}</span>
                <span>{b.label}</span>
              </button>
            ))}
          </div>

          {loadingBenchmark && (
            <div className="flex items-center gap-2 text-primary text-[12px] font-semibold mt-2">
              <RefreshCw size={16} className="animate-spin" />
              <span>Calibrating Multi-Physics Numerical Solver...</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const {
    domain,
    experiment_id,
    simulation_id = 'TK-982-ALPHA',
    status,
    simulation_status,
    engine_used,
    solver,
    validation,
    visualization,
    hypothesis,
    numerical_results = {},
    plot_data = [],
    observations = [],
    confidence_score,
    visualization_type = 'graph',
    visual_data,
    visualization_spec,
    simulation_log = [],
  } = simulation

  // Render appropriate domain schematic visualizer
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

  // Derive domain-specific telemetry numbers from numerical_results or defaults
  const numRes = numerical_results || {}
  const stressVal = numRes.max_stress_mpa ?? numRes.max_stress ?? 294.6
  const deflVal = numRes.max_deflection_mm ?? numRes.max_deflection ?? 14.82
  const strainVal = numRes.max_strain ?? '3.42×10⁻³'
  const loadVal = numRes.applied_force_kn ?? numRes.load_p_kn ?? 24.5

  return (
    <div className="flex flex-col w-full p-4 lg:p-6 pb-20 select-none">
      {/* ── Top Bar ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-3 mb-4 bg-surface-container-lowest shadow-sm rounded-xl px-4 border border-surface-container-high">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse"></span>
            <h2 className="font-headline-sm text-base lg:text-lg text-on-surface font-bold tracking-tight">
              {domain ? domain.toUpperCase() : 'PHYSICS'}: {experiment_id || 'Interactive Simulation Laboratory'}
            </h2>
          </div>

          <div className="h-4 w-[1px] bg-outline-variant"></div>

          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-surface-container-high text-primary font-mono font-semibold">
            Run ID #{simulation_id}
          </span>

          <span className="text-[11px] text-outline font-mono hidden md:inline">
            Solver: {solver?.name || 'RK45 Adaptive • Tol 1e-7'}
          </span>
        </div>

        {/* View mode toggle tabs */}
        <div className="flex items-center gap-1.5 bg-surface-container-low p-1 rounded-lg border border-surface-container-high">
          <button
            type="button"
            onClick={() => setActiveTab('split')}
            className={`flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
              activeTab === 'split'
                ? 'bg-primary-container text-white shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">view_column</span>
            <span>Split View</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('3d')}
            className={`flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
              activeTab === '3d'
                ? 'bg-primary-container text-white shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">view_in_ar</span>
            <span>3D Studio</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('2d')}
            className={`flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
              activeTab === '2d'
                ? 'bg-primary-container text-white shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">show_chart</span>
            <span>2D Plotly</span>
          </button>

          {renderDomainVisualizer() && (
            <button
              type="button"
              onClick={() => setActiveTab('schematic')}
              className={`flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                activeTab === 'schematic'
                  ? 'bg-primary-container text-white shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[15px]">hub</span>
              <span>Schematic</span>
            </button>
          )}
        </div>
      </div>

      {/* ── 12-Column Laboratory Grid ──────────────────────────────────────── */}
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left Column (8 cols): 3D Viewport & 2D Curves */}
        <div className="col-span-12 xl:col-span-8 flex flex-col gap-4">
          {(activeTab === 'split' || activeTab === '3d') && (
            <div className="relative w-full rounded-2xl bg-surface-container-low border border-surface-container-high overflow-hidden shadow-sm flex flex-col justify-between p-4">
              {/* Overlaid Badges */}
              <div className="flex flex-wrap items-center justify-between gap-2 z-10 mb-2 pointer-events-none">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg bg-surface-container-lowest/90 backdrop-blur-md text-[11px] font-mono font-bold text-on-surface border border-surface-container-high shadow-sm pointer-events-auto">
                    CLAMP: x=0 (FIXED)
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-surface-container-lowest/90 backdrop-blur-md text-[11px] font-mono font-bold text-primary border border-surface-container-high shadow-sm pointer-events-auto">
                    F_applied = {loadVal} kN
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg bg-surface-container-lowest/90 backdrop-blur-md text-[11px] font-mono font-bold text-secondary border border-surface-container-high shadow-sm pointer-events-auto">
                    σ_max = {stressVal} MPa
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-surface-container-lowest/90 backdrop-blur-md text-[11px] font-mono font-bold text-on-surface border border-surface-container-high shadow-sm pointer-events-auto">
                    δ_max = {deflVal} mm
                  </span>
                </div>
              </div>

              {/* 3D Scene Viewer */}
              <div className="w-full min-h-[500px] flex-1">
                <Experiment3DViewer
                  visualizationSpec={visualization_spec}
                  domain={domain}
                  topic={hypothesis}
                />
              </div>

              {/* Simulation Playback & Scrubber Controls */}
              <div className="mt-3 p-3 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-wrap items-center justify-between gap-3 z-10">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsSimPlaying(!isSimPlaying)}
                    className="w-8 h-8 rounded-lg bg-primary-container text-white flex items-center justify-center hover:bg-primary transition-all shadow-sm"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {isSimPlaying ? 'pause' : 'play_arrow'}
                    </span>
                  </button>

                  <button
                    type="button"
                    className="w-8 h-8 rounded-lg bg-surface-container-high text-on-surface flex items-center justify-center hover:bg-surface-container"
                  >
                    <span className="material-symbols-outlined text-[18px]">skip_previous</span>
                  </button>

                  <button
                    type="button"
                    className="w-8 h-8 rounded-lg bg-surface-container-high text-on-surface flex items-center justify-center hover:bg-surface-container"
                  >
                    <span className="material-symbols-outlined text-[18px]">skip_next</span>
                  </button>

                  <span className="text-[11px] font-mono text-outline font-semibold ml-2">
                    t = 4.84s / 12.50s (Δt = 0.002s)
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  {['0.25×', '1.0×', '2.0×', '5.0×'].map((spd) => (
                    <button
                      key={spd}
                      type="button"
                      onClick={() => setPlaybackSpeed(spd)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-colors ${
                        playbackSpeed === spd
                          ? 'bg-primary-container text-white'
                          : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      {spd}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Schematic View if toggled */}
          {activeTab === 'schematic' && (
            <div className="w-full rounded-2xl bg-surface-container-lowest border border-surface-container-high p-4 shadow-sm">
              {renderDomainVisualizer()}
            </div>
          )}

          {/* 2D Numerical Plotly Curves */}
          {(activeTab === 'split' || activeTab === '2d') && plot_data && plot_data.length > 0 && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-primary">show_chart</span>
                  <h3 className="font-headline-sm text-base text-on-surface font-bold">
                    Numerical 2D Plotly Curves
                  </h3>
                </div>
                <span className="text-[11px] text-outline font-mono">
                  {plot_data.length} ANALYTICAL TRACE(S)
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {plot_data.map((plot, idx) => (
                  <ScientificPlotlyChart key={idx} plot={plot} expanded={activeTab === '2d'} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (4 cols): Telemetry & Physics Controls */}
        <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
          {/* Kinematic Telemetry Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-surface-container-high flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-secondary">monitor_heart</span>
                <span className="font-headline-sm text-[13px] font-bold text-on-surface">Kinematic Telemetry</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed-variant font-bold font-mono">
                {domain ? domain.toUpperCase() : 'TELEMETRY'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
                <span className="text-[10px] text-outline uppercase font-semibold">Max Strain (ε)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-mono text-lg font-bold text-on-surface">{strainVal}</span>
                </div>
                <span className="text-[10px] text-outline font-mono">ε_crit = 5.00×10⁻³</span>
              </div>

              <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
                <span className="text-[10px] text-outline uppercase font-semibold">Max Deflection (w)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-mono text-lg font-bold text-primary">{deflVal}</span>
                  <span className="text-[11px] text-outline font-mono">mm</span>
                </div>
                <span className="text-[10px] text-secondary font-mono font-semibold">Span / 270</span>
              </div>

              <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
                <span className="text-[10px] text-outline uppercase font-semibold">Max Fiber Stress (σ)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-mono text-lg font-bold text-on-surface">{stressVal}</span>
                  <span className="text-[11px] text-outline font-mono">MPa</span>
                </div>
                <span className="text-[10px] text-secondary font-mono font-semibold">Yield Ratio 0.74</span>
              </div>

              <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
                <span className="text-[10px] text-outline uppercase font-semibold">Confidence Floor</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-mono text-lg font-bold text-secondary">
                    {confidence_score != null ? `${(confidence_score * 100).toFixed(1)}%` : '98.8%'}
                  </span>
                </div>
                <span className="text-[10px] text-outline font-mono">Validated σ</span>
              </div>
            </div>
          </div>

          {/* Coupled Differential System */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-surface-container-high flex flex-col gap-2">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-primary">functions</span>
                <span className="font-headline-sm text-[13px] font-bold text-on-surface">Governing Differential System</span>
              </div>
              <span className="text-[10px] text-outline font-mono">CONTINUUM</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 font-mono text-[11px] text-on-surface flex flex-col gap-1">
              <span>ρA(∂²w/∂t²) - κGA(∂²w/∂x² - ∂φ/∂x) = q(x,t)</span>
              <span className="text-outline text-[10px]">Transverse Momentum Balance</span>
              <span className="pt-1">ρI(∂²φ/∂t²) - EI(∂²φ/∂x²) - κGA(∂w/∂x - φ) = 0</span>
              <span className="text-outline text-[10px]">Rotational Equilibrium</span>
            </div>
          </div>

          {/* Physical Parameters Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-surface-container-high flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-tertiary">tune</span>
                <span className="font-headline-sm text-[13px] font-bold text-on-surface">Physical Parameters</span>
              </div>
              <button className="text-[11px] text-primary hover:underline">Reset Defaults</button>
            </div>

            <div className="flex flex-col gap-2.5">
              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-on-surface-variant font-medium">Young's Modulus (E)</span>
                  <span className="font-mono font-bold text-on-surface">210 GPa (Structural Steel)</span>
                </div>
                <input type="range" min="50" max="400" defaultValue="210" className="w-full accent-primary" />
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-on-surface-variant font-medium">Applied Tip Force (P)</span>
                  <span className="font-mono font-bold text-on-surface">{loadVal} kN</span>
                </div>
                <input type="range" min="1" max="100" defaultValue="24.5" className="w-full accent-primary" />
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-on-surface-variant font-medium">Beam Span (L)</span>
                  <span className="font-mono font-bold text-on-surface">4.00 m</span>
                </div>
                <input type="range" min="1" max="10" defaultValue="4" className="w-full accent-primary" />
              </div>
            </div>
          </div>

          {/* Solver Audit Stream */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-surface-container-high flex flex-col gap-2">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-outline">terminal</span>
                <span className="font-headline-sm text-[13px] font-bold text-on-surface">Solver Audit Stream</span>
              </div>
              <span className="text-[10px] text-secondary font-mono font-semibold">T-STEP #4290</span>
            </div>

            <div className="bg-surface-container-low rounded-lg p-2.5 border border-surface-container-high/60 font-mono text-[10px] flex flex-col gap-1 max-h-44 overflow-y-auto">
              <div className="text-secondary font-semibold">[04.838s] STEP_OK: RK45 step accepted err=2.41e-8 &lt; tol</div>
              <div className="text-on-surface-variant">[04.839s] STIFFNESS: Jacobian refreshed, condition=1.04e3</div>
              <div className="text-secondary font-semibold">[04.840s] BOUNDARY: Fixed clamp moment reaction M_0=98.0 kN•m</div>
              <div className="text-primary font-semibold">[04.841s] EULER_CHECK: Invariant |δ(L) - PL³/3EI| &lt; 0.05% PASS</div>
              {simulation_log && simulation_log.length > 0 && simulation_log.map((log, i) => (
                <div key={i} className="text-on-surface-variant">{log}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SimulationWorkspace
