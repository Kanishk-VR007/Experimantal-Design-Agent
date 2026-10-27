import { useState } from 'react'
import './CircuitVisualizer.css'

// ─── Individual component symbols ──────────────────────────────────────────

function Resistor({ x, y }) {
  const w = 40, h = 16
  return (
    <g>
      <line x1={x - 30} y1={y} x2={x - w / 2} y2={y} stroke="#9ca3af" strokeWidth="2" />
      <line x1={x + w / 2} y1={y} x2={x + 30} y2={y} stroke="#9ca3af" strokeWidth="2" />
      <rect x={x - w / 2} y={y - h / 2} width={w} height={h}
        fill="#92400e" stroke="#f59e0b" strokeWidth="1.5" rx="2" />
      <line x1={x - 10} y1={y - h / 2} x2={x - 10} y2={y + h / 2} stroke="#ef4444" strokeWidth="2.5" opacity="0.8" />
      <line x1={x} y1={y - h / 2} x2={x} y2={y + h / 2} stroke="#fbbf24" strokeWidth="2.5" opacity="0.8" />
      <line x1={x + 10} y1={y - h / 2} x2={x + 10} y2={y + h / 2} stroke="#a3a3a3" strokeWidth="2.5" opacity="0.8" />
    </g>
  )
}

function LED({ x, y, color = 'red' }) {
  const fill = { red: '#ef4444', green: '#22c55e', blue: '#3b82f6', yellow: '#eab308', white: '#f8fafc' }[color] || '#ef4444'
  return (
    <g>
      {/* anode lead */}
      <line x1={x - 25} y1={y} x2={x - 12} y2={y} stroke="#9ca3af" strokeWidth="2" />
      {/* body triangle */}
      <polygon points={`${x - 12},${y - 13} ${x - 12},${y + 13} ${x + 9},${y}`}
        fill={fill} stroke={fill} strokeWidth="1" opacity="0.9" />
      {/* cathode bar */}
      <line x1={x + 9} y1={y - 13} x2={x + 9} y2={y + 13} stroke="#e2e8f0" strokeWidth="2.5" />
      {/* cathode lead */}
      <line x1={x + 9} y1={y} x2={x + 25} y2={y} stroke="#9ca3af" strokeWidth="2" />
      {/* light rays */}
      <line x1={x + 14} y1={y - 12} x2={x + 22} y2={y - 20} stroke={fill} strokeWidth="1.5" opacity="0.75" />
      <line x1={x + 18} y1={y - 4} x2={x + 28} y2={y - 10} stroke={fill} strokeWidth="1.5" opacity="0.75" />
    </g>
  )
}

function ArduinoUno({ x, y, width = 140, height = 210 }) {
  return (
    <g>
      {/* PCB body */}
      <rect x={x} y={y} width={width} height={height} fill="#00469a" stroke="#3b82f6" strokeWidth="2" rx="6" />
      <rect x={x + 4} y={y + 4} width={width - 8} height={height - 8} fill="#005ec6" rx="4" />
      {/* USB connector */}
      <rect x={x + width / 2 - 14} y={y - 9} width="28" height="14"
        fill="#374151" stroke="#6b7280" strokeWidth="1" rx="2" />
      {/* Text */}
      <text x={x + width / 2} y={y + height / 2 - 18} textAnchor="middle"
        fill="white" fontSize="13" fontWeight="bold">Arduino</text>
      <text x={x + width / 2} y={y + height / 2} textAnchor="middle"
        fill="#93c5fd" fontSize="11">Uno</text>
      {/* ATmega chip */}
      <rect x={x + width / 2 - 22} y={y + height / 2 + 14} width="44" height="26"
        fill="#1e3a5f" stroke="#3b82f6" strokeWidth="1" rx="2" />
      <text x={x + width / 2} y={y + height / 2 + 30} textAnchor="middle"
        fill="#93c5fd" fontSize="7">ATmega328P</text>
      {/* Pin labels on right side */}
      <circle cx={x + width} cy={y + 75} r="4" fill="#f97316" />
      <text x={x + width + 8} y={y + 79} fill="#f97316" fontSize="9">D13</text>
      <circle cx={x + width} cy={y + 135} r="4" fill="#6b7280" />
      <text x={x + width + 8} y={y + 139} fill="#6b7280" fontSize="9">GND</text>
    </g>
  )
}

