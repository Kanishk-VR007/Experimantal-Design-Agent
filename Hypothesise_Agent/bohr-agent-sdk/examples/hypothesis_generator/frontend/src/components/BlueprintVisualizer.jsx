import { useState } from 'react'
import './BlueprintVisualizer.css'

// ─── Element renderers ─────────────────────────────────────────────────────

function BeamElement({ el }) {
  return (
    <g>
      <rect x={el.x} y={el.y} width={el.width} height={el.height}
        fill="#1e3a5f" stroke="#3b82f6" strokeWidth="2" />
      {/* Cross-hatching */}
      {Array.from({ length: Math.floor(el.width / 12) }).map((_, i) => (
        <line key={i} x1={el.x + i * 12} y1={el.y} x2={el.x + i * 12 + 8} y2={el.y + el.height}
          stroke="#2563eb" strokeWidth="0.5" opacity="0.4" />
      ))}
    </g>
  )
}

function PinSupport({ el }) {
  const sz = 22
  return (
    <g>
      <polygon points={`${el.x},${el.y} ${el.x - sz},${el.y + sz} ${el.x + sz},${el.y + sz}`}
        fill="none" stroke="#f59e0b" strokeWidth="2" />
      {/* Ground hatching */}
      {[-16, -8, 0, 8, 16].map((dx, i) => (
        <line key={i} x1={el.x + dx - 4} y1={el.y + sz + 8} x2={el.x + dx + 4} y2={el.y + sz}
          stroke="#f59e0b" strokeWidth="1.5" opacity="0.6" />
      ))}
    </g>
  )
}

function RollerSupport({ el }) {
  const sz = 22
  return (
    <g>
      <polygon points={`${el.x},${el.y} ${el.x - sz},${el.y + sz} ${el.x + sz},${el.y + sz}`}
        fill="none" stroke="#10b981" strokeWidth="2" />
      <circle cx={el.x - 10} cy={el.y + sz + 8} r="5" fill="none" stroke="#10b981" strokeWidth="1.5" />
      <circle cx={el.x} cy={el.y + sz + 8} r="5" fill="none" stroke="#10b981" strokeWidth="1.5" />
      <circle cx={el.x + 10} cy={el.y + sz + 8} r="5" fill="none" stroke="#10b981" strokeWidth="1.5" />
    </g>
  )
}

function DistributedLoad({ el }) {
  const nArrows = Math.max(4, Math.floor(el.width / 30))
  const gap = el.width / nArrows
  return (
    <g>
      <line x1={el.x} y1={el.y} x2={el.x + el.width} y2={el.y}
        stroke="#ef4444" strokeWidth="2" />
      {Array.from({ length: nArrows + 1 }).map((_, i) => {
        const ax = el.x + i * gap
        return (
          <g key={i}>
            <line x1={ax} y1={el.y} x2={ax} y2={el.y + 40}
              stroke="#ef4444" strokeWidth="1.5" />
            <polygon points={`${ax},${el.y + 40} ${ax - 4},${el.y + 32} ${ax + 4},${el.y + 32}`}
              fill="#ef4444" />
          </g>
        )
      })}
    </g>
  )
}

function PointLoad({ el }) {
  return (
    <g>
      <line x1={el.x} y1={el.y} x2={el.x} y2={el.y + 35}
        stroke="#ef4444" strokeWidth="2" />
      <polygon points={`${el.x},${el.y + 35} ${el.x - 5},${el.y + 25} ${el.x + 5},${el.y + 25}`}
        fill="#ef4444" />
    </g>
  )
}

function DimensionLine({ el }) {
  const isVertical = el.x1 === el.x2
  return (
    <g>
      <line x1={el.x1} y1={el.y1} x2={el.x2} y2={el.y2}
        stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 2" />
      {/* End ticks */}
      {isVertical ? (
        <>
          <line x1={el.x1 - 6} y1={el.y1} x2={el.x1 + 6} y2={el.y1} stroke="#94a3b8" strokeWidth="1.5" />
          <line x1={el.x2 - 6} y1={el.y2} x2={el.x2 + 6} y2={el.y2} stroke="#94a3b8" strokeWidth="1.5" />
        </>
      ) : (
        <>
          <line x1={el.x1} y1={el.y1 - 6} x2={el.x1} y2={el.y1 + 6} stroke="#94a3b8" strokeWidth="1.5" />
          <line x1={el.x2} y1={el.y2 - 6} x2={el.x2} y2={el.y2 + 6} stroke="#94a3b8" strokeWidth="1.5" />
        </>
      )}
      <text x={(el.x1 + el.x2) / 2} y={(el.y1 + el.y2) / 2 + (isVertical ? 0 : -8)}
        textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600"
        dx={isVertical ? 18 : 0}>
        {el.label}
      </text>
    </g>
  )
}

