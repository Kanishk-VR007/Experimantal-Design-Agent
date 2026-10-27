import { useState } from 'react'
import './SampleTestVisualizer.css'

// ─── OD600 → fill colour ──────────────────────────────────────────────────
function odColor(od, type) {
  if (type === 'blank')   return '#0f172a'
  if (type === 'control') return '#334155'
  if (od >= 1.0)  return '#1a472a'
  if (od >= 0.5)  return '#2d6a4f'
  if (od >= 0.2)  return '#52b788'
  if (od >= 0.05) return '#b7e4c7'
  return '#e2e8f0'
}

function odTextColor(od, type) {
  if (type === 'blank' || type === 'control') return '#94a3b8'
  if (od >= 0.5) return '#d1fae5'
  return '#1e293b'
}

// ─── Single well ─────────────────────────────────────────────────────────────
function Well({ well, cx, cy, r, onHover, hovered }) {
  const fill   = odColor(well.od600, well.sample_type)
  const stroke = hovered ? '#f59e0b' : '#334155'
  const sw     = hovered ? 2 : 0.8

  return (
    <g
      className="well-group"
      onMouseEnter={() => onHover(well)}
      onMouseLeave={() => onHover(null)}
      style={{ cursor: 'pointer' }}
    >
      <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth={sw} />
      {/* OD label inside well (only for larger wells) */}
      {r >= 14 && (
        <text
          x={cx} y={cy + 1}
          textAnchor="middle" dominantBaseline="middle"
          fontSize="6" fill={odTextColor(well.od600, well.sample_type)}
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          {well.od600.toFixed(2)}
        </text>
      )}
    </g>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────
export default function SampleTestVisualizer({ visualData }) {
  const [hovered, setHovered] = useState(null)

  if (!visualData) return null

  const { title, plate, stats, legend } = visualData

  const ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
  const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

  // Layout constants
  const PAD_L  = 56   // left margin (row letters)
  const PAD_T  = 46   // top margin  (col numbers)
  const CELL   = 42   // cell size (px)
  const R      = 16   // well radius (px)
  const SVG_W  = PAD_L + COLS.length * CELL + 20
  const SVG_H  = PAD_T + ROWS.length * CELL + 20

  // Build lookup map
  const wellMap = {}
  plate.wells.forEach(w => { wellMap[w.id] = w })

  return (
    <div className="sample-visualizer">
      <div className="sample-header">
        <span className="sample-title">🧪 {title}</span>
      </div>

      <div className="sample-layout">
        {/* ── SVG plate ── */}
        <div className="plate-wrapper">
          <svg
            width={SVG_W}
            height={SVG_H}
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            className="plate-svg"
          >
            {/* Plate background */}
            <rect x={PAD_L - 8} y={PAD_T - 8}
              width={COLS.length * CELL + 16}
              height={ROWS.length * CELL + 16}
              rx="8" ry="8"
              fill="#1e293b" stroke="#334155" strokeWidth="1.5"
            />

            {/* Column headers */}
            {COLS.map((col, ci) => (
              <text key={col}
                x={PAD_L + ci * CELL + CELL / 2}
                y={PAD_T - 16}
                textAnchor="middle"
                fontSize="10" fill="#64748b"
                fontFamily="monospace"
              >{col}</text>
            ))}

            {/* Row headers + wells */}
            {ROWS.map((row, ri) => (
              <g key={row}>
                <text
                  x={PAD_L - 16}
                  y={PAD_T + ri * CELL + CELL / 2}
                  textAnchor="middle" dominantBaseline="middle"
                  fontSize="10" fill="#64748b" fontFamily="monospace"
                >{row}</text>

                {COLS.map((col, ci) => {
                  const wellId = `${row}${col}`
                  const well   = wellMap[wellId]
                  if (!well) return null
                  const cx = PAD_L + ci * CELL + CELL / 2
                  const cy = PAD_T + ri * CELL + CELL / 2
                  return (
                    <Well
                      key={wellId}
                      well={well}
                      cx={cx} cy={cy} r={R}
                      onHover={setHovered}
                      hovered={hovered?.id === wellId}
                    />
                  )
                })}
              </g>
            ))}
          </svg>

          {/* Hover tooltip */}
          {hovered && (
            <div className="well-tooltip">
              <div className="tooltip-id">{hovered.id}</div>
              <div className="tooltip-row"><span>Type</span><span className={`badge badge-${hovered.sample_type}`}>{hovered.sample_type}</span></div>
              <div className="tooltip-row"><span>OD600</span><span>{hovered.od600}</span></div>
              <div className="tooltip-row"><span>Time</span><span>{hovered.time_h} h</span></div>
              <div className="tooltip-row"><span>Sample</span><span>{hovered.label}</span></div>
            </div>
          )}
        </div>

        {/* ── Right panel ── */}
        <div className="sample-panel">
          {/* Stats */}
          <div className="sample-stats">
            <h4>📊 Plate Summary</h4>
            <div className="stat-grid">
              <div className="stat-card"><span className="stat-val">{stats.total_wells}</span><span className="stat-lbl">Total Wells</span></div>
              <div className="stat-card positive"><span className="stat-val">{stats.positive_wells}</span><span className="stat-lbl">Positive</span></div>
              <div className="stat-card negative"><span className="stat-val">{stats.negative_wells}</span><span className="stat-lbl">Negative</span></div>
              <div className="stat-card control"><span className="stat-val">{stats.control_wells}</span><span className="stat-lbl">Controls</span></div>
              <div className="stat-card"><span className="stat-val">{stats.mean_od600}</span><span className="stat-lbl">Mean OD600</span></div>
              <div className="stat-card"><span className="stat-val">{stats.max_od600}</span><span className="stat-lbl">Max OD600</span></div>
            </div>
          </div>

          {/* Legend */}
          <div className="sample-legend">
            <h4>🎨 OD600 Scale</h4>
            {legend.map((item, i) => (
              <div key={i} className="legend-row">
                <span className="legend-swatch" style={{ backgroundColor: item.color }} />
                <span className="legend-label">{item.label}</span>
              </div>
            ))}
            <div className="legend-row">
              <span className="legend-swatch" style={{ backgroundColor: '#334155' }} />
              <span className="legend-label">Control / Blank</span>
            </div>
          </div>

          {/* Protocol notes */}
          <div className="sample-protocol">
            <h4>🔬 Protocol Notes</h4>
            <ul>
              <li>Assay: OD600 absorbance (microplate reader)</li>
              <li>Wells A1–A3: negative control (sterile media)</li>
              <li>Wells H10–H12: instrument blanks</li>
              <li>All samples run in duplicate</li>
              <li>Incubation: 37 °C, 180 rpm shaking</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