function Battery({ x, y }) {
  return (
    <g>
      {/* Body */}
      <rect x={x - 26} y={y - 45} width="52" height="92" fill="#374151" stroke="#6b7280" strokeWidth="2" rx="5" />
      {/* Positive terminal cap */}
      <rect x={x - 10} y={y - 52} width="20" height="10" fill="#9ca3af" rx="2" />
      {/* +/- labels */}
      <text x={x} y={y - 30} textAnchor="middle" fill="#ef4444" fontSize="16" fontWeight="bold">+</text>
      <text x={x} y={y - 10} textAnchor="middle" fill="#6b7280" fontSize="10">━━━</text>
      <text x={x} y={y + 10} textAnchor="middle" fill="#6b7280" fontSize="10">━━━</text>
      <text x={x} y={y + 30} textAnchor="middle" fill="#94a3b8" fontSize="14" fontWeight="bold">−</text>
      {/* Negative terminal */}
      <line x1={x - 12} y1={y + 47} x2={x + 12} y2={y + 47} stroke="#6b7280" strokeWidth="4" />
    </g>
  )
}

function VoltageSource({ x, y }) {
  return (
    <g>
      <circle cx={x} cy={y} r="28" fill="#1e293b" stroke="#a855f7" strokeWidth="2" />
      <text x={x} y={y - 5} textAnchor="middle" fill="#c084fc" fontSize="18">~</text>
      <text x={x} y={y + 12} textAnchor="middle" fill="#e2e8f0" fontSize="9">VS</text>
      {/* terminals */}
      <line x1={x} y1={y - 28} x2={x} y2={y - 42} stroke="#ef4444" strokeWidth="2" />
      <text x={x + 6} y={y - 36} fill="#ef4444" fontSize="12">+</text>
      <line x1={x} y1={y + 28} x2={x} y2={y + 42} stroke="#3b82f6" strokeWidth="2" />
      <text x={x + 6} y={y + 44} fill="#3b82f6" fontSize="11">−</text>
    </g>
  )
}

function Capacitor({ x, y }) {
  return (
    <g>
      {/* leads */}
      <line x1={x - 30} y1={y} x2={x - 6} y2={y} stroke="#9ca3af" strokeWidth="2" />
      <line x1={x + 6} y1={y} x2={x + 30} y2={y} stroke="#9ca3af" strokeWidth="2" />
      {/* plates */}
      <line x1={x - 6} y1={y - 15} x2={x - 6} y2={y + 15} stroke="#e2e8f0" strokeWidth="3" />
      <line x1={x + 6} y1={y - 15} x2={x + 6} y2={y + 15} stroke="#e2e8f0" strokeWidth="3" />
    </g>
  )
}

function Inductor({ x, y }) {
  const bumps = 4
  const bumpR = 9
  const totalW = bumps * bumpR * 2
  const sx = x - totalW / 2
  let d = `M ${sx - 15} ${y} L ${sx} ${y}`
  for (let i = 0; i < bumps; i++) {
    const bx = sx + i * bumpR * 2 + bumpR
    d += ` A ${bumpR} ${bumpR} 0 0 1 ${bx + bumpR} ${y}`
  }
  d += ` L ${sx + totalW + 15} ${y}`
  return (
    <g>
      <path d={d} fill="none" stroke="#e2e8f0" strokeWidth="2.2" />
    </g>
  )
}

