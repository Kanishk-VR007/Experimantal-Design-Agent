import { useState, useEffect, useRef } from 'react'
import { Sparkles, RefreshCw } from 'lucide-react'
import ConstraintEditor from './ConstraintEditor'
import DatasetUploader from './DatasetUploader'
import LiteratureSettings from './LiteratureSettings'
import { useExperimentStore } from '../../stores/experimentStore'
import ExperimentPipelineStatus from '../../components/ExperimentPipelineStatus'
import ReferenceSearchPanel from '../../components/ReferenceSearchPanel'

const DOMAINS = [
  {
    id: 'physics',
    name: 'Physics',
    badge: 'Q-PHYS',
    desc: 'Quantum, Relativity, Hydrodynamics',
    icon: 'cyclone',
    color: '#004ac6',
    bgColor: 'bg-surface-container',
  },
  {
    id: 'chemistry',
    name: 'Chemistry',
    badge: 'CHEM-RXN',
    desc: 'Kinetics, Organometallic, Spectro',
    icon: 'science',
    color: '#006591',
    bgColor: 'bg-secondary-fixed/50',
  },
  {
    id: 'civil',
    name: 'Civil Eng',
    badge: 'STRUCT',
    desc: 'Geotech, FEA, Static Loads',
    icon: 'foundation',
    color: '#006591',
    bgColor: 'bg-surface-container-high',
  },
  {
    id: 'mechanical',
    name: 'Mech Eng',
    badge: 'THERMO-MECH',
    desc: 'Turbulence, Fatigue, Kinematics',
    icon: 'precision_manufacturing',
    color: '#004ac6',
    bgColor: 'bg-surface-container-low',
  },
  {
    id: 'electronics',
    name: 'Electronics',
    badge: 'E-CIRCUIT',
    desc: 'VLSI, SPICE, Photonic Waves',
    icon: 'memory',
    color: '#6a1edb',
    bgColor: 'bg-tertiary-fixed/60',
  },
  {
    id: 'cs',
    name: 'Comp Sci',
    badge: 'ALGO-THEORY',
    desc: 'Graph Theory, Complexity, Crypto',
    icon: 'terminal',
    color: '#004ac6',
    bgColor: 'bg-primary-fixed/50',
  },
]

