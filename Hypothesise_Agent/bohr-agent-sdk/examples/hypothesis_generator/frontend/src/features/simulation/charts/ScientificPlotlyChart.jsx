import Plot from 'react-plotly.js'

function ScientificPlotlyChart({ plot, expanded = false }) {
  if (!plot || !plot.x || !plot.y) return null

  const COLORS = ['#00f0ff', '#38bdf8', '#a855f7', '#10b981', '#f59e0b', '#ec4899']

  const baseMode = plot.plot_type === 'line' ? 'lines' : 'lines+markers'
  const traces = [
    {
      x: plot.x,
      y: plot.y,
      type: plot.plot_type === 'bar' ? 'bar' : 'scatter',
      mode: baseMode,
      name: plot.series_name || 'Experimental',
      line: { color: COLORS[0], width: 2.5 },
      marker: { color: COLORS[0], size: plot.plot_type === 'scatter' ? 6 : 4 },
    },
  ]

  if (plot.extra_series && plot.extra_series.length) {
    plot.extra_series.forEach((s, idx) => {
      traces.push({
        x: plot.x,
        y: s.y,
        type: plot.plot_type === 'bar' ? 'bar' : 'scatter',
        mode: baseMode,
        name: s.name,
        line: { color: s.color || COLORS[(idx + 1) % COLORS.length], width: 2 },
        marker: { color: s.color || COLORS[(idx + 1) % COLORS.length], size: 4 },
      })
    })
  }

  const layout = {
    title: {
      text: plot.title,
      font: { size: expanded ? 15 : 13, color: '#f1f5f9', family: 'Inter' }
    },
    xaxis: {
      title: { text: plot.x_label, font: { size: 11, color: '#94a3b8' } },
      showgrid: true,
      gridcolor: '#334155',
      zerolinecolor: '#475569',
      tickfont: { color: '#94a3b8', size: 10 }
    },
    yaxis: {
      title: { text: plot.y_label, font: { size: 11, color: '#94a3b8' } },
      showgrid: true,
      gridcolor: '#334155',
      zerolinecolor: '#475569',
      tickfont: { color: '#94a3b8', size: 10 }
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.7)',
    font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
    margin: { t: 40, r: 20, b: 45, l: 55 },
    autosize: true,
    height: expanded ? 500 : 320,
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.15,
      font: { size: 11, color: '#94a3b8' }
    }
  }

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  }

  return (
    <div className="scientific-plotly-wrapper">
      <Plot
        data={traces}
        layout={layout}
        config={config}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  )
}

export default ScientificPlotlyChart

