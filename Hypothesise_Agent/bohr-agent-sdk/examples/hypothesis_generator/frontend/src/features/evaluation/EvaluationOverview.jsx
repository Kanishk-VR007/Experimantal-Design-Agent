import { useState } from 'react'
import { Award, BarChart3, CheckCircle2 } from 'lucide-react'

const RADAR_DIMENSIONS = [
  { name: '1. Theoretical Rigor & Grounding', score: 98, weight: '20%', verdict: 'PASS' },
  { name: '2. Experimental Reproducibility', score: 97, weight: '15%', verdict: 'PASS' },
  { name: '3. Multi-Physics Simulation Fidelity', score: 99, weight: '25%', verdict: 'VERIFIED' },
  { name: '4. Statistical Verification & CI', score: 95, weight: '15%', verdict: 'PASS' },
  { name: '5. Adversarial Robustness', score: 96, weight: '10%', verdict: 'PASS' },
  { name: '6. Continuous Memory Calibration', score: 98, weight: '5%', verdict: 'OPTIMAL' },
  { name: '7. Publication Readiness Grade', score: 97, weight: '10%', verdict: 'TIER A+' },
]

const AUDITED_RUNS = [
  {
    id: '#EXP-2024-8842',
    title: 'Timoshenko Cantilever 3D Elastic Field',
    domain: 'CIVIL',
    score: 98.4,
    pValue: 'p < 0.0001',
    status: 'Tier A+',
    date: '2026-11-18',
  },
  {
    id: '#EXP-2024-8839',
    title: "Ohm's Law in Non-Ideal Thin-Film Circuit",
    domain: 'ELECTRONICS',
    score: 97.2,
    pValue: 'p < 0.0002',
    status: 'Tier A',
    date: '2026-11-18',
  },
  {
    id: '#EXP-2024-8835',
    title: 'Spur Gear Train Kinematics & Contact Fatigue',
    domain: 'MECHANICAL',
    score: 98.9,
    pValue: 'p < 0.00001',
    status: 'Tier A+',
    date: '2026-11-17',
  },
  {
    id: '#EXP-2024-8828',
    title: 'Damped Simple Pendulum Non-Linear Phase Portrait',
    domain: 'PHYSICS',
    score: 99.1,
    pValue: 'p < 0.00001',
    status: 'Tier A+',
    date: '2026-11-17',
  },
  {
    id: '#EXP-2024-8820',
    title: 'CNN vs Vision Transformer (CIFAR-10) Convergence',
    domain: 'COMP SCI',
    score: 96.8,
    pValue: 'p < 0.001',
    status: 'Tier A',
    date: '2026-11-16',
  },
]