function Ground({ x, y }) {
  return (
    <g>
      <line x1={x} y1={y - 6} x2={x} y2={y + 4} stroke="#6b7280" strokeWidth="2" />
      <line x1={x - 16} y1={y + 4} x2={x + 16} y2={y + 4} stroke="#6b7280" strokeWidth="2.5" />
      <line x1={x - 10} y1={y + 10} x2={x + 10} y2={y + 10} stroke="#6b7280" strokeWidth="2" />
      <line x1={x - 5} y1={y + 16} x2={x + 5} y2={y + 16} stroke="#6b7280" strokeWidth="1.5" />
    </g>
  )
}

function PowerRail({ x, y, label }) {
  return (
    <g>
      <line x1={x} y1={y + 8} x2={x} y2={y + 22} stroke="#ef4444" strokeWidth="2" />
      <line x1={x - 14} y1={y + 8} x2={x + 14} y2={y + 8} stroke="#ef4444" strokeWidth="2.5" />
      <text x={x} y={y + 4} textAnchor="middle" fill="#fca5a5" fontSize="11" fontWeight="bold">{label}</text>
    </g>
  )
}

function OutputNode({ x, y, label }) {
  return (
    <g>
      <circle cx={x} cy={y} r="7" fill="#064e3b" stroke="#10b981" strokeWidth="2" />
      <circle cx={x} cy={y} r="2.5" fill="#a7f3d0" />
      <text x={x + 14} y={y + 4} fill="#10b981" fontSize="11" fontWeight="500">{label.split('\n')[0]}</text>
    </g>
  )
}

// ─── Component dispatcher ────────────────────────────────────────────────────

function ComponentEl({ comp, isHovered, onEnter, onLeave }) {
  const { type, x, y, width, height, label = '', orientation = 'horizontal', properties = {} } = comp
  const labelShort = label.split('\n')[0]
  const isVertical = orientation === 'vertical'

  // For vertical components, wrap in 90° rotation
  const wrapVertical = (children) => isVertical
    ? <g transform={`rotate(-90, ${x}, ${y})`}>{children}</g>
    : <>{children}</>

  return (
    <g
      style={{ cursor: 'pointer' }}
      opacity={isHovered ? 1 : 0.93}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {/* Hover glow */}
      {isHovered && <circle cx={x + (width || 0) / 2} cy={y + (height || 0) / 2}
        r="55" fill="rgba(255,255,255,0.04)" />}

      {/* Render component body */}
      {type === 'resistor' && wrapVertical(<Resistor x={x} y={y} />)}
      {type === 'led' && wrapVertical(<LED x={x} y={y} color={properties.color || 'red'} />)}
      {type === 'arduino_uno' && <ArduinoUno x={x} y={y} width={width || 140} height={height || 210} />}
      {type === 'battery' && <Battery x={x} y={y} />}
      {type === 'voltage_source' && <VoltageSource x={x} y={y} />}
      {type === 'capacitor' && wrapVertical(<Capacitor x={x} y={y} />)}
      {type === 'inductor' && wrapVertical(<Inductor x={x} y={y} />)}
      {type === 'ground' && <Ground x={x} y={y} />}
      {type === 'power' && <PowerRail x={x} y={y} label={labelShort} />}
      {type === 'output_node' && <OutputNode x={x} y={y} label={label} />}

      {/* Label (skip for types that draw their own) */}
      {!['arduino_uno', 'power', 'output_node'].includes(type) && (
        <text
          x={type === 'ground' ? x + 20 : x}
          y={isVertical ? y + 46 : y - 20}
          textAnchor={type === 'ground' ? 'start' : 'middle'}
          fill="#cbd5e1"
          fontSize="10"
        >
          {labelShort}
        </text>
      )}
      {/* Second label line */}
      {label.includes('\n') && !['arduino_uno', 'power', 'output_node'].includes(type) && (
        <text
          x={x}
          y={isVertical ? y + 58 : y + 34}
          textAnchor="middle"
          fill="#94a3b8"
          fontSize="9"
        >
          {label.split('\n')[1]}
        </text>
      )}
    </g>
  )
}

// ─── Wire renderer ───────────────────────────────────────────────────────────