function WallElement({ el }) {
  const thick = el.thick
  return (
    <rect x={el.x} y={el.y} width={el.width} height={el.height}
      fill={thick ? 'none' : '#475569'}
      stroke={thick ? '#e2e8f0' : '#64748b'}
      strokeWidth={thick ? 2.5 : 1.5} />
  )
}

function ColumnElement({ el }) {
  const sz = 10
  return (
    <g>
      <rect x={el.x - sz / 2} y={el.y - sz / 2} width={sz} height={sz}
        fill="#334155" stroke="#e2e8f0" strokeWidth="1.5" />
      <line x1={el.x - sz / 2} y1={el.y - sz / 2} x2={el.x + sz / 2} y2={el.y + sz / 2}
        stroke="#e2e8f0" strokeWidth="0.8" />
      <line x1={el.x + sz / 2} y1={el.y - sz / 2} x2={el.x - sz / 2} y2={el.y + sz / 2}
        stroke="#e2e8f0" strokeWidth="0.8" />
    </g>
  )
}

function DoorElement({ el }) {
  const w = 20
  const isH = el.orientation === 'h'
  return (
    <g>
      <rect x={el.x} y={el.y} width={isH ? w : 4} height={isH ? 4 : w}
        fill="#0f172a" stroke="#f59e0b" strokeWidth="1" />
      {/* Swing arc */}
      <path d={isH
        ? `M ${el.x} ${el.y + 4} A ${w} ${w} 0 0 0 ${el.x + w} ${el.y + 4}`
        : `M ${el.x + 4} ${el.y} A ${w} ${w} 0 0 1 ${el.x + 4} ${el.y + w}`}
        fill="none" stroke="#f59e0b" strokeWidth="1" strokeDasharray="3 2" />
    </g>
  )
}

function WindowElement({ el }) {
  const w = 18
  const isH = el.orientation === 'h'
  return (
    <g>
      <rect x={el.x - (isH ? w / 2 : 2)} y={el.y - (isH ? 2 : w / 2)}
        width={isH ? w : 4} height={isH ? 4 : w}
        fill="#0ea5e9" stroke="#38bdf8" strokeWidth="1.5" opacity="0.7" />
    </g>
  )
}

function RoomLabel({ el }) {
  return (
    <g>
      <text x={el.x} y={el.y} textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="600">
        {el.label}
      </text>
      {el.area_sqm && (
        <text x={el.x} y={el.y + 16} textAnchor="middle" fill="#64748b" fontSize="9">
          {el.area_sqm} m²
        </text>
      )}
    </g>
  )
}

function DeflectionIndicator({ el }) {
  return (
    <g>
      <line x1={el.x} y1={el.y} x2={el.x} y2={el.y + 20}
        stroke="#a855f7" strokeWidth="1.5" strokeDasharray="3 2" />
      <polygon points={`${el.x},${el.y + 20} ${el.x - 4},${el.y + 14} ${el.x + 4},${el.y + 14}`}
        fill="#a855f7" />
    </g>
  )
}

function JointElement({ el }) {
  return <circle cx={el.x} cy={el.y} r="4" fill="#e2e8f0" stroke="#3b82f6" strokeWidth="1.5" />
}

function MemberElement({ el }) {
  const colorMap = {
    bottom_chord: '#3b82f6',
    top_chord: '#ef4444',
    diagonal: '#f59e0b',
    vertical: '#a855f7',
  }
  return (
    <line x1={el.x1} y1={el.y1} x2={el.x2} y2={el.y2}
      stroke={colorMap[el.member_type] || '#94a3b8'} strokeWidth="2.5" />
  )
}

// ─── Main Component ────────────────────────────────────────────────────────

