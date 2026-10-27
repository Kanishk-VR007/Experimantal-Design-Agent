import { useState } from 'react'
import './MechVisualizer.css'

// ─── Part renderers ─────────────────────────────────────────────────────────

function GearPart({ part }) {
  const { cx, cy, r, teeth = 20 } = part
  const toothDepth = Math.max(4, r * 0.12)
  const toothAngle = (2 * Math.PI) / teeth

  // Build gear outline path
  const points = []
  for (let i = 0; i < teeth; i++) {
    const a1 = i * toothAngle
    const a2 = a1 + toothAngle * 0.35
    const a3 = a1 + toothAngle * 0.5
    const a4 = a1 + toothAngle * 0.85
    points.push(`${cx + (r - toothDepth) * Math.cos(a1)},${cy + (r - toothDepth) * Math.sin(a1)}`)
    points.push(`${cx + r * Math.cos(a2)},${cy + r * Math.sin(a2)}`)
    points.push(`${cx + r * Math.cos(a3)},${cy + r * Math.sin(a3)}`)
    points.push(`${cx + (r - toothDepth) * Math.cos(a4)},${cy + (r - toothDepth) * Math.sin(a4)}`)
  }

  const dir = part.direction === 'ccw' ? -1 : 1
  return (
    <g>
      <polygon points={points.join(' ')} fill="#1e293b" stroke="#60a5fa" strokeWidth="1.5" />
      {/* Hub */}
      <circle cx={cx} cy={cy} r={r * 0.2} fill="#334155" stroke="#94a3b8" strokeWidth="1.5" />
      {/* Shaft hole */}
      <circle cx={cx} cy={cy} r={r * 0.08} fill="#0f172a" stroke="#475569" strokeWidth="1" />
      {/* Pitch circle (dashed) */}
      <circle cx={cx} cy={cy} r={r - toothDepth / 2} fill="none"
        stroke="#3b82f6" strokeWidth="0.8" strokeDasharray="4 3" opacity="0.5" />
      {/* Direction arrow */}
      <path
        d={`M ${cx + r * 0.5} ${cy - dir * 4} A ${r * 0.5} ${r * 0.5} 0 0 ${dir > 0 ? 1 : 0} ${cx + r * 0.35} ${cy + dir * r * 0.35}`}
        fill="none" stroke="#a855f7" strokeWidth="1.5" markerEnd="url(#mechArrow)" opacity="0.7" />
    </g>
  )
}

function ShaftPart({ part }) {
  const { cx, cy, length = 60 } = part
  return (
    <g>
      <rect x={cx - 6} y={cy - length / 2} width="12" height={length}
        fill="#475569" stroke="#94a3b8" strokeWidth="1.5" rx="2" />
      {/* Centre line */}
      <line x1={cx} y1={cy - length / 2 - 8} x2={cx} y2={cy + length / 2 + 8}
        stroke="#64748b" strokeWidth="0.8" strokeDasharray="8 4" />
    </g>
  )
}

function CrossSection({ part }) {
  const { cx, cy, r } = part
  return (
    <g>
      {/* Outer circle */}
      <circle cx={cx} cy={cy} r={r} fill="#1e293b" stroke="#e2e8f0" strokeWidth="2" />
      {/* Hatch lines */}
      {Array.from({ length: Math.floor(r / 6) }).map((_, i) => {
        const offset = -r + (i + 1) * 12
        const halfChord = Math.sqrt(Math.max(0, r * r - offset * offset))
        return (
          <line key={i}
            x1={cx + offset} y1={cy - halfChord} x2={cx + offset + 6} y2={cy + halfChord}
            stroke="#334155" strokeWidth="0.8" />
        )
      })}
      {/* Centre marks */}
      <line x1={cx - r - 10} y1={cy} x2={cx + r + 10} y2={cy}
        stroke="#64748b" strokeWidth="0.6" strokeDasharray="8 4" />
      <line x1={cx} y1={cy - r - 10} x2={cx} y2={cy + r + 10}
        stroke="#64748b" strokeWidth="0.6" strokeDasharray="8 4" />
    </g>
  )
}

function ShaftSide({ part }) {
  const { x, y, width, height } = part
  return (
    <g>
      <rect x={x} y={y} width={width} height={height}
        fill="#1e293b" stroke="#e2e8f0" strokeWidth="2" />
      {/* Centre line */}
      <line x1={x - 15} y1={y + height / 2} x2={x + width + 15} y2={y + height / 2}
        stroke="#64748b" strokeWidth="0.8" strokeDasharray="12 4" />
      {/* Hidden lines for keyway */}
      <line x1={x} y1={y + 8} x2={x + width} y2={y + 8}
        stroke="#475569" strokeWidth="0.8" strokeDasharray="6 3" />
    </g>
  )
}

