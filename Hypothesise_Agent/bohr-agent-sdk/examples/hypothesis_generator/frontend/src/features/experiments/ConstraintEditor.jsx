import { useState } from 'react'
import { Sliders, ChevronDown, ChevronUp } from 'lucide-react'

function ConstraintEditor({ constraints, onChange, disabled }) {
  const [expanded, setExpanded] = useState(false)

  const handleChange = (key, val) => {
    onChange({
      ...constraints,
      [key]: val
    })
  }

  return (
    <div className="constraint-editor">
      <button
        type="button"
        className="constraint-toggle-btn"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="toggle-left">
          <Sliders size={15} />
          <span>Advanced Experimental Constraints</span>
        </div>
        {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>

      {expanded && (
        <div className="constraint-fields-grid">
          <div className="form-field">
            <label>Operating Temperature (°C)</label>
            <input
              type="number"
              value={constraints.temperature ?? 25}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
              disabled={disabled}
              step="0.5"
            />
          </div>

          <div className="form-field">
            <label>Primary Material / Medium</label>
            <select
              value={constraints.material || 'Structural Steel (E=200 GPa)'}
              onChange={(e) => handleChange('material', e.target.value)}
              disabled={disabled}
            >
              <option value="Structural Steel (E=200 GPa)">Structural Steel (E=200 GPa)</option>
              <option value="Reinforced Concrete (E=30 GPa)">Reinforced Concrete (E=30 GPa)</option>
              <option value="Aluminum 6061 (E=69 GPa)">Aluminum 6061 (E=69 GPa)</option>
              <option value="Cast Iron (E=110 GPa)">Cast Iron (E=110 GPa)</option>
              <option value="FR-4 PCB Epoxy-Glass">FR-4 PCB Epoxy-Glass</option>
              <option value="Copper Alloy (E=117 GPa)">Copper Alloy (E=117 GPa)</option>
              <option value="Silicon / CMOS Substrate">Silicon / CMOS Substrate</option>
            </select>
          </div>

          <div className="form-field">
            <label>Boundary Conditions</label>
            <select
              value={constraints.boundaryConditions || 'Fixed-Free (Cantilever)'}
              onChange={(e) => handleChange('boundaryConditions', e.target.value)}
              disabled={disabled}
            >
              <option value="Fixed-Free (Cantilever)">Fixed-Free (Cantilever)</option>
              <option value="Simply Supported (Pin-Roller)">Simply Supported (Pin-Roller)</option>
              <option value="Fixed-Fixed (Clamped ends)">Fixed-Fixed (Clamped ends)</option>
              <option value="Closed Adiabatic Chamber">Closed Adiabatic Chamber</option>
              <option value="Isothermal Continuous Stirred Tank">Isothermal Continuous Stirred Tank</option>
            </select>
          </div>

          <div className="form-field">
            <label>Safety & Uncertainty Tolerance (±%)</label>
            <input
              type="number"
              value={constraints.uncertaintyTolerance ?? 5}
              onChange={(e) => handleChange('uncertaintyTolerance', parseFloat(e.target.value))}
              disabled={disabled}
              min="0.1"
              max="20"
              step="0.5"
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default ConstraintEditor