export default function BlueprintVisualizer({ visualData }) {
  const [hovered, setHovered] = useState(null)

  if (!visualData || !visualData.elements) return null

  const { title, width = 720, height = 520, elements, annotations = [] } = visualData
  const isStructural = visualData.blueprint_type === 'structural'

  const renderElement = (el) => {
    switch (el.type) {
      case 'beam':               return <BeamElement el={el} />
      case 'pin_support':        return <PinSupport el={el} />
      case 'roller_support':     return <RollerSupport el={el} />
      case 'distributed_load':   return <DistributedLoad el={el} />
      case 'point_load':         return <PointLoad el={el} />
      case 'dimension':          return <DimensionLine el={el} />
      case 'wall':               return <WallElement el={el} />
      case 'column':             return <ColumnElement el={el} />
      case 'door':               return <DoorElement el={el} />
      case 'window':             return <WindowElement el={el} />
      case 'room_label':         return <RoomLabel el={el} />
      case 'deflection_indicator': return <DeflectionIndicator el={el} />
      case 'joint':              return <JointElement el={el} />
      case 'member':             return <MemberElement el={el} />
      default:                   return null
    }
  }

  // Tooltip position: use the element's x/y or midpoint
  const getElCenter = (el) => {
    if (el.x1 !== undefined) return { x: (el.x1 + el.x2) / 2, y: (el.y1 + el.y2) / 2 }
    if (el.cx !== undefined) return { x: el.cx, y: el.cy }
    return { x: el.x + (el.width || 0) / 2, y: el.y + (el.height || 0) / 2 }
  }

  return (
    <div className="bp-wrapper">
      <div className="bp-header">
        <span className="bp-badge">{isStructural ? 'STRUCTURAL' : 'FLOOR PLAN'}</span>
        <span className="bp-title">{title}</span>
        <span className="bp-hint">hover elements for details</span>
      </div>

      <div className="bp-canvas-outer">
        <svg
          className="bp-svg"
          viewBox={`0 0 ${width} ${height}`}
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Grid */}
          <defs>
            <pattern id="bp-grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <circle cx="10" cy="10" r="0.5" fill={isStructural ? '#1e293b' : '#334155'} />
            </pattern>
          </defs>
          <rect width={width} height={height} fill={isStructural ? '#0f172a' : '#1e293b'} />
          <rect width={width} height={height} fill="url(#bp-grid)" />

          {/* Title block */}
          <rect x={width - 200} y={height - 35} width="195" height="30"
            fill="rgba(15,23,42,0.8)" stroke="#334155" strokeWidth="1" rx="4" />
          <text x={width - 102} y={height - 14} textAnchor="middle" fill="#64748b" fontSize="8">
            EXPERIMENTAL DESIGN AGENT — BLUEPRINT
          </text>

          {/* Elements */}
          {elements.map((el) => (
            <g key={el.id}
              onMouseEnter={() => setHovered(el)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: el.properties && Object.keys(el.properties).length ? 'pointer' : 'default' }}
            >
              {renderElement(el)}
              {/* Labels for structural elements */}
              {el.label && el.type !== 'room_label' && el.type !== 'dimension' && (
                <text x={getElCenter(el).x} y={getElCenter(el).y - 10}
                  textAnchor="middle" fill="#94a3b8" fontSize="9">
                  {el.label}
                </text>
              )}
            </g>
          ))}

          {/* Annotations */}
          {annotations.map((a, i) => (
            <text key={i} x={a.x} y={a.y} textAnchor="middle"
              fill={a.color || '#94a3b8'} fontSize="11" fontWeight="600">
              {a.text}
            </text>
          ))}
        </svg>
      </div>

      {/* Tooltip */}
      {hovered && hovered.properties && Object.keys(hovered.properties).length > 0 && (
        <div className="bp-tooltip"
          style={{ left: getElCenter(hovered).x + 12, top: getElCenter(hovered).y - 20 }}>
          <div className="bp-tooltip-title">{hovered.label || hovered.id}</div>
          <div className="bp-tooltip-type">{hovered.type.replace(/_/g, ' ')}</div>
          {Object.entries(hovered.properties).map(([k, v]) => (
            <div key={k} className="bp-tooltip-row">
              <span className="bp-tooltip-key">{k.replace(/_/g, ' ')}</span>
              <span className="bp-tooltip-val">{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="bp-legend">
        {isStructural ? (
          <>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#3b82f6' }} /> Beam / Bottom Chord</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#f59e0b' }} /> Support / Diagonal</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#ef4444' }} /> Load / Top Chord</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#a855f7' }} /> Deflection / Vertical</span>
          </>
        ) : (
          <>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#e2e8f0' }} /> Wall</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#334155' }} /> Column</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#f59e0b' }} /> Door</span>
            <span className="bp-legend-item"><span className="bp-dot" style={{ background: '#0ea5e9' }} /> Window</span>
          </>
        )}
      </div>
    </div>
  )
}