function EvaluationOverview({ simulation, design }) {
  const [filterDomain, setFilterDomain] = useState('ALL')

  const compositeScore = 96.4
  const filteredRuns = filterDomain === 'ALL'
    ? AUDITED_RUNS
    : AUDITED_RUNS.filter(r => r.domain === filterDomain)

  return (
    <div className="flex flex-col w-full p-4 lg:p-6 pb-20 select-none gap-6">
      {/* ── Div 0: Header with ISO Conformance Badge & Actions ─────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed-variant text-[11px] font-semibold font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              ISO-17025 Conformance
            </span>
            <span className="text-[11px] text-outline font-mono">HASH: 0x9e88...2d1a</span>
          </div>

          <h1 className="font-headline-sm text-2xl lg:text-3xl font-bold text-on-surface tracking-tight">
            Scientific Evaluation &amp; Validation Cockpit
          </h1>

          <p className="text-[13px] text-on-surface-variant max-w-2xl">
            Multi-dimensional empirical verification, peer-review audit matrices, and cryptographic validation proofs for autonomous research formulations.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start lg:self-auto">
          <button
            type="button"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-container-high hover:bg-surface-container text-on-surface text-[12px] font-semibold transition-colors border border-surface-container-high"
          >
            <span className="material-symbols-outlined text-[17px] text-primary">download</span>
            <span>Export Audit Package</span>
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-container text-white text-[12px] font-semibold hover:bg-primary transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-[17px]">verified_user</span>
            <span>Run Full Audit Suite</span>
          </button>
        </div>
      </div>

      {/* ── Div 1: 4 Key Telemetry Metrics ─────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-outline font-semibold uppercase">Audited Runs</span>
            <span className="material-symbols-outlined text-[18px] text-primary">science</span>
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="font-mono text-2xl font-bold text-on-surface">142</span>
            <span className="text-[11px] text-emerald-600 font-semibold">+12 today</span>
          </div>
          <span className="text-[10px] text-outline mt-1 font-mono">Across 7 calibrated domains</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-outline font-semibold uppercase">Reproducibility</span>
            <span className="material-symbols-outlined text-[18px] text-secondary">verified</span>
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="font-mono text-2xl font-bold text-secondary">98.7%</span>
            <span className="text-[11px] text-outline">NIST Validated</span>
          </div>
          <span className="text-[10px] text-outline mt-1 font-mono">Variance σ &lt; 0.004</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-outline font-semibold uppercase">Math Invariants</span>
            <span className="material-symbols-outlined text-[18px] text-tertiary">functions</span>
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="font-mono text-2xl font-bold text-tertiary">99.2%</span>
            <span className="text-[11px] text-outline">Z3 Pass</span>
          </div>
          <span className="text-[10px] text-outline mt-1 font-mono">1,280 closed-form proofs</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-outline font-semibold uppercase">Confidence Floor</span>
            <span className="material-symbols-outlined text-[18px] text-primary">analytics</span>
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="font-mono text-2xl font-bold text-primary">99.4%</span>
            <span className="text-[11px] text-outline">Bayesian σ</span>
          </div>
          <span className="text-[10px] text-outline mt-1 font-mono">Student-t CI α=0.05</span>
        </div>
      </div>

      {/* ── Div 2: Big Tier A+ Overall Score Banner ────────────────────────── */}
      <div className="p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative overflow-hidden">
        <div className="flex items-center gap-6">
          <div className="flex flex-col">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-4xl lg:text-5xl font-extrabold text-primary">
                {compositeScore}
              </span>
              <span className="text-sm font-bold text-outline">/ 100 PTS</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold uppercase tracking-wider">
                Tier A+ Verified
              </span>
              <span className="text-xs text-outline font-semibold">• Publication Ready</span>
            </div>
          </div>

          <div className="h-12 w-[1px] bg-surface-container-high hidden md:block"></div>

          <p className="text-[13px] text-on-surface-variant max-w-xl leading-relaxed hidden sm:block">
            Autonomous multi-agent protocol synthesis cleared peer-grade scrutiny without manual hallucination repairs. Differential invariants and Monte Carlo trials verified against verified canonical formulations.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 shrink-0">
          <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high">
            <span className="text-[10px] text-outline block">Literature Grounding</span>
            <span className="font-mono text-xs font-bold text-on-surface">98.2%</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high">
            <span className="text-[10px] text-outline block">Analytical Accuracy</span>
            <span className="font-mono text-xs font-bold text-primary">99.1%</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high">
            <span className="text-[10px] text-outline block">Reproducibility</span>
            <span className="font-mono text-xs font-bold text-secondary">98.7%</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high">
            <span className="text-[10px] text-outline block">Z3 Proof Verification</span>
            <span className="font-mono text-xs font-bold text-tertiary">97.4%</span>
          </div>
        </div>
      </div>

      {/* ── Div 3: 7-Axis Evaluation Radar & Vectors (12 cols) ─────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Radar SVG Chart (6 cols) */}
        <div className="xl:col-span-6 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-primary">radar</span>
              <span className="font-headline-sm text-base font-bold text-on-surface">
                Empirical Evaluation Radar
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-primary font-bold">
              7-AXIS VECTORS
            </span>
          </div>

          <div className="relative w-full h-[340px] flex items-center justify-center">
            <svg className="w-full h-full" viewBox="0 0 400 340" fill="none">
              {/* Concentric Polygons */}
              <polygon points="200,40 330,105 330,235 200,300 70,235 70,105" stroke="#dce9ff" strokeWidth="1" fill="#eff4ff" fillOpacity="0.4" />
              <polygon points="200,80 295,125 295,215 200,260 105,215 105,125" stroke="#dce9ff" strokeWidth="1" fill="none" />
              <polygon points="200,120 260,145 260,195 200,220 140,195 140,145" stroke="#dce9ff" strokeWidth="1" fill="none" />

              {/* Axis rays */}
              <line x1="200" y1="170" x2="200" y2="40" stroke="#c3c6d7" strokeWidth="1" />
              <line x1="200" y1="170" x2="330" y2="105" stroke="#c3c6d7" strokeWidth="1" />
              <line x1="200" y1="170" x2="330" y2="235" stroke="#c3c6d7" strokeWidth="1" />
              <line x1="200" y1="170" x2="200" y2="300" stroke="#c3c6d7" strokeWidth="1" />
              <line x1="200" y1="170" x2="70" y2="235" stroke="#c3c6d7" strokeWidth="1" />
              <line x1="200" y1="170" x2="70" y2="105" stroke="#c3c6d7" strokeWidth="1" />

              {/* Data polygon */}
              <polygon
                points="200,45 325,110 320,230 200,295 75,230 75,110"
                fill="#2563eb"
                fillOpacity="0.25"
                stroke="#2563eb"
                strokeWidth="2.5"
              />

              {/* Data points */}
              <circle cx="200" cy="45" r="4.5" fill="#2563eb" />
              <circle cx="325" cy="110" r="4.5" fill="#006591" />
              <circle cx="320" cy="230" r="4.5" fill="#6a1edb" />
              <circle cx="200" cy="295" r="4.5" fill="#16a34a" />
              <circle cx="75" cy="230" r="4.5" fill="#004ac6" />
              <circle cx="75" cy="110" r="4.5" fill="#8343f4" />

              {/* Labels */}
              <text x="200" y="28" textAnchor="middle" fill="#0b1c30" fontSize="10" fontWeight="700">Rigor 98%</text>
              <text x="345" y="105" textAnchor="start" fill="#0b1c30" fontSize="10" fontWeight="700">Reprod. 97%</text>
              <text x="345" y="235" textAnchor="start" fill="#0b1c30" fontSize="10" fontWeight="700">Fidelity 99%</text>
              <text x="200" y="318" textAnchor="middle" fill="#0b1c30" fontSize="10" fontWeight="700">Stats 95%</text>
              <text x="55" y="235" textAnchor="end" fill="#0b1c30" fontSize="10" fontWeight="700">Robust. 96%</text>
              <text x="55" y="105" textAnchor="end" fill="#0b1c30" fontSize="10" fontWeight="700">Memory 98%</text>
            </svg>
          </div>
        </div>

        {/* 7-Axis Vector Table (6 cols) */}
        <div className="xl:col-span-6 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
            <span className="font-headline-sm text-base font-bold text-on-surface">Criteria Breakdown</span>
            <span className="text-[10px] text-outline font-mono">WEIGHTED COMPOSITE</span>
          </div>

          <div className="flex flex-col gap-2.5">
            {RADAR_DIMENSIONS.map((dim, idx) => (
              <div key={idx} className="p-2.5 rounded-xl bg-surface-container-low border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-semibold text-on-surface">{dim.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-primary font-bold">{dim.score}%</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">
                      {dim.verdict}
                    </span>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: `${dim.score}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Div 4: Adversarial Stress Diagnostic ───────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-6 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-secondary">security</span>
              <span className="font-headline-sm text-sm font-bold text-on-surface">
                Adversarial Stress Diagnostic
              </span>
            </div>
            <span className="text-[11px] font-mono text-emerald-600 font-bold">97.0% Score</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-[12px]">
            <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
              <span className="text-[10px] text-outline font-semibold uppercase block">Hallucination Index</span>
              <span className="font-mono text-base font-bold text-emerald-600">0.0000 %</span>
              <span className="text-[10px] text-outline block mt-0.5">Zero unverifiable claims</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
              <span className="text-[10px] text-outline font-semibold uppercase block">Boundary Perturbation</span>
              <span className="font-mono text-base font-bold text-primary">0.02% drift</span>
              <span className="text-[10px] text-outline block mt-0.5">10,000 Monte Carlo runs</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
              <span className="text-[10px] text-outline font-semibold uppercase block">Prior Contamination</span>
              <span className="font-mono text-base font-bold text-emerald-600">0.000 %</span>
              <span className="text-[10px] text-outline block mt-0.5">Blind verification passed</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-surface-container-high/60">
              <span className="text-[10px] text-outline font-semibold uppercase block">Confounder Resilience</span>
              <span className="font-mono text-base font-bold text-secondary">98.4 %</span>
              <span className="text-[10px] text-outline block mt-0.5">Anti-bias verified</span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-6 p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-surface-container-high pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-tertiary">gavel</span>
              <span className="font-headline-sm text-sm font-bold text-on-surface">
                Formal Verification Proof Matrix
              </span>
            </div>
            <span className="text-[10px] font-mono text-outline">Z3 + LEAN 4 SOLVER</span>
          </div>

          <div className="flex flex-col gap-2 font-mono text-[11px]">
            <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 flex items-center justify-between">
              <span className="text-on-surface">Invariant 1: Energy conservation ∂E/∂t + ∇•J = 0</span>
              <span className="text-emerald-600 font-bold">PROVEN</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 flex items-center justify-between">
              <span className="text-on-surface">Invariant 2: Clamped boundary deflection w(0) = 0</span>
              <span className="text-emerald-600 font-bold">PROVEN</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 flex items-center justify-between">
              <span className="text-on-surface">Invariant 3: Bending curvature consistency M = -EI(w'')</span>
              <span className="text-emerald-600 font-bold">PROVEN</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 flex items-center justify-between">
              <span className="text-on-surface">Invariant 4: Student-t distribution CI α=0.05</span>
              <span className="text-primary font-bold">VALIDATED</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Div 5: Audited Experiment Ledger Table ─────────────────────────── */}
      <div className="p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-container-high pb-3">
          <div>
            <h3 className="font-headline-sm text-base font-bold text-on-surface">Audited Experiment Ledger</h3>
            <span className="text-[12px] text-on-surface-variant">
              142 total records • Real-time ledger of swarm-audited hypotheses, validation grades, and manifests
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {['ALL', 'CIVIL', 'ELECTRONICS', 'PHYSICS', 'COMP SCI'].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setFilterDomain(d)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
                  filterDomain === d
                    ? 'bg-primary-container text-white'
                    : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-surface-container-high text-outline text-[11px] uppercase font-mono">
                <th className="py-2.5 px-3">Run ID</th>
                <th className="py-2.5 px-3">Experiment Title</th>
                <th className="py-2.5 px-3">Domain</th>
                <th className="py-2.5 px-3">Validation</th>
                <th className="py-2.5 px-3">Significance</th>
                <th className="py-2.5 px-3">Grade</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => (
                <tr key={run.id} className="border-b border-surface-container-high/60 hover:bg-surface-container-low/50 transition-colors">
                  <td className="py-2.5 px-3 font-mono font-bold text-primary">{run.id}</td>
                  <td className="py-2.5 px-3 font-semibold text-on-surface">{run.title}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-surface-container text-outline text-[10px] font-mono">
                      {run.domain}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono font-bold text-on-surface">{run.score}%</td>
                  <td className="py-2.5 px-3 font-mono text-outline">{run.pValue}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                      {run.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button className="text-primary font-semibold hover:underline">Inspect</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default EvaluationOverview