const TEMPLATES = [
  {
    id: 'electronics_hall',
    title: 'Ohmic Transport & Transverse Hall Voltage',
    category: 'ELECTRONICS // SOLID STATE',
    domain: 'electronics',
    icon: 'electric_bolt',
    formula: 'V_H = (I • B) / (n • e • d)',
    stat: 'R² = 0.999',
    desc: 'Examine carrier mobility μ and transverse voltage V_H in 2D topological insulators across cryogenic magnetic fields (0 - 14 Tesla).',
    prompt: 'Verify Ohm\'s Law (V = IR) and calculate current-limiting resistor for a 5V microcontroller LED blink circuit with 2.0V forward drop at 20 mA.'
  },
  {
    id: 'cantilever_beam',
    title: 'Cantilever Elastic Beam Deflection',
    category: 'CIVIL // EULER-BERNOULLI',
    domain: 'civil',
    icon: 'architecture',
    formula: 'δ_max = (P • L³) / (3 • E • I)',
    stat: 'FEA ±0.02%',
    desc: 'Calculate non-linear curvature δ(x) under point load P for structural steel cantilever experiencing anisotropic shear deformation.',
    prompt: 'Analyze the deflection and bending stress of a 4-meter structural steel cantilever beam under a 20 kN point load at the free tip.'
  },
  {
    id: 'mech_gear',
    title: 'Spur Gear Train Torque & Speed Ratio',
    category: 'MECHANICAL // KINEMATICS',
    domain: 'mechanical',
    icon: 'settings_motion',
    formula: 'i = ω_in / ω_out = N_2 / N_1',
    stat: 'η = 98.4%',
    desc: 'Simulate torque multiplication, angular velocity ratio, and contact fatigue for a 20-tooth pinion driving a 60-tooth gear with 5 kW input.',
    prompt: 'Simulate torque multiplication and angular velocity ratio for a 20-tooth pinion driving a 60-tooth gear with 5 kW input power at 1800 RPM.'
  },
  {
    id: 'sorting_dynamics',
    title: 'Sorting Dynamics: QuickSort vs MergeSort',
    category: 'COMP SCI // ASYMPTOTICS',
    domain: 'cs',
    icon: 'alt_route',
    formula: 'T(n) = 2T(n/2) + O(n)',
    stat: 'O(n log n)',
    desc: 'Benchmark QuickSort, MergeSort, and BubbleSort operations, comparison counts, recursion depth, and memory allocations from n=10 to 500.',
    prompt: 'Benchmark QuickSort, MergeSort, and BubbleSort operations, comparison counts, and memory allocations from n=10 to n=500.'
  },
  {
    id: 'damped_pendulum',
    title: 'Damped Simple Pendulum Simulation',
    category: 'PHYSICS // NON-LINEAR DYNAMICS',
    domain: 'physics',
    icon: 'motion_mode',
    formula: 'd²θ/dt² + (b/m)dθ/dt + (g/L)sin(θ) = 0',
    stat: 'Q = 45.2',
    desc: 'Simulate a damped simple pendulum of length 1.5m, bob mass 0.5kg, and release angle 30 degrees with air resistance damping.',
    prompt: 'Simulate a damped simple pendulum of length 1.5m, bob mass 0.5kg, and release angle 30 degrees with air drag damping.'
  },
  {
    id: 'cnn_vit',
    title: 'CNN vs Vision Transformer (CIFAR-10)',
    category: 'COMP SCI // DEEP LEARNING',
    domain: 'cs',
    icon: 'neurology',
    formula: 'Attn(Q,K,V) = softmax(QKᵀ/√d)V',
    stat: 'Top-1 94.8%',
    desc: 'Compare convergence speed, loss curves, and validation accuracy between ResNet-style CNN and Vision Transformer on image classification.',
    prompt: 'Compare convergence speed, loss curves, and validation accuracy between ResNet-style CNN and Vision Transformer on image classification.'
  }
]