function TorqueArrow({ part }) {
  const { cx, cy } = part
  return (
    <g>
      <path d={`M ${cx - 20} ${cy} A 20 20 0 0 1 ${cx} ${cy - 20}`}
        fill="none" stroke="#f59e0b" strokeWidth="2" markerEnd="url(#mechArrow)" />
    </g>
  )
}

function MomentArrow({ part }) {
  const { cx, cy } = part
  return (
    <g>
      <path d={`M ${cx} ${cy - 20} A 20 20 0 0 1 ${cx + 20} ${cy}`}
        fill="none" stroke="#a855f7" strokeWidth="2" markerEnd="url(#mechArrow)" />
    </g>
  )
}

function CylinderPart({ part }) {
  const { x, y, width, height } = part
  return (
    <g>
      <rect x={x} y={y} width={width} height={height}
        fill="#1e293b" stroke="#e2e8f0" strokeWidth="2" rx="3" />
      {/* Cooling fins */}
      {Array.from({ length: 5 }).map((_, i) => (
        <line key={i} x1={x - 6} y1={y + 30 + i * 30} x2={x} y2={y + 30 + i * 30}
          stroke="#94a3b8" strokeWidth="1.5" />
      ))}
      {Array.from({ length: 5 }).map((_, i) => (
        <line key={i} x1={x + width} y1={y + 30 + i * 30} x2={x + width + 6} y2={y + 30 + i * 30}
          stroke="#94a3b8" strokeWidth="1.5" />
      ))}
    </g>
  )
}

function PistonPart({ part }) {
  const { x, y, width, height } = part
  return (
    <g>
      <rect x={x} y={y} width={width} height={height}
        fill="#475569" stroke="#e2e8f0" strokeWidth="2" rx="2" />
      {/* Rings */}
      <line x1={x} y1={y + 5} x2={x + width} y2={y + 5}
        stroke="#94a3b8" strokeWidth="1.5" />
      <line x1={x} y1={y + 10} x2={x + width} y2={y + 10}
        stroke="#94a3b8" strokeWidth="1.5" />
    </g>
  )
}

function ConnectingRod({ part }) {
  return (
    <line x1={part.x1} y1={part.y1} x2={part.x2} y2={part.y2}
      stroke="#94a3b8" strokeWidth="4" strokeLinecap="round" />
  )
}

function Crankshaft({ part }) {
  const { cx, cy, r = 40 } = part
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#64748b" strokeWidth="1" strokeDasharray="4 3" />
      <circle cx={cx} cy={cy} r="6" fill="#475569" stroke="#e2e8f0" strokeWidth="1.5" />
      <line x1={cx} y1={cy} x2={cx + r * 0.8} y2={cy}
        stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
      <circle cx={cx + r * 0.8} cy={cy} r="4" fill="#334155" stroke="#94a3b8" strokeWidth="1" />
    </g>
  )
}

function StatePoint({ part }) {
  return (
    <g>
      <circle cx={part.x} cy={part.y} r="5" fill="#334155" stroke="#60a5fa" strokeWidth="1.5" />
      <text x={part.x + 12} y={part.y + 4} fill="#e2e8f0" fontSize="10">{part.label}</text>
    </g>
  )
}

// ─── Dimension Line ─────────────────────────────────────────────────────────

function MechDimension({ dim }) {
  const isVertical = dim.x1 === dim.x2
  return (
    <g>
      <line x1={dim.x1} y1={dim.y1} x2={dim.x2} y2={dim.y2}
        stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 2" />
      {isVertical ? (
        <>
          <line x1={dim.x1 - 5} y1={dim.y1} x2={dim.x1 + 5} y2={dim.y1} stroke="#94a3b8" strokeWidth="1.5" />
          <line x1={dim.x2 - 5} y1={dim.y2} x2={dim.x2 + 5} y2={dim.y2} stroke="#94a3b8" strokeWidth="1.5" />
        </>
      ) : (
        <>
          <line x1={dim.x1} y1={dim.y1 - 5} x2={dim.x1} y2={dim.y1 + 5} stroke="#94a3b8" strokeWidth="1.5" />
          <line x1={dim.x2} y1={dim.y2 - 5} x2={dim.x2} y2={dim.y2 + 5} stroke="#94a3b8" strokeWidth="1.5" />
        </>
      )}
      <text x={(dim.x1 + dim.x2) / 2} y={(dim.y1 + dim.y2) / 2 + (isVertical ? 0 : -8)}
        textAnchor="middle" fill="#94a3b8" fontSize="10" fontWeight="600"
        dx={isVertical ? 16 : 0}>
        {dim.label}
      </text>
    </g>
  )
}

// ─── Main Component ────────────────────────────────────────────────────────

