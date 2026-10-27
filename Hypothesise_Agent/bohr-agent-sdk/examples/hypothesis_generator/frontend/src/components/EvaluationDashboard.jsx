import { useState, useEffect, useRef, useMemo } from 'react'
import SimulationResults from './SimulationResults'
import MemoryMetrics from './MemoryMetrics'
import './EvaluationDashboard.css'

// ── Constants ─────────────────────────────────────────────────────────────
const GRADE_META = {
  A: { color: '#00ff88', bg: 'rgba(0,255,136,0.1)',  label: 'Excellent' },
  B: { color: '#00d9ff', bg: 'rgba(0,217,255,0.1)',  label: 'Good'      },
  C: { color: '#ffaa00', bg: 'rgba(255,170,0,0.1)',  label: 'Average'   },
  D: { color: '#ff6b35', bg: 'rgba(255,107,53,0.1)', label: 'Below Avg' },
  F: { color: '#ff3366', bg: 'rgba(255,51,102,0.1)', label: 'Failed'    },
}

const LAYER_META = {
  L1_hypothesis: { icon: '💡', label: 'Hypothesis',   desc: 'Clarity and testability of the research hypothesis' },
  L2_architect:  { icon: '🏗️', label: 'Architecture', desc: 'Experimental design structure and completeness' },
  L3_simulation: { icon: '⚗️', label: 'Simulation',   desc: 'Fidelity and confidence of simulation results' },
  L4_analysis:   { icon: '📊', label: 'Analysis',     desc: 'Depth of numerical analysis and visualizations' },
  L5_auditor:    { icon: '🛡️', label: 'Audit',        desc: 'Methodology soundness and error control' },
  L6_memory:     { icon: '🧠', label: 'Coverage',     desc: 'Domain coverage and variable completeness' },
  L7_review:     { icon: '📝', label: 'Review',       desc: 'Peer-review readiness and overall report quality' },
}

// keep a flat icon map for backward compat
const LAYER_ICONS = Object.fromEntries(
  Object.entries(LAYER_META).map(([k, v]) => [k, v.icon])
)

// ── Helpers ────────────────────────────────────────────────────────────────
const clamp     = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v))
const gradeOf   = s => s >= 0.9 ? 'A' : s >= 0.8 ? 'B' : s >= 0.7 ? 'C' : s >= 0.6 ? 'D' : 'F'
const scoreColor = s => s >= 0.9 ? '#00ff88' : s >= 0.8 ? '#00d9ff' : s >= 0.7 ? '#ffaa00' : s >= 0.6 ? '#ff6b35' : '#ff3366'