function WireEl({ wire }) {
  const { path = [], color = '#9ca3af', label = '' } = wire
  if (path.length < 2) return null
  const pts = path.map(([px, py]) => `${px},${py}`).join(' ')
  const mid = path[Math.floor(path.length / 2)]
  return (
    <g>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
      {/* Junction dot at each intermediate point */}
      {path.slice(1, -1).map(([px, py], i) => (
        <circle key={i} cx={px} cy={py} r="3" fill={color} />
      ))}
      {label && (
        <text x={mid[0]} y={mid[1] - 7} textAnchor="middle" fill={color}
          fontSize="9" opacity="0.85">{label}</text>
      )}
    </g>
  )
}

// ─── Hover tooltip ────────────────────────────────────────────────────────────

function Tooltip({ comp, canvasWidth }) {
  if (!comp) return null
  const { x, y, label = '', type, properties = {} } = comp
  const entries = Object.entries(properties)
  const tipW = 190
  const tipH = Math.max(80, entries.length * 18 + 52)
  // Flip to left if near right edge
  const tx = x + 70 > canvasWidth - tipW ? x - tipW - 10 : x + 60
  const ty = Math.max(8, y - 20)

  return (
    <foreignObject x={tx} y={ty} width={tipW} height={tipH}>
      <div className="cv-tooltip">
        <div className="cv-tooltip-title">{label.replace('\n', ' ')}</div>
        <div className="cv-tooltip-type">{type.replace(/_/g, ' ')}</div>
        {entries.map(([k, v]) => (
          <div key={k} className="cv-tooltip-row">
            <span className="cv-tooltip-key">{k.replace(/_/g, ' ')}</span>
            <span className="cv-tooltip-val">{String(v)}</span>
          </div>
        ))}
      </div>
    </foreignObject>
  )
}

// ─── Main CircuitVisualizer component ────────────────────────────────────────

function CircuitVisualizer({ visualData }) {
  const [hovered, setHovered] = useState(null)

  if (!visualData) return null

  const {
    title = 'Circuit Diagram',
    width = 700,
    height = 400,
    components = [],
    wires = [],
  } = visualData

  const hoveredComp = hovered ? components.find(c => c.id === hovered) : null

  return (
    <div className="cv-wrapper">
      {/* Header */}
      <div className="cv-header">
        <span className="cv-badge">⚡ Interactive Circuit</span>
        <span className="cv-title">{title}</span>
        <span className="cv-hint">Hover over components for details</span>
      </div>

      {/* SVG canvas */}
      <div className="cv-canvas-outer">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="cv-svg"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Dark PCB background */}
          <rect width={width} height={height} fill="#0d1117" rx="10" />

          {/* Subtle dot grid */}
          <defs>
            <pattern id="cv-grid" width="22" height="22" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="0.7" fill="#1e2d3d" />
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#cv-grid)" rx="10" />

          {/* Wires — drawn first (behind components) */}
          {wires.map((w, i) => <WireEl key={i} wire={w} />)}

          {/* Components */}
          {components.map(comp => (
            <ComponentEl
              key={comp.id}
              comp={comp}
              isHovered={hovered === comp.id}
              onEnter={() => setHovered(comp.id)}
              onLeave={() => setHovered(null)}
            />
          ))}

          {/* Tooltip overlay */}
          {hoveredComp && (
            <Tooltip comp={hoveredComp} canvasWidth={width} />
          )}
        </svg>
      </div>

      {/* Component legend */}
      <div className="cv-legend">
        {components.filter(c => c.type !== 'ground' && c.type !== 'power').map(c => (
          <div
            key={c.id}
            className={`cv-legend-item ${hovered === c.id ? 'active' : ''}`}
            onMouseEnter={() => setHovered(c.id)}
            onMouseLeave={() => setHovered(null)}
          >
            <span className="cv-legend-id">{c.id}</span>
            <span className="cv-legend-label">{c.label?.replace('\n', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default CircuitVisualizer
