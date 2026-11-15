import { Atom, FlaskConical, Building2, Cog, Cpu, Binary, Compass } from 'lucide-react'

export const DOMAINS = [
  { id: 'civil', label: 'Civil Eng', icon: Building2, color: '#f59e0b', desc: 'Euler-Bernoulli beams, deflection, bending stress, CAD blueprints' },
  { id: 'mechanical', label: 'Mechanical Eng', icon: Cog, color: '#ec4899', desc: 'Spur gear trains, speed/torque transmission, dynamics, stress' },
  { id: 'cs', label: 'Computer Science', icon: Binary, color: '#8b5cf6', desc: 'Deep neural networks, Dijkstra graphs, sorting complexity' },
  { id: 'electronics', label: 'Electronics', icon: Cpu, color: '#06b6d4', desc: "Ohm's Law, LED blink, voltage divider, breadboard circuitry" },
  { id: 'physics', label: 'Physics', icon: Atom, color: '#38bdf8', desc: 'Damped simple pendulum, ballistic trajectory, kinematics' },
  { id: 'chemistry', label: 'Chemistry', icon: FlaskConical, color: '#a855f7', desc: 'Spectrophotometry, Beer-Lambert law, reaction kinetics' },
]

function DomainSelector({ selectedDomain, onSelectDomain, disabled }) {
  return (
    <div className="domain-selector">
      <div className="section-label-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div className="section-label" style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          Target Engineering &amp; Scientific Domain <span style={{ color: 'var(--accent-primary)', fontSize: '0.75rem' }}>(Prevents Hallucination)</span>
        </div>
        {selectedDomain && (
          <button
            type="button"
            className="btn-clear-domain"
            onClick={() => onSelectDomain(null)}
            style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '0.75rem', cursor: 'pointer', textDecoration: 'underline' }}
          >
            Reset to Auto-Detect
          </button>
        )}
      </div>
      <div className="domain-chips-grid">
        {DOMAINS.map((d) => {
          const Icon = d.icon
          const isSelected = selectedDomain === d.id
          return (
            <button
              key={d.id}
              type="button"
              className={`domain-chip ${isSelected ? 'active' : ''}`}
              style={{
                '--chip-color': d.color,
                borderColor: isSelected ? d.color : undefined,
                background: isSelected ? `${d.color}20` : undefined,
                boxShadow: isSelected ? `0 0 12px ${d.color}35` : undefined,
              }}
              onClick={() => onSelectDomain(isSelected ? null : d.id)}
              disabled={disabled}
              title={d.desc}
            >
              <Icon size={16} color={isSelected ? d.color : 'var(--text-secondary)'} />
              <span style={{ fontWeight: isSelected ? 600 : 400 }}>{d.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default DomainSelector
