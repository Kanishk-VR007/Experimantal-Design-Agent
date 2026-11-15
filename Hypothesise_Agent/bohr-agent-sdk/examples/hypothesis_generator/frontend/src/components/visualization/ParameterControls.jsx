import React, { useState, useEffect } from 'react'

export function ParameterControls({ parameters = [], onUpdateParameters, isUpdating = false }) {
  const [paramValues, setParamValues] = useState(() => {
    const initial = {}
    parameters.forEach((p) => {
      initial[p.name] = p.value
    })
    return initial
  })

  useEffect(() => {
    const next = {}
    parameters.forEach((p) => {
      next[p.name] = p.value
    })
    setParamValues(next)
  }, [parameters])

  const handleChange = (name, val) => {
    setParamValues((prev) => ({ ...prev, [name]: val }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (onUpdateParameters) {
      onUpdateParameters(paramValues)
    }
  }

  if (!parameters || parameters.length === 0) return null

  return (
    <div className="vis-parameter-controls">
      <div className="vis-param-header">
        <h4>🎛️ Experimental Parameters</h4>
        <span className="vis-param-subtitle">Adjust variables and rerun the numerical solver</span>
      </div>

      <form onSubmit={handleSubmit} className="vis-param-form">
        <div className="vis-param-grid">
          {parameters.map((param) => {
            const currentVal = paramValues[param.name] ?? param.value
            const isRange = param.min_val !== null && param.max_val !== null

            return (
              <div key={param.name} className="vis-param-field">
                <div className="vis-param-label-row">
                  <label htmlFor={`param-${param.name}`}>{param.label}</label>
                  <span className="vis-param-val-readout">
                    {typeof currentVal === 'number' ? currentVal.toFixed(2) : currentVal}{' '}
                    {param.unit && <small>{param.unit}</small>}
                  </span>
                </div>

                {param.type === 'select' && param.options ? (
                  <select
                    id={`param-${param.name}`}
                    value={currentVal}
                    onChange={(e) => handleChange(param.name, e.target.value)}
                    className="vis-input vis-select"
                  >
                    {param.options.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                ) : isRange ? (
                  <div className="vis-slider-input-group">
                    <input
                      id={`param-${param.name}`}
                      type="range"
                      min={param.min_val}
                      max={param.max_val}
                      step={param.step || 0.1}
                      value={currentVal}
                      onChange={(e) => handleChange(param.name, parseFloat(e.target.value))}
                      className="vis-range-slider"
                    />
                    <input
                      type="number"
                      min={param.min_val}
                      max={param.max_val}
                      step={param.step || 0.1}
                      value={currentVal}
                      onChange={(e) => handleChange(param.name, parseFloat(e.target.value) || 0)}
                      className="vis-number-box"
                    />
                  </div>
                ) : (
                  <input
                    id={`param-${param.name}`}
                    type={typeof param.value === 'number' ? 'number' : 'text'}
                    value={currentVal}
                    onChange={(e) =>
                      handleChange(
                        param.name,
                        typeof param.value === 'number' ? parseFloat(e.target.value) || 0 : e.target.value
                      )
                    }
                    className="vis-input"
                  />
                )}

                {param.description && (
                  <small className="vis-param-desc">{param.description}</small>
                )}
              </div>
            )
          })}
        </div>

        <button
          type="submit"
          disabled={isUpdating}
          className="vis-btn vis-btn-rerun"
        >
          {isUpdating ? '⏳ Recomputing Model...' : '⚡ Rerun Numerical Simulation'}
        </button>
      </form>
    </div>
  )
}

