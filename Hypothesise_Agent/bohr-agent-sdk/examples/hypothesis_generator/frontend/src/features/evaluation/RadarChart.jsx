function RadarChart({ scores = {}, size = 320 }) {
  const axes = [
    { key: 'hypothesis', label: 'L1 Hypothesis', score: scores.hypothesis ?? 98 },
    { key: 'architecture', label: 'L2 Architecture', score: scores.architecture ?? 96 },
    { key: 'simulation', label: 'L3 Simulation', score: scores.simulation ?? 99 },
    { key: 'statistics', label: 'L4 Statistics', score: scores.statistics ?? 95 },
    { key: 'audit', label: 'L5 Audit', score: scores.audit ?? 97 },
    { key: 'coverage', label: 'L6 Coverage', score: scores.coverage ?? 98 },
    { key: 'review', label: 'L7 Peer Review', score: scores.review ?? 97 },
  ]

  const center = size / 2
  const radius = (size / 2) - 45
  const angleStep = (Math.PI * 2) / axes.length

  // Generate grid concentric polygons (at 25%, 50%, 75%, 100%)
  const gridLevels = [0.25, 0.5, 0.75, 1.0]

  const getCoordinates = (index, valuePct) => {
    const angle = index * angleStep - Math.PI / 2
    const r = radius * valuePct
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    }
  }

  // Data polygon coordinates
  const dataPoints = axes.map((a, i) => getCoordinates(i, (a.score || 0) / 100))
  const dataPolygonPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')

  return (
    <div className="radar-chart-container" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="radar-svg">
        {/* Concentric grid polygons */}
        {gridLevels.map((lvl, lIdx) => {
          const pts = axes.map((_, i) => {
            const c = getCoordinates(i, lvl)
            return `${c.x},${c.y}`
          }).join(' ')
          return (
            <polygon
              key={lIdx}
              points={pts}
              fill={lIdx === gridLevels.length - 1 ? 'rgba(30, 41, 59, 0.4)' : 'none'}
              stroke="var(--border)"
              strokeWidth="1"
              strokeDasharray={lvl < 1 ? '3 3' : 'none'}
            />
          )
        })}

        {/* Spoke lines */}
        {axes.map((_, i) => {
          const c = getCoordinates(i, 1.0)
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={c.x}
              y2={c.y}
              stroke="var(--border)"
              strokeWidth="1"
            />
          )
        })}

        {/* Data polygon with gradient fill and glow */}
        <polygon
          points={dataPolygonPoints}
          fill="rgba(0, 240, 255, 0.2)"
          stroke="var(--accent-primary)"
          strokeWidth="2.5"
          filter="drop-shadow(0 0 6px rgba(0, 240, 255, 0.5))"
        />

        {/* Data points */}
        {dataPoints.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="4.5"
            fill="var(--accent-primary)"
            stroke="#0f172a"
            strokeWidth="2"
          />
        ))}

        {/* Axis Labels */}
        {axes.map((a, i) => {
          const c = getCoordinates(i, 1.22)
          return (
            <text
              key={i}
              x={c.x}
              y={c.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#94a3b8"
              fontSize="10"
              fontWeight="600"
              fontFamily="var(--font-ui)"
            >
              {a.label}
            </text>
          )
        })}
      </svg>
    </div>
  )
}

export default RadarChart

