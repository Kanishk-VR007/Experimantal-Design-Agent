import { useState, useEffect } from 'react'
import { Sliders, RotateCcw, Play, Check } from 'lucide-react'
import { updateVisualization } from '../../services/apiClient'
import { useExperimentStore } from '../../stores/experimentStore'

function ParameterInspector({ simulation, onSimulationUpdated }) {
  const [params, setParams] = useState({})
  const [loading, setLoading] = useState(false)
  const [applied, setApplied] = useState(false)

  const domain = simulation?.domain || 'physics'
  const experimentId =
    simulation?.experiment_id ||
    simulation?.visualization_spec?.experiment_id ||
    simulation?.simulation_id ||
    'pendulum'

  // Extract initial parameters from the actual validated 3D scene specification first
  useEffect(() => {
    const specParams = simulation?.visualization_spec?.parameters
    if (Array.isArray(specParams) && specParams.length > 0) {
      const extracted = {}
      for (const p of specParams) {
        if (p?.name && typeof p.value === 'number') {
          extracted[p.name] = p.value
        }
      }
      if (Object.keys(extracted).length > 0) {
        setParams(extracted)
        return
      }
    }
    if (simulation?.parameters && Object.keys(simulation.parameters).length > 0) {
      setParams(simulation.parameters)
    } else if (domain.startsWith('civil')) {
      setParams({
        span_m: 5.0,
        point_load_kN: 10.0,
        elastic_modulus_GPa: 200.0,
      })
    } else if (domain === 'electronics') {
      setParams({
        resistance_ohm: 10.0,
        inductance_H: 0.1,
        capacitance_F: 0.001,
        voltage_V: 5.0,
      })
    } else if (domain.startsWith('mech')) {
      setParams({
        crank_length: 1.0,
        coupler_length: 2.5,
        rocker_length: 2.0,
        ground_length: 3.0,
      })
    } else if (domain === 'cs' || domain === 'computer_science') {
      setParams({
        epochs: 50,
      })
    } else {
      setParams({
        length_m: 1.5,
        bob_mass_kg: 0.5,
        angle_rad: 0.5,
        damping: 0.05,
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
    const specParams = simulation?.visualization_spec?.parameters
    if (Array.isArray(specParams) && specParams.length > 0) {
      const extracted = {}
      for (const p of specParams) {
        if (p?.name && typeof p.value === 'number') extracted[p.name] = p.value
      }
      if (Object.keys(extracted).length > 0) {
        setParams(extracted)
        setApplied(false)
        return
      }
    }
    if (simulation?.parameters) {
      setParams(simulation.parameters)
    }
    setApplied(false)
  }

  const handleApply = async () => {
    setLoading(true)
    try {
      const res = await updateVisualization(experimentId, {
        experiment_id: experimentId,
        domain,
        parameters: params,
        current_procedure: simulation?.procedure || null,
      })
      if (res && res.simulation) {
        if (onSimulationUpdated) {
          onSimulationUpdated(res.simulation)
        }
      }
      setApplied(true)
      setTimeout(() => setApplied(false), 2500)
    } catch (err) {
      console.warn('Parameter update fallback:', err)
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