// ══════════════════════════════════════════════════════════════════════════
// Client-side evaluation scorer — derives 7 evaluation dimensions from
// a simulation result object + the design text.
// ══════════════════════════════════════════════════════════════════════════
function computeEvalFromSimulation(simulation, design) {
  const {
    confidence_score = 0,
    status           = 'unknown',
    hypothesis       = '',
    numerical_results= {},
    plot_data        = [],
    observations     = [],
    simulation_log   = [],
    domain           = '',
    engine_used      = '',
  } = simulation || {}

  const dt    = (design || '').toLowerCase()
  const dl    = dt.length
  const kws   = ['hypothesis','variable','method','control','analysis','limitation','expected','procedure','material']
  const hits  = kws.filter(s => dt.includes(s)).length
  const nKeys = Object.keys(numerical_results || {}).length
  const nPlot = (plot_data || []).length
  const nObs  = (observations || []).length
  const nLog  = (simulation_log || []).length
  const hLen  = (hypothesis || '').length

  // L1 — Hypothesis
  const l1 = clamp(
    (hLen > 200 ? 0.88 : hLen > 100 ? 0.78 : hLen > 50 ? 0.62 : 0.40) +
    (dt.includes('hypothesis') ? 0.05 : 0) +
    (/\bif\b|\bwhen\b|\bwill\b/.test((hypothesis || '').toLowerCase()) ? 0.04 : 0)
  )
  // L2 — Architecture
  const l2 = clamp(0.25 + (hits / kws.length) * 0.60 + (dl > 800 ? 0.15 : dl > 400 ? 0.08 : 0))
  // L3 — Simulation fidelity
  const l3 = clamp(confidence_score * 0.80 + (status === 'success' ? 0.20 : 0))
  // L4 — Analysis depth
  const l4 = clamp(0.35 + Math.min(nKeys / 5, 1) * 0.35 + Math.min(nPlot / 4, 1) * 0.30)
  // L5 — Audit / methodology
  const l5 = clamp(0.35 + Math.min(nObs / 4, 1) * 0.30 + Math.min(nLog / 8, 1) * 0.20 + (status === 'success' ? 0.15 : 0))
  // L6 — Domain coverage
  const l6 = clamp(0.45 + (domain ? 0.15 : 0) + (nPlot > 2 ? 0.15 : nPlot > 0 ? 0.08 : 0) + (nKeys > 3 ? 0.18 : nKeys > 0 ? 0.08 : 0))
  // L7 — Review readiness
  const l7 = clamp((l2 + l3 + l4) / 3 * 0.85 + (nObs > 2 ? 0.10 : 0) + 0.05)

  const layers = {
    L1_hypothesis: {
      score: l1, grade: gradeOf(l1),
      criteria: {
        hypothesis_present: clamp(hLen > 0 ? 0.9 : 0),
        testability:        clamp(l1),
        specificity:        clamp(hLen > 150 ? 0.9 : hLen > 80 ? 0.7 : 0.5),
        design_alignment:   clamp(dt.includes('hypothesis') ? 0.85 : 0.5),
      },
      summary: `Hypothesis ${hLen > 100 ? 'is well-articulated' : hLen > 0 ? 'is present but could be more specific' : 'is missing'}.`,
      issues:      l1 < 0.7 ? ['Add explicit if-then conditional structure', 'Quantify expected outcome magnitude'] : [],
      suggestions: ['Use explicit if-then structure', 'Quantify expected outcomes where possible'],
    },
    L2_architect: {
      score: l2, grade: gradeOf(l2),
      criteria: {
        design_completeness:     clamp(hits / kws.length),
        variable_identification: clamp(dt.includes('variable') ? 0.85 : 0.4),
        control_specification:   clamp(dt.includes('control')  ? 0.80 : 0.35),
        procedure_clarity:       clamp(dl > 800 ? 0.9 : dl > 400 ? 0.65 : 0.35),
      },
      summary: `Design covers ${hits}/${kws.length} key methodology sections.`,
      issues:      l2 < 0.7 ? ['Missing design sections reduce reproducibility'] : [],
      suggestions: ['Add explicit control variable section', 'Define measurement procedures in detail'],
    },
    L3_simulation: {
      score: l3, grade: gradeOf(l3),
      criteria: {
        confidence_score:   clamp(confidence_score),
        simulation_success: status === 'success' ? 1.0 : 0.0,
        numerical_output:   clamp(nKeys > 0 ? 0.85 : 0.2),
        engine_reliability: clamp(engine_used ? 0.8 : 0.5),
      },
      summary: `Simulation ${status} with ${(confidence_score * 100).toFixed(0)}% confidence${engine_used ? ` via ${engine_used}` : ''}.`,
      issues:      status !== 'success' ? [`Simulation status: ${status} — check inputs`] : [],
      suggestions: ['Increase iterations for higher confidence', 'Validate with analytical solutions'],
    },
    L4_analysis: {
      score: l4, grade: gradeOf(l4),
      criteria: {
        numerical_depth:     clamp(Math.min(nKeys / 5, 1)),
        visualization_count: clamp(Math.min(nPlot / 4, 1)),
        data_richness:       clamp((nKeys + nPlot) > 0 ? 0.8 : 0.3),
        quantitative_output: clamp(nKeys > 2 ? 0.9 : nKeys > 0 ? 0.6 : 0.2),
      },
      summary: `${nKeys} numerical results and ${nPlot} visualizations produced.`,
      issues:      nPlot === 0 ? ['No visualizations generated — add plot outputs'] : [],
      suggestions: ['Add statistical significance tests', 'Include error bars and confidence intervals'],
    },
    L5_auditor: {
      score: l5, grade: gradeOf(l5),
      criteria: {
        observational_depth:  clamp(Math.min(nObs / 4, 1)),
        process_logging:      clamp(Math.min(nLog / 8, 1)),
        error_handling:       status === 'success' ? 0.9 : 0.3,
        methodology_coverage: clamp(dt.includes('method') ? 0.85 : 0.4),
      },
      summary: `${nObs} observations logged across ${nLog} pipeline steps.`,
      issues:      nObs === 0 ? ['No observations recorded'] : [],
      suggestions: ['Log intermediate checkpoints', 'Document assumptions and limitations explicitly'],
    },
    L6_memory: {
      score: l6, grade: gradeOf(l6),
      criteria: {
        domain_identification: clamp(domain ? 0.9 : 0.3),
        variable_breadth:      clamp(Math.min((nKeys + nPlot) / 6, 1)),
        domain_specificity:    clamp(domain && domain !== 'general' ? 0.85 : 0.5),
        interdisciplinary:     clamp(dl > 600 ? 0.75 : 0.45),
      },
      summary: `Domain: ${domain || 'General'}. ${nKeys + nPlot} total measured dimensions.`,
      issues:      !domain ? ['Domain not identified — specify research field'] : [],
      suggestions: ['Reference domain-specific standards', 'Compare against published benchmarks'],
    },
    L7_review: {
      score: l7, grade: gradeOf(l7),
      criteria: {
        reproducibility:        clamp(l5 * 0.9),
        data_transparency:      clamp(l4 * 0.95),
        hypothesis_testability: clamp(l1 * 0.9),
        methodological_rigor:   clamp((l2 + l5) / 2),
      },
      summary: `Report readiness derived from design quality and simulation outcomes.`,
      issues:      l7 < 0.7 ? ['Improve simulation confidence and design completeness'] : [],
      suggestions: ['Add literature cross-references', 'Structure output as formal research report'],
    },
  }

  const overallScore = Object.values(layers).reduce((sum, l) => sum + l.score, 0) / 7
  const sorted       = Object.entries(layers).sort((a, b) => a[1].score - b[1].score)

  return {
    run_id:             'sim_live',
    source:             'simulation',
    overall_score:      overallScore,
    eval_passed:        overallScore >= 0.7,
    pass_threshold:     0.7,
    layer_scores:       layers,
    weakest_layer:      sorted[0][0],
    strongest_layer:    sorted[sorted.length - 1][0],
    pipeline_log:       simulation_log,
    domain, engine_used, confidence_score,
    numerical_results,
    plot_count:         nPlot,
    obs_count:          nObs,
    evaluated_at:       new Date().toISOString(),
    eval_duration_s:    0,
    refinement_targets: sorted.filter(([, d]) => d.score < 0.7).map(([k]) => k),
    baseline_comparison:{ status: 'insufficient_history' },
  }
}

