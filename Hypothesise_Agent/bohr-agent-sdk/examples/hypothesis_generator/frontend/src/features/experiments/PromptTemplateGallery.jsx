import { Sparkles, Building2, Cog, Binary, Cpu, Atom } from 'lucide-react'

export const PROMPT_TEMPLATES = [
  {
    id: 'cs_nn',
    title: 'CNN vs Vision Transformer (CIFAR-10)',
    domain: 'cs',
    topic: 'Compare convergence speed, loss curves, and validation accuracy between ResNet-style CNN and Vision Transformer on image classification',
    badge: 'Comp Sci',
    badgeColor: '#8b5cf6'
  },
  {
    id: 'cs_dijkstra',
    title: 'Dijkstra Shortest Path & Graph Traversal',
    domain: 'cs',
    topic: "Analyze Dijkstra's shortest path and BFS exploration order on a weighted network graph with dynamic node costs",
    badge: 'Comp Sci',
    badgeColor: '#8b5cf6'
  },
  {
    id: 'cs_sorting',
    title: 'Sorting Dynamics: QuickSort vs MergeSort',
    domain: 'cs',
    topic: 'Benchmark QuickSort, MergeSort, and BubbleSort operations, comparison counts, and memory allocations from n=10 to n=500',
    badge: 'Comp Sci',
    badgeColor: '#8b5cf6'
  },
  {
    id: 'cantilever',
    title: 'Cantilever Beam Deflection & Stress',
    domain: 'civil',
    topic: 'Analyze the deflection and bending stress of a 4-meter structural steel cantilever beam under a 20 kN point load at the free tip',
    badge: 'Civil Eng',
    badgeColor: '#f59e0b'
  },
  {
    id: 'mech_gear',
    title: 'Spur Gear Train Torque & Speed Ratio',
    domain: 'mechanical',
    topic: 'Simulate torque multiplication and angular velocity ratio for a 20-tooth pinion driving a 60-tooth gear with 5 kW input power at 1800 RPM',
    badge: 'Mechanical',
    badgeColor: '#ec4899'
  },
  {
    id: 'ohms_law',
    title: "Ohm's Law & LED Breadboard Circuit",
    domain: 'electronics',
    topic: "Verify Ohm's Law (V = IR) and calculate current-limiting resistor for a 5V microcontroller LED blink circuit",
    badge: 'Electronics',
    badgeColor: '#06b6d4'
  },
  {
    id: 'pendulum',
    title: 'Damped Simple Pendulum Simulation',
    domain: 'physics',
    topic: 'Simulate a damped simple pendulum of length 1.5m, bob mass 0.5kg, and release angle 30 degrees with air drag damping',
    badge: 'Physics',
    badgeColor: '#38bdf8'
  },
  {
    id: 'ballistics',
    title: 'Ballistic Trajectory with Aerodynamic Drag',
    topic: 'Calculate the 2D projectile trajectory of a 2 kg sphere launched at 45 degrees with initial velocity 50 m/s under aerodynamic drag',
    domain: 'physics',
    badge: 'Physics',
    badgeColor: '#38bdf8'
  }
]

function PromptTemplateGallery({ onSelectTemplate, disabled }) {
  return (
    <div className="template-gallery">
      <div className="section-header" style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
        <Sparkles size={14} className="accent-icon" color="var(--accent-primary)" />
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Benchmark Scientific Templates (Click to Populate Domain &amp; Prompt):
        </span>
      </div>
      <div className="template-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '8px' }}>
        {PROMPT_TEMPLATES.map((tmpl) => (
          <div
            key={tmpl.id}
            data-template-id={tmpl.id}
            className="template-card"
            onClick={() => !disabled && onSelectTemplate(tmpl)}
            style={{
              cursor: disabled ? 'not-allowed' : 'pointer',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '10px 12px',
              background: 'var(--bg-card)',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)' }}>{tmpl.title}</span>
              <span
                style={{
                  fontSize: '0.68rem',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: `${tmpl.badgeColor}20`,
                  color: tmpl.badgeColor,
                  fontWeight: 600,
                }}
              >
                {tmpl.badge}
              </span>
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: 0, lineClamp: 2, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {tmpl.topic}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PromptTemplateGallery
