import { useState, useEffect } from 'react'
import { Sliders, RotateCcw, Play, Check } from 'lucide-react'
import { updateVisualization } from '../../services/apiClient'
import { useExperimentStore } from '../../stores/experimentStore'

function ParameterInspector({ simulation, onSimulationUpdated }) {
  const [params, setParams] = useState({})
  const [loading, setLoading] = useState(false)
  const [applied, setApplied] = useState(false)

  const domain = simulation?.domain || 'physics'
  const simulationId = simulation?.simulation_id || 'sim_default'

  // Extract initial parameters based on domain and simulation results
  useEffect(() => {
    if (simulation?.parameters) {
      setParams(simulation.parameters)
    } else if (domain === 'civil' || simulation?.type === 'cantilever_beam') {
      setParams({
        length_m: 4.0,
        load_kn: 20.0,
        youngs_modulus_gpa: 200.0,
        width_m: 0.2,
        height_m: 0.4
      })
    } else if (domain === 'electronics' || simulation?.type === 'ohms_law') {
      setParams({
        resistance_ohms: 100,
        voltage_max_v: 12,
        voltage_min_v: 0
      })
    } else if (domain === 'mechanical' || simulation?.type === 'spur_gears') {
      setParams({
        driver_teeth: 20,
        driven_teeth: 60,
        input_rpm: 1800,
        input_torque_nm: 25.0
      })
    } else if (domain === 'cs' || domain === 'computer_science') {
      setParams({
        nodes_count: 16,
        edge_probability: 0.35,
        execution_speed_ms: 120
      })
    } else {
      setParams({
        length_m: 1.5,
        mass_kg: 0.5,
        angle_deg: 30,
        damping: 0.05
      })
    }
  }, [simulation, domain])

  const handleSliderChange = (key, val) => {
    setParams((prev) => ({
      ...prev,
      [key]: val
    }))
    setApplied(false)
  }

  const handleReset = () => {
    if (simulation?.parameters) {
      setParams(simulation.parameters)
    }
    setApplied(false)
  }

  const handleApply = async () => {
    setLoading(true)
    try {
      const res = await updateVisualization(simulationId, { parameters: params })
      if (res && res.simulation) {
        if (onSimulationUpdated) {
          onSimulationUpdated(res.simulation)
        }
      }
      setApplied(true)
      setTimeout(() => setApplied(false), 2500)
    } catch (err) {
      console.warn('Parameter update fallback:', err)
      // If server does not have update endpoint active, update local simulation parameters
      if (onSimulationUpdated && simulation) {
        onSimulationUpdated({
          ...simulation,
          parameters: { ...params }
        })
      }
      setApplied(true)
      setTimeout(() => setApplied(false), 2000)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="parameter-inspector-card">
      <div className="param-header">
        <div className="title-area">
          <Sliders size={16} color="var(--accent-primary)" />
          <h4>Physical Parameter Controls</h4>
        </div>
        <button
          type="button"
          className="btn-icon-param"
          onClick={handleReset}
          title="Reset to baseline values"
          disabled={loading}
        >
          <RotateCcw size={14} />
        </button>
      </div>

      <div className="param-controls-list">
        {Object.entries(params).map(([key, val]) => {
          if (typeof val !== 'number') return null
          const min = val > 0 ? (val * 0.1).toFixed(2) : -100
          const max = val > 0 ? (val * 3.0).toFixed(2) : 100
          const step = (max - min) / 100

          return (
            <div key={key} className="param-field-item">
              <div className="param-label-row">
                <span className="param-key">{key.replace(/_/g, ' ')}</span>
                <span className="param-val-badge">{val}</span>
              </div>
              <input
                type="range"
                min={min}
                max={max}
                step={step > 0 ? step : 0.1}
                value={val}
                onChange={(e) => handleSliderChange(key, parseFloat(e.target.value))}
                className="param-slider"
                disabled={loading}
              />
            </div>
          )
        })}
      </div>

      <div className="param-actions">
        <button
          type="button"
          className="btn-apply-parameters"
          onClick={handleApply}
          disabled={loading}
        >
          {applied ? (
            <>
              <Check size={14} color="#10b981" />
              <span>Parameters Synchronized</span>
            </>
          ) : (
            <>
              <Play size={14} />
              <span>Apply &amp; Re-solve Simulation</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export default ParameterInspector