// ── Demo data (shown when nothing has been run yet) ───────────────────────
const DEMO_EVAL = computeEvalFromSimulation(
  {
    confidence_score: 0.82,
    status: 'success',
    hypothesis: 'If dropout regularization is increased from 0.2 to 0.5, then validation loss will decrease by at least 15%, reducing overfitting in the CNN model.',
    numerical_results: { accuracy: 0.923, val_loss: 0.231, f1_score: 0.889, precision: 0.901, recall: 0.878 },
    plot_data: [{ title: 'Loss Curve' }, { title: 'Accuracy' }, { title: 'Confusion Matrix' }],
    observations: ['Val loss stabilized at epoch 23', 'Dropout 0.5 outperforms 0.2', 'No signs of catastrophic forgetting'],
    simulation_log: ['[L1] Hypothesis parsed', '[L2] Design structured', '[L3] Simulation started', '[L3] Converged at epoch 23', '[L4] 5 metrics computed', '[L7] Review complete'],
    domain: 'machine_learning',
    engine_used: 'PyTorch',
  },
  'Hypothesis: Dropout regularization effect. Variables: dropout rate (independent), validation loss (dependent). Methodology: Train ResNet-18 with varied dropout rates, measure convergence. Control variables: learning rate, batch size. Expected outcomes: Higher dropout reduces overfitting. Limitations: Single dataset evaluation. Procedure: grid search across rates.'
)

// ══════════════════════════════════════════════════════════════════════════
// Visual sub-components
// ══════════════════════════════════════════════════════════════════════════

