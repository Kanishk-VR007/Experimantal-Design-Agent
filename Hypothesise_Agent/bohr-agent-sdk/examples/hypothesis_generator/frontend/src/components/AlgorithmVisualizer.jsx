import { useState, useEffect } from 'react'
import { Play, Pause, SkipForward, RotateCcw, Cpu, Network, Layers, Binary, Activity, Info } from 'lucide-react'
import './AlgorithmVisualizer.css'

export default function AlgorithmVisualizer({ visualData, data }) {
  const actualData = visualData || data || {}
  const isNeural = actualData.type === 'neural_network' || (!actualData.type && actualData.layers)

  const [activeTab, setActiveTab] = useState(isNeural ? 'neural' : 'algorithm')
  const [currentStep, setCurrentStep] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [hoveredNode, setHoveredNode] = useState(null)

  // Sorting array animation state
  const initialArray = actualData.array_initial || [45, 12, 89, 34, 67, 23, 91, 5, 56, 78, 40, 62]
  const traceSteps = actualData.trace_steps || [
    { step: 1, action: 'compare', indices: [0, 1], pivot: 62, message: 'Comparing Array[0]=45 with Array[1]=12' },
    { step: 2, action: 'swap', indices: [0, 1], pivot: 62, message: 'Swap: 12 < 45 placed in ascending order' },
    { step: 3, action: 'partition', indices: [5], pivot: 62, message: 'Pivot 62 locked in place at index 7' },
    { step: 4, action: 'recurse', indices: [0, 6], pivot: 40, message: 'Recursive partition on left subarray [0..6]' },
    { step: 5, action: 'complete', indices: [0, 11], message: 'Array fully sorted: O(n log n) divide-and-conquer verified' }
  ]

  // Playback timer
  useEffect(() => {
    let timer = null
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= traceSteps.length - 1) {
            setIsPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, 1200)
    }
    return () => clearInterval(timer)
  }, [isPlaying, traceSteps.length])

  // Neural layers definition
  const neuralLayers = actualData.layers || [
    { id: 'in', name: 'Input Tensor', type: 'input', nodes: 6, shape: '28x28x1', color: '#06b6d4', desc: 'Normalized input image pixel matrix' },
    { id: 'conv', name: 'Conv2D + ReLU', type: 'conv', nodes: 8, shape: '64 channels (3x3)', color: '#8b5cf6', desc: 'Spatial feature extraction & edge detection' },
    { id: 'attn', name: 'Multi-Head Attention', type: 'attention', nodes: 6, shape: '8 Heads (d=256)', color: '#f59e0b', desc: 'Global context token self-attention mechanism' },
    { id: 'dense', name: 'Dense Classifier', type: 'dense', nodes: 5, shape: '128 units', color: '#38bdf8', desc: 'Fully-connected latent representation projection' },
    { id: 'out', name: 'Softmax Logits', type: 'output', nodes: 4, shape: '10 classes', color: '#10b981', desc: 'Class posterior probability distribution' }
  ]

  // Graph topology definition
  const graphData = actualData.graph || {
    nodes: [
      { id: 'A', label: 'Start (A)', distance: 0, x: 70, y: 140 },
      { id: 'B', label: 'Node B', distance: 4, x: 170, y: 70 },
      { id: 'C', label: 'Node C', distance: 2, x: 170, y: 210 },
      { id: 'D', label: 'Node D', distance: 7, x: 290, y: 70 },
      { id: 'E', label: 'Node E', distance: 5, x: 290, y: 210 },
      { id: 'F', label: 'Target (F)', distance: 9, x: 390, y: 140 }
    ],
    edges: [
      { source: 'A', target: 'B', weight: 4, in_path: false },
      { source: 'A', target: 'C', weight: 2, in_path: true },
      { source: 'B', target: 'D', weight: 5, in_path: false },
      { source: 'C', target: 'E', weight: 3, in_path: true },
      { source: 'D', target: 'F', weight: 2, in_path: false },
      { source: 'E', target: 'F', weight: 4, in_path: true },
      { source: 'C', target: 'B', weight: 1, in_path: false },
      { source: 'B', target: 'E', weight: 2, in_path: false }
    ],
    shortest_path: ['A', 'C', 'E', 'F'],
    total_cost: 9
  }

  const activeTrace = traceSteps[currentStep] || traceSteps[0]

  return (
    <div className="algorithm-visualizer-container">
      {/* Visualizer Header Tabs */}
      <div className="algo-header-bar">
        <div className="algo-title-group">
          <Binary size={18} color="var(--accent-primary)" />
          <span className="algo-title">Computer Science Computational Architecture</span>
        </div>

        <div className="algo-tabs">
          <button
            type="button"
            className={`algo-tab-btn ${activeTab === 'neural' ? 'active' : ''}`}
            onClick={() => setActiveTab('neural')}
          >
            <Layers size={14} />
            <span>Neural Network Topology</span>
          </button>
          <button
            type="button"
            className={`algo-tab-btn ${activeTab === 'algorithm' ? 'active' : ''}`}
            onClick={() => setActiveTab('algorithm')}
          >
            <Network size={14} />
            <span>Sorting &amp; Graph DAG</span>
          </button>
        </div>
      </div>

      {/* ── TAB 1: NEURAL NETWORK ARCHITECTURE ── */}
      {activeTab === 'neural' && (
        <div className="algo-content-pane">
          <div className="algo-canvas-wrapper">
            <svg viewBox="0 0 760 320" className="algo-svg-canvas">
              <defs>
                <linearGradient id="synapseGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.6" />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Inter-layer Synaptic Connections */}
              {neuralLayers.slice(0, -1).map((layer, lIdx) => {
                const nextLayer = neuralLayers[lIdx + 1]
                const x1 = 80 + lIdx * 150
                const x2 = 80 + (lIdx + 1) * 150

                return (
                  <g key={`synapses-${lIdx}`}>
                    {Array.from({ length: layer.nodes }).map((_, n1) => {
                      const y1 = 60 + n1 * (200 / (layer.nodes - 1 || 1))
                      return Array.from({ length: nextLayer.nodes }).map((_, n2) => {
                        const y2 = 60 + n2 * (200 / (nextLayer.nodes - 1 || 1))
                        // Sparsely connect for visual elegance
                        if ((n1 + n2) % 2 === 0) {
                          return (
                            <line
                              key={`syn-${lIdx}-${n1}-${n2}`}
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="#334155"
                              strokeWidth="1"
                              opacity="0.4"
                              strokeDasharray="4 2"
                              className="flowing-synapse"
                            />
                          )
                        }
                        return null
                      })
                    })}
                  </g>
                )
              })}

              {/* Layer Nodes */}
              {neuralLayers.map((layer, lIdx) => {
                const x = 80 + lIdx * 150
                return (
                  <g key={layer.id} className="neural-layer-group">
                    {/* Layer Header Label */}
                    <text x={x} y="30" textAnchor="middle" fill="#94a3b8" fontSize="11" fontWeight="600">
                      {layer.name}
                    </text>
                    <text x={x} y="44" textAnchor="middle" fill="#64748b" fontSize="9">
                      {layer.shape}
                    </text>

                    {/* Neurons */}
                    {Array.from({ length: layer.nodes }).map((_, nIdx) => {
                      const y = 60 + nIdx * (200 / (layer.nodes - 1 || 1))
                      const isHovered = hoveredNode === `${layer.id}-${nIdx}`

                      return (
                        <g
                          key={nIdx}
                          onMouseEnter={() => setHoveredNode(`${layer.id}-${nIdx}`)}
                          onMouseLeave={() => setHoveredNode(null)}
                          style={{ cursor: 'pointer' }}
                        >
                          <circle
                            cx={x}
                            cy={y}
                            r={isHovered ? 12 : 9}
                            fill={layer.color}
                            opacity={0.9}
                            filter="url(#glow)"
                            stroke="#ffffff"
                            strokeWidth={isHovered ? 2 : 1}
                            className="neuron-circle"
                          />
                          <circle cx={x} cy={y} r="3" fill="#ffffff" opacity="0.8" />
                        </g>
                      )
                    })}
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Neural Telemetry Cards */}
          <div className="algo-telemetry-row">
            <div className="telemetry-card">
              <span className="telemetry-label">Architecture</span>
              <span className="telemetry-value" style={{ color: '#8b5cf6' }}>
                {actualData.architecture || 'ResNet CNN / Vision Transformer'}
              </span>
            </div>
            <div className="telemetry-card">
              <span className="telemetry-label">Peak Val Accuracy</span>
              <span className="telemetry-value" style={{ color: '#10b981' }}>
                {actualData.metrics?.transformer_final_accuracy_pct || actualData.metrics?.peak_accuracy_pct || '91.5%'}
              </span>
            </div>
            <div className="telemetry-card">
              <span className="telemetry-label">Final Loss</span>
              <span className="telemetry-value" style={{ color: '#38bdf8' }}>
                {actualData.metrics?.transformer_final_loss || '0.1600'}
              </span>
            </div>
            <div className="telemetry-card">
              <span className="telemetry-label">Optimization</span>
              <span className="telemetry-value" style={{ color: '#f59e0b' }}>
                AdamW + Cosine Decay
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: SORTING & GRAPH ALGORITHMS ── */}
      {activeTab === 'algorithm' && (
        <div className="algo-content-pane">
          {/* Top Half: Sorting Array Visualizer */}
          <div className="algo-sorting-section">
            <div className="section-subheading">
              <Activity size={14} color="#f59e0b" />
              <span>Divide-and-Conquer Sorting Execution (QuickSort / MergeSort)</span>
            </div>

            {/* Step Trace Banner */}
            <div className="algo-step-banner">
              <span className="step-tag">Step {activeTrace.step}/{traceSteps.length}:</span>
              <span className="step-msg">{activeTrace.message}</span>
            </div>

            {/* Array Bars */}
            <div className="array-bars-container">
              {initialArray.map((val, idx) => {
                const maxVal = Math.max(...initialArray)
                const heightPct = Math.round((val / maxVal) * 100)
                const isCompared = activeTrace.indices?.includes(idx)
                const isPivot = activeTrace.pivot === val

                let barColor = '#38bdf8'
                if (activeTrace.action === 'complete') barColor = '#10b981'
                else if (isPivot) barColor = '#f59e0b'
                else if (isCompared) barColor = '#ec4899'

                return (
                  <div key={idx} className="array-bar-col">
                    <span className="bar-val-label">{val}</span>
                    <div
                      className="array-bar-rect"
                      style={{
                        height: `${heightPct}%`,
                        backgroundColor: barColor,
                        boxShadow: (isCompared || isPivot) ? `0 0 10px ${barColor}` : 'none'
                      }}
                    />
                    <span className="bar-idx-label">[{idx}]</span>
                  </div>
                )
              })}
            </div>

            {/* Playback Controls */}
            <div className="algo-controls-bar">
              <button
                type="button"
                className="ctrl-btn"
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? 'Pause simulation' : 'Auto-play simulation'}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                <span>{isPlaying ? 'Pause' : 'Play Simulation'}</span>
              </button>
              <button
                type="button"
                className="ctrl-btn"
                onClick={() => setCurrentStep((prev) => Math.min(traceSteps.length - 1, prev + 1))}
                disabled={currentStep >= traceSteps.length - 1}
              >
                <SkipForward size={14} />
                <span>Next Step</span>
              </button>
              <button
                type="button"
                className="ctrl-btn"
                onClick={() => { setCurrentStep(0); setIsPlaying(false); }}
              >
                <RotateCcw size={14} />
                <span>Reset</span>
              </button>
              <div className="complexity-badge">
                Time: <strong>O(n log n)</strong> | Space: <strong>O(log n)</strong>
              </div>
            </div>
          </div>

          {/* Bottom Half: Dijkstra Shortest Path Graph */}
          <div className="algo-graph-section">
            <div className="section-subheading">
              <Network size={14} color="#10b981" />
              <span>Network Graph Traversal &amp; Dijkstra Shortest Path</span>
            </div>

            <div className="graph-canvas-frame">
              <svg viewBox="0 0 460 260" className="graph-svg">
                {/* Edges */}
                {graphData.edges.map((edge, eIdx) => {
                  const src = graphData.nodes.find((n) => n.id === edge.source)
                  const dst = graphData.nodes.find((n) => n.id === edge.target)
                  if (!src || !dst) return null

                  const isPath = edge.in_path
                  const mx = (src.x + dst.x) / 2
                  const my = (src.y + dst.y) / 2

                  return (
                    <g key={`edge-${eIdx}`}>
                      <line
                        x1={src.x}
                        y1={src.y}
                        x2={dst.x}
                        y2={dst.y}
                        stroke={isPath ? '#10b981' : '#475569'}
                        strokeWidth={isPath ? 3 : 1.5}
                        strokeDasharray={isPath ? 'none' : '4 3'}
                        opacity={isPath ? 1.0 : 0.6}
                      />
                      <rect x={mx - 9} y={my - 8} width="18" height="16" fill="#0f172a" rx="3" />
                      <text x={mx} y={my + 4} textAnchor="middle" fill={isPath ? '#10b981' : '#94a3b8'} fontSize="10" fontWeight="600">
                        {edge.weight}
                      </text>
                    </g>
                  )
                })}

                {/* Nodes */}
                {graphData.nodes.map((node) => {
                  const isShortestPath = graphData.shortest_path.includes(node.id)

                  return (
                    <g key={node.id} className="graph-node-group">
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r="18"
                        fill={isShortestPath ? '#065f46' : '#1e293b'}
                        stroke={isShortestPath ? '#10b981' : '#64748b'}
                        strokeWidth={isShortestPath ? 2.5 : 1.5}
                      />
                      <text x={node.x} y={node.y + 4} textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="700">
                        {node.id}
                      </text>
                      <text x={node.x} y={node.y - 22} textAnchor="middle" fill="#94a3b8" fontSize="9">
                        d={node.distance}
                      </text>
                    </g>
                  )
                })}
              </svg>

              <div className="graph-hud">
                <div className="hud-metric">
                  <span>Shortest Path:</span>
                  <strong>{graphData.shortest_path.join(' → ')}</strong>
                </div>
                <div className="hud-metric">
                  <span>Total Accumulated Cost:</span>
                  <strong style={{ color: '#10b981' }}>{graphData.total_cost} units</strong>
                </div>
                <div className="hud-metric">
                  <span>Dijkstra Complexity:</span>
                  <strong>O(V log V + E)</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