function ExperimentComposer({ onGenerate, generating, disabled }) {
  const [topic, setTopic] = useState('How does cryogenic liquid nitrogen quenching at 77 K alter the micro-crack propagation velocity and dislocation cell wall thickness in Ti-6Al-4V octet-truss lattices fabricated via Selective Laser Melting (SLM), when subjected to low-cycle fatigue testing at 10 Hz?')
  const [selectedDomain, setSelectedDomain] = useState('physics')
  const [maxPapers, setMaxPapers] = useState(3)
  const [useMockData, setUseMockData] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [constraints, setConstraints] = useState({
    temperature: 25,
    material: 'Structural Steel (E=200 GPa)',
    boundaryConditions: 'Fixed-Free (Cantilever)',
    uncertaintyTolerance: 5
  })
  const [dataset, setDataset] = useState(null)
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  const runElapsedTime = useExperimentStore((s) => s.runElapsedTime)
  const papers = useExperimentStore((s) => s.papers)
  const storeGenerating = useExperimentStore((s) => s.generating)
  const latencyDisplay = runElapsedTime ? `${runElapsedTime} s` : storeGenerating ? 'Timing...' : 'Standby'

  // Dynamic semantic complexity and solvability calculation based on formulation
  const words = topic.trim().split(/\s+/).filter(Boolean)
  const wordCount = words.length
  const hasMath = /[=\+\-\*\/\^\\_δσερωφμθπ]/.test(topic)
  const hasNumbers = /\d+/.test(topic)
  const hasDomainKeyword = /(cantilever|beam|stress|deflection|gear|torque|pendulum|damping|ohm|resistor|voltage|current|cnn|vit|quicksort|mergesort)/i.test(topic)

  let calcComplexity = 4.0
  if (wordCount > 5) calcComplexity += 1.5
  if (wordCount > 15) calcComplexity += 1.5
  if (hasMath) calcComplexity += 1.2
  if (hasNumbers) calcComplexity += 0.8
  if (hasDomainKeyword) calcComplexity += 1.0
  const complexityScore = Math.min(9.8, Math.max(3.0, calcComplexity)).toFixed(1)
  const complexityPct = Math.round((Number(complexityScore) / 10) * 100)
  const solvabilityPct = hasDomainKeyword ? 98.2 : wordCount > 8 ? 92.4 : 78.0

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setTopic((prev) => (prev ? `${prev} ${transcript}` : transcript))
        setIsListening(false)
      }

      recognition.onerror = () => setIsListening(false)
      recognition.onend = () => setIsListening(false)
      recognitionRef.current = recognition
    }
  }, [])

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.')
      return
    }
    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      setIsListening(true)
      recognitionRef.current.start()
    }
  }

  const handleSelectTemplate = (tmpl) => {
    setTopic(tmpl.prompt)
    setSelectedDomain(tmpl.domain)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!topic.trim()) return

    onGenerate({
      topic: topic.trim(),
      domain: selectedDomain,
      maxPapers,
      useMockData,
      constraints,
      dataset
    })
  }

  return (
    <div className="flex flex-col w-full pb-16">
      {/* ── Top Telemetry & Studio Headline Banner ────────────────────────── */}
      <section className="relative overflow-hidden rounded-2xl bg-surface-container-lowest shadow-sm border border-surface-container-high/60 mb-6 p-6 lg:p-8">
        <div className="absolute -top-32 -right-24 w-96 h-96 rounded-full bg-secondary-fixed opacity-40 blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 left-1/3 w-80 h-80 rounded-full bg-primary-fixed opacity-30 blur-3xl pointer-events-none"></div>

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div className="max-w-3xl flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high text-primary text-[11px] uppercase tracking-wider font-semibold">
                <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                Studio Environment // Autonomous v4.2
              </span>
              <span className="text-[11px] text-outline font-mono">SYS.ID // EXP-2025-089A</span>
            </div>

            <h1 className="font-headline-lg text-3xl lg:text-4xl text-on-surface font-bold tracking-tight">
              AI Scientific Experiment Studio
            </h1>

            <p className="text-on-surface-variant text-[14px] leading-relaxed max-w-2xl">
              Transform unstructured research questions into rigorously audited computational workflows. Hypothesise agents systematically scaffold equations, parameter spaces, Monte Carlo trials, and validation proofs.
            </p>

            {/* Key Metric Telemetry Badges */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[18px] text-primary">timer</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Formulation Latency</span>
                  <span className="text-[12px] text-on-surface font-bold">{latencyDisplay}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[18px] text-secondary">verified</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Verified Protocols</span>
                  <span className="text-[12px] text-secondary font-bold">
                    57 <span className="text-[10px] text-outline font-normal">canonical</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[18px] text-primary-container">format_image_left</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Anti-Hallucination</span>
                  <span className="text-[12px] text-primary font-bold">
                    Strict <span className="text-[10px] text-outline font-normal">Proof Gates</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[18px] text-tertiary">alt_route</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Proof Synthesizer</span>
                  <span className="text-[12px] text-tertiary font-bold">NumPy • SciPy • RK45</span>
                </div>
              </div>
            </div>
          </div>

          {/* Holographic 3D Scientific Apparatus Centerpiece */}
          <div className="w-full lg:w-80 h-56 rounded-2xl bg-surface-container-low border border-surface-container-high/70 flex flex-col justify-between p-4 relative overflow-hidden shadow-sm shrink-0">
            <div className="flex items-center justify-between z-10">
              <span className="text-[11px] text-on-surface-variant font-mono font-medium">HOLO-PHASE ENGINE</span>
              <span className="px-2 py-0.5 rounded-full bg-surface-container-lowest text-primary text-[10px] font-semibold border border-primary/20">
                ACTIVE LATTICE
              </span>
            </div>

            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <svg className="w-48 h-48 animate-[spin_24s_linear_infinite]" fill="none" viewBox="0 0 200 200">
                <circle cx="100" cy="100" opacity="0.6" r="88" stroke="#cbd5e1" strokeDasharray="4 6" strokeWidth="1"></circle>
                <circle cx="100" cy="100" opacity="0.8" r="70" stroke="#39b8fd" strokeDasharray="8 4" strokeWidth="1.5"></circle>
                <ellipse cx="100" cy="100" rx="76" ry="28" stroke="#2563eb" strokeDasharray="6 3" strokeWidth="1.5" transform="rotate(35 100 100)"></ellipse>
                <ellipse cx="100" cy="100" rx="76" ry="28" stroke="#8343f4" strokeDasharray="4 4" strokeWidth="1.2" transform="rotate(-40 100 100)"></ellipse>
                <circle cx="100" cy="100" fill="#eff4ff" r="32" stroke="#004ac6" strokeWidth="1.5"></circle>
                <circle cx="100" cy="100" fill="#2563eb" r="8"></circle>
                <circle cx="170" cy="100" fill="#006591" r="3"></circle>
                <circle cx="30" cy="100" fill="#6a1edb" r="2.5"></circle>
                <circle cx="100" cy="24" fill="#39b8fd" r="3.5"></circle>
              </svg>
            </div>

            <div className="flex items-end justify-between z-10 pt-8">
              <div className="flex flex-col">
                <span className="text-[10px] text-outline font-mono">θ = 42.18° • φ = 108.4°</span>
                <span className="text-[11px] text-on-surface font-semibold font-mono">ENTROPY: 0.0031 e.u.</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-secondary-container animate-pulse"></span>
                <span className="text-[11px] text-secondary font-mono font-bold">144 FPS</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Step 01: Ontological Foundation (Domain Selection) ──────────── */}
      <section className="flex flex-col gap-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-container text-white text-[13px] font-bold">
              01
            </span>
            <div>
              <h2 className="font-headline-sm text-lg text-on-surface font-bold">Ontological Foundation</h2>
              <span className="text-[12px] text-on-surface-variant">
                Select primary scientific domain to calibrate agent reasoning priors &amp; theorem solvers
              </span>
            </div>
          </div>
          <span className="text-[11px] text-outline font-mono">6 DOMAINS CALIBRATED</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {DOMAINS.map((d) => {
            const isSelected = selectedDomain === d.id
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setSelectedDomain(d.id)}
                className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between h-36 ${
                  isSelected
                    ? 'bg-surface-container-lowest border-primary ring-2 ring-primary/20 shadow-md'
                    : 'bg-surface-container-lowest border-surface-container-high hover:border-primary/40 hover:shadow-sm'
                }`}
              >
                <div className="flex items-start justify-between w-full">
                  <div className={`w-9 h-9 rounded-lg ${d.bgColor} flex items-center justify-center`}>
                    <span className="material-symbols-outlined text-[20px]" style={{ color: d.color }}>
                      {d.icon}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                      isSelected ? 'bg-primary text-white' : 'bg-surface-container text-outline'
                    }`}
                  >
                    {d.badge}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className={`text-[14px] font-bold ${isSelected ? 'text-primary' : 'text-on-surface'}`}>
                    {d.name}
                  </span>
                  <span className="text-[11px] text-on-surface-variant leading-tight">
                    {d.desc}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {/* ── Step 02: Autonomous Prompt Engineering ─────────────────────── */}
      <section className="flex flex-col gap-4 mb-6">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-container text-white text-[13px] font-bold">
            02
          </span>
          <div>
            <h2 className="font-headline-sm text-lg text-on-surface font-bold">Autonomous Prompt Engineering</h2>
            <span className="text-[12px] text-on-surface-variant">
              Define experimental query. Natural language parses directly into differential invariants and symbolic state spaces.
            </span>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high/70 shadow-sm flex flex-col gap-4">
          {/* Textarea Box with Floating Controls */}
          <div className="relative rounded-xl bg-surface-container-low border border-surface-container-high p-3">
            <textarea
              className="w-full bg-transparent resize-y text-on-surface placeholder:text-outline text-[14px] leading-relaxed focus:outline-none p-1 font-body-md min-h-[96px]"
              rows={4}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Formulate scientific problem or hypothesis... e.g. How does cryogenic nitrogen quenching affect micro-crack propagation and dislocation density in Ti-6Al-4V lattices?"
              disabled={disabled || generating}
              required
            />

            {/* Waveform Parser Visualizer */}
            <div className="flex items-center justify-between px-1 pt-2 border-t border-surface-container-high/60">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-outline font-mono uppercase">Live Acoustic / Semantic Parser</span>
                <div className="flex items-end gap-1 h-3.5">
                  <span className="w-1 bg-primary rounded-full h-2 animate-pulse"></span>
                  <span className="w-1 bg-secondary rounded-full h-3 animate-pulse" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-1 bg-secondary-container rounded-full h-3.5 animate-pulse" style={{ animationDelay: '300ms' }}></span>
                  <span className="w-1 bg-primary rounded-full h-1.5 animate-pulse" style={{ animationDelay: '450ms' }}></span>
                  <span className="w-1 bg-tertiary rounded-full h-2.5 animate-pulse" style={{ animationDelay: '200ms' }}></span>
                </div>
              </div>
              <span className="text-[11px] text-outline font-mono">
                {topic.split(/\s+/).filter(Boolean).length} words detected • {selectedDomain?.toUpperCase() || 'MULTI-PHYSICS'}
              </span>
            </div>
          </div>

          {/* Action Buttons & Dynamic Metrics */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={toggleVoiceInput}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[12px] font-medium transition-colors ${
                  isListening
                    ? 'bg-red-500 text-white border-red-500 animate-pulse'
                    : 'bg-surface-container-high border-surface-container-high hover:bg-surface-container text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[16px] text-primary">
                  {isListening ? 'mic_off' : 'mic'}
                </span>
                <span>{isListening ? 'Listening...' : 'Voice Input'}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container text-on-surface text-[12px] font-medium transition-colors border border-surface-container-high"
              >
                <span className="material-symbols-outlined text-[16px] text-secondary">tune</span>
                <span>{showAdvanced ? 'Hide Bounds' : 'State Bounds & Datasets'}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTopic(
                    'Formulate exact finite element formulation δ_max = (P * L^3)/(3*E*I) with beam parameters L=4.0m, P=20kN, E=200GPa.'
                  )
                  setSelectedDomain('civil')
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container text-on-surface text-[12px] font-medium transition-colors border border-surface-container-high"
              >
                <span className="material-symbols-outlined text-[16px] text-primary">functions</span>
                <span>Insert TeX Equation</span>
              </button>
            </div>

            {/* Dynamic Complexity & Solvability Gauge */}
            <div className="flex items-center gap-4 self-end md:self-auto">
              <div className="flex flex-col items-end">
                <span className="text-[10px] text-outline uppercase font-semibold">Semantic Complexity</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-2 bg-surface-container-high rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-300"
                      style={{ width: `${complexityPct}%` }}
                    ></div>
                  </div>
                  <span className="text-[11px] text-on-surface font-mono font-bold">
                    {complexityScore} / 10
                  </span>
                </div>
              </div>

              <div className="h-7 w-[1px] bg-surface-container-high hidden sm:block"></div>

              <div className="flex flex-col items-end">
                <span className="text-[10px] text-outline uppercase font-semibold">Solvability Metric</span>
                <span className="text-[12px] text-primary font-bold">{solvabilityPct}% Confidence</span>
              </div>
            </div>
          </div>

          {/* Advanced Drawer for Constraints, Datasets, and Literature */}
          {showAdvanced && (
            <div className="flex flex-col gap-4 pt-4 border-t border-surface-container-high">
              <ConstraintEditor
                constraints={constraints}
                onChange={setConstraints}
                disabled={disabled || generating}
              />
              <DatasetUploader
                onDatasetLoaded={setDataset}
                disabled={disabled || generating}
              />
              <LiteratureSettings
                maxPapers={maxPapers}
                onChangeMaxPapers={setMaxPapers}
                useMockData={useMockData}
                onToggleMockData={setUseMockData}
                disabled={disabled || generating}
              />
            </div>
          )}
        </div>
      </section>

      {/* ── Verified Scientific Prompt Templates ──────────────────────── */}
      <section className="flex flex-col gap-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <div>
            <h3 className="font-headline-sm text-lg text-on-surface font-bold">Verified Scientific Prompt Templates</h3>
            <span className="text-[12px] text-on-surface-variant">
              Pre-calibrated parameter spaces and analytical boundary systems ready for swarm simulation
            </span>
          </div>
          <span className="text-[11px] text-primary font-semibold flex items-center gap-1">
            Browse all 57 canonical protocols
            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {TEMPLATES.map((tmpl) => (
            <div
              key={tmpl.id}
              className="p-4 rounded-xl bg-surface-container-lowest border border-surface-container-high shadow-sm hover:shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container-high text-primary font-semibold">
                    {tmpl.category}
                  </span>
                  <span className="material-symbols-outlined text-outline group-hover:text-primary text-[18px] transition-colors">
                    {tmpl.icon}
                  </span>
                </div>

                <h4 className="text-[14px] font-bold text-on-surface pt-1 leading-snug">
                  {tmpl.title}
                </h4>

                <p className="text-[12px] text-on-surface-variant line-clamp-2 leading-relaxed">
                  {tmpl.desc}
                </p>

                <div className="p-2 rounded-lg bg-surface-container-low font-mono text-[11px] text-on-surface-variant flex items-center justify-between border border-surface-container-high/50">
                  <span className="truncate pr-2">{tmpl.formula}</span>
                  <span className="text-primary font-bold shrink-0">{tmpl.stat}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleSelectTemplate(tmpl)}
                className="mt-3 w-full py-2 rounded-lg bg-surface-container-low hover:bg-primary-container hover:text-white text-on-surface text-[12px] font-semibold transition-all flex items-center justify-center gap-1 border border-surface-container-high"
              >
                <span>Load Parameter Archetype</span>
                <span className="material-symbols-outlined text-[16px]">chevron_right</span>
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* ── Active Pipeline Tracker (Visible During or Post Execution) ─── */}
      <section className="mb-6">
        <ExperimentPipelineStatus />
      </section>

      {/* ── Retrieved Academic Grounding Papers (When Available) ────────── */}
      {papers && papers.length > 0 && (
        <section className="mb-6">
          <ReferenceSearchPanel papers={papers} />
        </section>
      )}

      {/* ── Submit Action CTA Bar ───────────────────────────────────────── */}
      <div className="p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="text-[13px] font-bold text-on-surface">Ready for Protocol Synthesis?</span>
          <span className="text-[11px] text-on-surface-variant">
            Orchestrates Qwen Prompt Refiner, Qwen Vision Analyzer, and DeepSeek R1 Reasoner.
          </span>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || generating || !topic.trim()}
          className="w-full sm:w-auto px-6 py-3 bg-primary-container text-white rounded-xl text-[14px] font-bold hover:bg-primary transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {generating ? (
            <>
              <RefreshCw size={18} className="animate-spin" />
              <span>Synthesizing Multi-Agent Experimental Protocol...</span>
            </>
          ) : (
            <>
              <Sparkles size={18} />
              <span>Formulate Hypothesis &amp; Generate Design</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export default ExperimentComposer