// ── Animated ring ──────────────────────────────────────────────────────────
function ScoreRing({ score, size = 140, stroke = 10, passed }) {
  const canvasRef = useRef(null)
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    let frame, current = 0
    const target = score, step = target / 60
    const animate = () => {
      current = Math.min(current + step, target)
      setDisplayed(current)
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const cx = size / 2, cy = size / 2, r = (size - stroke * 2) / 2
      ctx.clearRect(0, 0, size, size)
      // track
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = stroke; ctx.stroke()
      // fill
      const color = passed ? '#00ff88' : '#ffaa00'
      const start = -Math.PI / 2, end = start + Math.PI * 2 * current
      ctx.beginPath(); ctx.arc(cx, cy, r, start, end)
      ctx.strokeStyle = color; ctx.lineWidth = stroke; ctx.lineCap = 'round'; ctx.stroke()
      // glow
      ctx.beginPath(); ctx.arc(cx, cy, r, start, end)
      ctx.strokeStyle = passed ? 'rgba(0,255,136,0.14)' : 'rgba(255,170,0,0.14)'
      ctx.lineWidth = stroke + 10; ctx.lineCap = 'round'; ctx.stroke()
      if (current < target) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [score, size, stroke, passed])

  return (
    <div className="score-ring-wrap" style={{ width: size, height: size }}>
      <canvas ref={canvasRef} width={size} height={size} />
      <div className="score-ring-center">
        <span className="score-ring-pct" style={{ color: passed ? '#00ff88' : '#ffaa00' }}>
          {(displayed * 100).toFixed(1)}%
        </span>
        <span className="score-ring-lbl">{passed ? '✓ PASS' : '~ REVIEW'}</span>
      </div>
    </div>
  )
}

// ── Count-up number ────────────────────────────────────────────────────────
function CountUp({ target, suffix = '', decimals = 1, delay = 0 }) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => {
      let current = 0
      const step = target / 50
      const id = setInterval(() => {
        current = Math.min(current + step, target)
        setVal(current)
        if (current >= target) clearInterval(id)
      }, 20)
      return () => clearInterval(id)
    }, delay)
    return () => clearTimeout(t)
  }, [target, delay])
  return <span>{val.toFixed(decimals)}{suffix}</span>
}

// ── Animated bar ───────────────────────────────────────────────────────────
function AnimatedBar({ value, color, delay = 0 }) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setWidth(value * 100), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return (
    <div className="anim-bar-bg">
      <div className="anim-bar-fill"
        style={{ width: `${width}%`, background: color, transition: `width 0.9s cubic-bezier(.4,0,.2,1) ${delay}ms` }} />
    </div>
  )
}

// ── Radar chart (SVG) ──────────────────────────────────────────────────────
function RadarChart({ layers, size = 280 }) {
  const cx = size / 2, cy = size / 2, r = size * 0.37
  const names  = Object.keys(layers)
  const n      = names.length
  const scores = names.map(k => layers[k].score ?? 0)
  const toXY   = (angle, radius) => ({ x: cx + radius * Math.sin(angle), y: cy - radius * Math.cos(angle) })
  const step   = (Math.PI * 2) / n
  const rings  = [0.25, 0.5, 0.75, 1.0]
  const points = scores.map((s, i) => { const p = toXY(i * step, s * r); return `${p.x},${p.y}` }).join(' ')
  const axisPoints = names.map((_, i) => toXY(i * step, r))

  return (
    <svg className="radar-svg" width={size} height={size} style={{ overflow: 'visible' }}>
      {rings.map(ring => (
        <polygon key={ring} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={1}
          points={names.map((_, i) => { const p = toXY(i * step, ring * r); return `${p.x},${p.y}` }).join(' ')} />
      ))}
      {/* 70% threshold ring */}
      <polygon
        points={names.map((_, i) => { const p = toXY(i * step, 0.70 * r); return `${p.x},${p.y}` }).join(' ')}
        fill="none" stroke="rgba(255,170,0,0.35)" strokeWidth={1.5} strokeDasharray="4,3" />
      {axisPoints.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
      ))}
      {/* Data polygon */}
      <polygon points={points} fill="rgba(0,217,255,0.10)" stroke="#00d9ff" strokeWidth={2} />
      {/* Dots coloured by score */}
      {scores.map((s, i) => {
        const p = toXY(i * step, s * r)
        return <circle key={i} cx={p.x} cy={p.y} r={4} fill={scoreColor(s)} stroke="#000" strokeWidth={1.5} />
      })}
      {/* Labels */}
      {names.map((name, i) => {
        const p  = toXY(i * step, r + 26)
        const lm = LAYER_META[name] || {}
        return (
          <text key={i} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
            fontSize={10} fill="rgba(255,255,255,0.55)">
            {lm.icon} {lm.label || name}
          </text>
        )
      })}
      <text x={cx} y={cy - 0.70 * r - 6} textAnchor="middle" fontSize={8} fill="rgba(255,170,0,0.65)">70%</text>
    </svg>
  )
}