export default function MechVisualizer({ visualData }) {
  const [hovered, setHovered] = useState(null)

  if (!visualData || !visualData.parts) return null

  const { title, width = 720, height = 460, parts, dimensions = [], annotations = [] } = visualData

  const renderPart = (part) => {
    switch (part.type) {
      case 'gear':             return <GearPart part={part} />
      case 'shaft':            return <ShaftPart part={part} />
      case 'cross_section':    return <CrossSection part={part} />
      case 'shaft_side':       return <ShaftSide part={part} />
      case 'torque_arrow':     return <TorqueArrow part={part} />
      case 'moment_arrow':     return <MomentArrow part={part} />
      case 'cylinder':         return <CylinderPart part={part} />
      case 'piston':           return <PistonPart part={part} />
      case 'connecting_rod':   return <ConnectingRod part={part} />
      case 'crankshaft':       return <Crankshaft part={part} />
      case 'state_point':      return <StatePoint part={part} />
      default:                 return null
    }
  }

  const getPartCenter = (p) => {
    if (p.cx !== undefined) return { x: p.cx, y: p.cy }
    if (p.x1 !== undefined) return { x: (p.x1 + p.x2) / 2, y: (p.y1 + p.y2) / 2 }
    return { x: p.x + (p.width || 0) / 2, y: p.y + (p.height || 0) / 2 }
  }

  return (
    <div className="mech-wrapper">
      <div className="mech-header">
        <span className="mech-badge">CAD / 3D MODEL</span>
        <span className="mech-title">{title}</span>
        <span className="mech-hint">hover parts for specs</span>
      </div>

      <div className="mech-canvas-outer">
        <svg
          className="mech-svg"
          viewBox={`0 0 ${width} ${height}`}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <marker id="mechArrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" />
            </marker>
            <pattern id="mechGrid" width="30" height="30" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="30" y2="0" stroke="#1e293b" strokeWidth="0.5" />
              <line x1="0" y1="0" x2="0" y2="30" stroke="#1e293b" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width={width} height={height} fill="#0f172a" />
          <rect width={width} height={height} fill="url(#mechGrid)" />

          {/* Title block */}
          <rect x={width - 210} y={height - 35} width="205" height="30"
            fill="rgba(15,23,42,0.8)" stroke="#334155" strokeWidth="1" rx="4" />
          <text x={width - 107} y={height - 14} textAnchor="middle" fill="#64748b" fontSize="8">
            EXPERIMENTAL DESIGN AGENT — MECHANICAL
          </text>

          {/* Parts */}
          {parts.map((part) => (
            <g key={part.id}
              onMouseEnter={() => setHovered(part)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: part.properties && Object.keys(part.properties).length ? 'pointer' : 'default' }}
            >
              {renderPart(part)}
              {part.label && part.type !== 'state_point' && (
                <text x={getPartCenter(part).x} y={getPartCenter(part).y + (part.r || 30) + 16}
                  textAnchor="middle" fill="#94a3b8" fontSize="9">
                  {part.label}
                </text>
              )}
            </g>
          ))}

          {/* Dimensions */}
          {dimensions.map((dim) => <MechDimension key={dim.id} dim={dim} />)}

          {/* Annotations */}
          {annotations.map((a, i) => (
            <text key={i} x={a.x} y={a.y} textAnchor="middle"
              fill={a.color || '#94a3b8'} fontSize="12" fontWeight="600">
              {a.text}
            </text>
          ))}
        </svg>
      </div>

      {/* Tooltip */}
      {hovered && hovered.properties && Object.keys(hovered.properties).length > 0 && (
        <div className="mech-tooltip"
          style={{ left: getPartCenter(hovered).x + 12, top: getPartCenter(hovered).y - 20 }}>
          <div className="mech-tooltip-title">{hovered.label || hovered.id}</div>
          <div className="mech-tooltip-type">{hovered.type.replace(/_/g, ' ')}</div>
          {Object.entries(hovered.properties).map(([k, v]) => (
            <div key={k} className="mech-tooltip-row">
              <span className="mech-tooltip-key">{k.replace(/_/g, ' ')}</span>
              <span className="mech-tooltip-val">{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="mech-legend">
        <span className="mech-legend-item"><span className="mech-dot" style={{ background: '#60a5fa' }} /> Gear / Section</span>
        <span className="mech-legend-item"><span className="mech-dot" style={{ background: '#e2e8f0' }} /> Shaft / Structure</span>
        <span className="mech-legend-item"><span className="mech-dot" style={{ background: '#f59e0b' }} /> Torque / Force</span>
        <span className="mech-legend-item"><span className="mech-dot" style={{ background: '#a855f7' }} /> Moment / Direction</span>
      </div>
    </div>
  )
}