// ── Layer card ─────────────────────────────────────────────────────────────
function LayerCard({ name, data, isWeakest, isStrongest, index }) {
  const [expanded, setExpanded] = useState(false)
  const g   = data.grade || 'F'
  const meta = GRADE_META[g] || GRADE_META.F
  const lm  = LAYER_META[name] || { icon: '●', label: name, desc: '' }
  const s   = data.score ?? 0
  const bc  = scoreColor(s)

  return (
    <div
      className={`layer-card ${expanded ? 'expanded' : ''} ${isWeakest ? 'weakest' : ''} ${isStrongest ? 'strongest' : ''}`}
      onClick={() => setExpanded(e => !e)}
    >
      {isWeakest   && <div className="card-badge weakest-badge">WEAKEST</div>}
      {isStrongest && <div className="card-badge strongest-badge">BEST</div>}

      <div className="card-top">
        <div className="card-icon-name">
          <span className="card-icon">{lm.icon}</span>
          <div>
            <div className="card-name">{lm.label}</div>
            <div className="card-desc">{lm.desc}</div>
          </div>
        </div>
        <div className="grade-chip" style={{ color: meta.color, background: meta.bg }}>{g}</div>
      </div>

      <div className="card-bar-row">
        <AnimatedBar value={s} color={bc} delay={index * 80} />
        <span className="card-score-pct" style={{ color: bc }}>{(s * 100).toFixed(1)}%</span>
      </div>

      {data.summary && <p className="card-summary">{data.summary}</p>}

      {expanded && (
        <div className="card-detail" onClick={e => e.stopPropagation()}>
          {Object.keys(data.criteria || {}).length > 0 && (
            <div className="criteria-section">
              <div className="detail-heading">Criteria Breakdown</div>
              {Object.entries(data.criteria).map(([k, v]) => (
                <div key={k} className="crit-row">
                  <span className="crit-name">{k.replace(/_/g, ' ')}</span>
                  <AnimatedBar value={v} color={bc} delay={60} />
                  <span className="crit-val">{(v * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}
          {data.issues?.length > 0 && (
            <div className="issues-section">
              <div className="detail-heading issues-heading">⚠ Issues</div>
              <ul>{data.issues.map((x, i) => <li key={i} className="issue-item">{x}</li>)}</ul>
            </div>
          )}
          {data.suggestions?.length > 0 && (
            <div className="sug-section">
              <div className="detail-heading sug-heading">→ Suggestions</div>
              <ul>{data.suggestions.map((x, i) => <li key={i} className="sug-item">{x}</li>)}</ul>
            </div>
          )}
        </div>
      )}
      <div className="expand-hint">{expanded ? '▲ collapse' : '▼ details'}</div>
    </div>
  )
}

// ── Pipeline log ───────────────────────────────────────────────────────────
function PipelineLog({ log }) {
  const [filter, setFilter] = useState('all')
  const bottomRef = useRef(null)

  const filtered = (log || []).filter(line => {
    if (filter === 'all')   return true
    if (filter === 'sim')   return line.includes('[L3]') || line.toLowerCase().includes('sim')
    if (filter === 'error') return line.toLowerCase().includes('error') || line.toLowerCase().includes('fail')
    return true
  })

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [filtered.length])

  return (
    <div className="log-panel">
      <div className="log-header">
        <span className="log-title">Pipeline Log</span>
        <div className="log-filters">
          {['all', 'sim', 'error'].map(f => (
            <button key={f} className={`log-filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>
      {filtered.length === 0
        ? <div className="log-empty">No log entries yet. Run a simulation to populate.</div>
        : (
          <div className="log-scroll">
            {filtered.map((line, i) => (
              <div key={i} className={`log-line ${line.includes('[L3]') || line.toLowerCase().includes('sim') ? 'log-sim' : ''} ${(line.toLowerCase().includes('error') || line.toLowerCase().includes('fail')) ? 'log-err' : ''}`}>
                <span className="log-idx">{String(i + 1).padStart(3, '0')}</span>{line}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )
      }
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════
export default function EvaluationDashboard({ simulation, design }) {
  const [activeTab, setActiveTab]     = useState('overview')
  const [apiReports, setApiReports]   = useState([])
  const [pickedReport, setPickedReport] = useState(null)

  const isDemo = !simulation && !pickedReport

  // Compute live eval from simulation prop
  const liveEval = useMemo(() => {
    if (!simulation) return null
    return computeEvalFromSimulation(simulation, design)
  }, [simulation, design])

  // Which dataset to display: API pick > live sim > demo
  const evalData   = pickedReport || liveEval || DEMO_EVAL
  const { layer_scores: layers = {}, ...evRest } = evalData
  const {
    run_id, overall_score, eval_passed: passed, pass_threshold,
    weakest_layer, strongest_layer, eval_duration_s, evaluated_at,
    refinement_targets, pipeline_log, domain, engine_used,
    confidence_score: cs, numerical_results, plot_count, obs_count,
  } = evRest

  // Try to load historical API reports (non-blocking)
  useEffect(() => {
    fetch('http://localhost:8000/api/eval-reports')
      .then(r => r.json())
      .then(d => setApiReports(d.reports || []))
      .catch(() => {})
  }, [])

  const loadApiReport = async (runId) => {
    try {
      const res  = await fetch(`http://localhost:8000/api/eval-reports/${runId}`)
      const data = await res.json()
      setPickedReport(data)
    } catch {}
  }

  const TABS = ['overview', 'layers', 'insights', 'log']

  return (
    <div className="eval-dashboard">

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="eval-sidebar">
        <div className="sidebar-heading">Source</div>

        {liveEval && (
          <div
            className={`report-item ${!pickedReport ? 'active' : ''} passed`}
            onClick={() => setPickedReport(null)}
          >
            <div className="report-item-id">⚡ Live Simulation</div>
            <div className="report-item-meta">
              <span className="report-badge pass">LIVE</span>
              <span className="report-score">{(liveEval.overall_score * 100).toFixed(1)}%</span>
            </div>
          </div>
        )}

        {isDemo && (
          <div className="report-item active passed">
            <div className="report-item-id">📋 Demo Preview</div>
            <div className="report-item-meta">
              <span className="report-badge" style={{ background: 'rgba(255,170,0,0.1)', color: '#ffaa00' }}>DEMO</span>
              <span className="report-score">{(DEMO_EVAL.overall_score * 100).toFixed(1)}%</span>
            </div>
          </div>
        )}

        {apiReports.length > 0 && (
          <>
            <div className="sidebar-heading" style={{ marginTop: 16 }}>History</div>
            {apiReports.map(r => (
              <div
                key={r.run_id}
                className={`report-item ${pickedReport?.run_id === r.run_id ? 'active' : ''} ${r.eval_passed ? 'passed' : 'failed'}`}
                onClick={() => loadApiReport(r.run_id)}
              >
                <div className="report-item-id">{r.run_id}</div>
                <div className="report-item-meta">
                  <span className={`report-badge ${r.eval_passed ? 'pass' : 'fail'}`}>
                    {r.eval_passed ? '✓ PASS' : '✕ FAIL'}
                  </span>
                  <span className="report-score">{(r.overall_score * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </>
        )}
      </aside>

      {/* ── Main panel ───────────────────────────────────────────────────── */}
      <div className="eval-main">

        {/* Demo banner */}
        {isDemo && (
          <div className="demo-banner">
            <span>📋</span>
            <div>
              <strong>Demo Preview</strong> — Run a simulation in the <strong>Lab</strong> tab to see your real evaluation.
            </div>
          </div>
        )}

        {/* Live badge */}
        {liveEval && !pickedReport && (
          <div className="live-banner">
            <span className="live-dot" />
            <strong>Live Evaluation</strong> — Scored from your latest simulation result.
          </div>
        )}

        {/* Header */}
        <div className="eval-header">
          <div className="eval-header-left">
            <h2 className="eval-title">Evaluation Report</h2>
            <div className="eval-run-id">
              {run_id === 'sim_live' ? 'Source: Simulation Data' : `Run: ${run_id}`}
            </div>
            {evaluated_at && (
              <div className="eval-timestamp">{new Date(evaluated_at).toLocaleString()}</div>
            )}
          </div>
          <div className={`eval-verdict ${passed ? 'passed' : 'failed'}`}>
            <span className="verdict-icon">{passed ? '✓' : '~'}</span>
            <span className="verdict-text">{passed ? 'PASSED' : 'NEEDS IMPROVEMENT'}</span>
          </div>
        </div>

        {/* Refinement targets */}
        {refinement_targets?.length > 0 && (
          <div className="refinement-banner">
            <div className="rb-info">
              <span className="rb-icon">↩</span>
              <div>
                <div className="rb-title">
                  Layers below {((pass_threshold || 0.7) * 100).toFixed(0)}% threshold
                </div>
              </div>
            </div>
            <div className="rb-tags">
              {refinement_targets.map(t => (
                <span key={t} className="rb-tag">
                  {LAYER_ICONS[t] || '●'} {LAYER_META[t]?.label || t}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="eval-tabs">
          {TABS.map(tab => (
            <button
              key={tab}
              className={`eval-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'overview'  && '⬡ Overview'}
              {tab === 'layers'    && '⊞ Layers'}
              {tab === 'insights'  && '🔍 Insights'}
              {tab === 'log'       && '❯ Log'}
              {tab === 'memory'    && '🧠 Memory Metrics'}
            </button>
          ))}
        </div>

        {/* ── MEMORY METRICS ───────────────────────────────────────────── */}
        {activeTab === 'memory' && (
          <MemoryMetrics />
        )}

        {/* ── OVERVIEW ─────────────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="tab-content">
            <div className="overview-grid">

              {/* Score ring */}
              <div className="overview-ring-card">
                <ScoreRing score={overall_score} size={170} stroke={12} passed={passed} />
                <div className="ring-card-meta">
                  <div className="ring-meta-row">
                    <span className="ring-meta-label">Threshold</span>
                    <span className="ring-meta-val">{((pass_threshold || 0.7) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="ring-meta-row">
                    <span className="ring-meta-label">Layers</span>
                    <span className="ring-meta-val">{Object.keys(layers).length}</span>
                  </div>
                  <div className="ring-meta-row">
                    <span className="ring-meta-label">To Improve</span>
                    <span className="ring-meta-val" style={{ color: '#ff6b35' }}>
                      {refinement_targets?.length ?? 0}
                    </span>
                  </div>
                  {domain && (
                    <div className="ring-meta-row">
                      <span className="ring-meta-label">Domain</span>
                      <span className="ring-meta-val">{domain}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Radar */}
              <div className="overview-radar-card">
                <div className="card-section-title">Layer Performance Radar</div>
                <RadarChart layers={layers} size={290} />
              </div>

              {/* Stats */}
              <div className="overview-stats-col">
                <div className="stat-card strongest">
                  <div className="stat-icon">🏆</div>
                  <div className="stat-body">
                    <div className="stat-label">Strongest</div>
                    <div className="stat-val">
                      {LAYER_ICONS[strongest_layer]} {LAYER_META[strongest_layer]?.label || strongest_layer}
                    </div>
                    <div className="stat-sub">
                      {((layers[strongest_layer]?.score ?? 0) * 100).toFixed(1)}% — Grade {layers[strongest_layer]?.grade}
                    </div>
                  </div>
                </div>
                <div className="stat-card weakest">
                  <div className="stat-icon">⚠</div>
                  <div className="stat-body">
                    <div className="stat-label">Needs Work</div>
                    <div className="stat-val">
                      {LAYER_ICONS[weakest_layer]} {LAYER_META[weakest_layer]?.label || weakest_layer}
                    </div>
                    <div className="stat-sub">
                      {((layers[weakest_layer]?.score ?? 0) * 100).toFixed(1)}% — Grade {layers[weakest_layer]?.grade}
                    </div>
                  </div>
                </div>
                <div className="grade-dist-card">
                  <div className="card-section-title">Grade Distribution</div>
                  <div className="grade-dist">
                    {['A', 'B', 'C', 'D', 'F'].map(g => {
                      const count = Object.values(layers).filter(l => l.grade === g).length
                      return count > 0 ? (
                        <div key={g} className="grade-dist-item">
                          <span className="grade-dist-chip"
                            style={{ color: GRADE_META[g].color, background: GRADE_META[g].bg }}>
                            {g}
                          </span>
                          <span className="grade-dist-count">{count}</span>
                          <span className="grade-dist-label">{GRADE_META[g].label}</span>
                        </div>
                      ) : null
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* All layer bars */}
            <div className="all-bars-card">
              <div className="card-section-title">Score Breakdown — All Layers</div>
              <div className="all-bars">
                {Object.entries(layers).map(([name, data], i) => {
                  const s = data.score ?? 0
                  const c = scoreColor(s)
                  return (
                    <div key={name} className="bar-row">
                      <span className="bar-layer-name">{LAYER_ICONS[name]} {LAYER_META[name]?.label || name}</span>
                      <AnimatedBar value={s} color={c} delay={i * 60} />
                      <span className="bar-layer-score" style={{ color: c }}>{(s * 100).toFixed(1)}%</span>
                      <span className="bar-grade-chip" style={{ color: GRADE_META[data.grade]?.color }}>{data.grade}</span>
                    </div>
                  )
                })}
                <div className="threshold-line" style={{ left: `${(pass_threshold || 0.7) * 100}%` }}>
                  <div className="threshold-label">70% pass</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── LAYERS ───────────────────────────────────────────────────── */}
        {activeTab === 'layers' && (
          <div className="tab-content">
            <div className="layer-grid">
              {Object.entries(layers).map(([name, data], i) => (
                <LayerCard key={name} name={name} data={data}
                  isWeakest={name === weakest_layer}
                  isStrongest={name === strongest_layer}
                  index={i} />
              ))}
            </div>
          </div>
        )}

        {/* ── INSIGHTS ─────────────────────────────────────────────────── */}
        {activeTab === 'insights' && (
          <div className="tab-content">
            <div className="insights-grid">

              {/* Key metrics */}
              <div className="insights-metrics-card">
                <div className="card-section-title">Simulation Metrics</div>
                <div className="insights-metrics">
                  <div className="ins-metric">
                    <div className="ins-metric-val" style={{ color: scoreColor(cs || 0) }}>
                      <CountUp target={(cs || 0) * 100} suffix="%" delay={100} />
                    </div>
                    <div className="ins-metric-label">Confidence</div>
                  </div>
                  <div className="ins-metric">
                    <div className="ins-metric-val" style={{ color: '#00d9ff' }}>
                      <CountUp target={plot_count || 0} suffix="" decimals={0} delay={200} />
                    </div>
                    <div className="ins-metric-label">Plots</div>
                  </div>
                  <div className="ins-metric">
                    <div className="ins-metric-val" style={{ color: '#00ff88' }}>
                      <CountUp target={Object.keys(numerical_results || {}).length} suffix="" decimals={0} delay={300} />
                    </div>
                    <div className="ins-metric-label">Results</div>
                  </div>
                  <div className="ins-metric">
                    <div className="ins-metric-val" style={{ color: '#ffaa00' }}>
                      <CountUp target={obs_count || 0} suffix="" decimals={0} delay={400} />
                    </div>
                    <div className="ins-metric-label">Observations</div>
                  </div>
                </div>
                {(domain || engine_used) && (
                  <div className="ins-domain-row">
                    {domain && (
                      <>
                        <span className="ins-domain-label">Domain</span>
                        <span className="ins-domain-val">{domain}</span>
                      </>
                    )}
                    {engine_used && (
                      <>
                        <span className="ins-domain-label">Engine</span>
                        <span className="ins-domain-val">{engine_used}</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Numerical results */}
              {Object.keys(numerical_results || {}).length > 0 && (
                <div className="insights-results-card">
                  <div className="card-section-title">Numerical Results</div>
                  <div className="num-results-table">
                    {Object.entries(numerical_results).map(([k, v]) => (
                      <div key={k} className="num-result-row">
                        <span className="num-result-key">{k.replace(/_/g, ' ')}</span>
                        <span className="num-result-val">
                          {typeof v === 'number' ? v.toFixed(4) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Score formula */}
              <div className="insights-formula-card">
                <div className="card-section-title">How Each Score Was Derived</div>
                <div className="formula-rows">
                  {Object.entries(layers).map(([name, data]) => {
                    const lm = LAYER_META[name] || {}
                    return (
                      <div key={name} className="formula-row">
                        <span className="formula-icon">{lm.icon}</span>
                        <div className="formula-body">
                          <div className="formula-name">{lm.label}</div>
                          <div className="formula-desc">{data.summary}</div>
                        </div>
                        <span className="formula-score" style={{ color: scoreColor(data.score) }}>
                          {(data.score * 100).toFixed(1)}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── LOG ──────────────────────────────────────────────────────── */}
        {activeTab === 'log' && (
          <div className="tab-content">
            <PipelineLog log={pipeline_log} />
          </div>
        )}

      </div>
    </div>
  )
}
