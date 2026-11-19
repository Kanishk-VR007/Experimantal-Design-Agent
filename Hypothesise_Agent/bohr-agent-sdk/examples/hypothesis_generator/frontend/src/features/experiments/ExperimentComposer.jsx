import { useState, useEffect, useRef } from 'react'
import { Sparkles, RefreshCw, Search, Image as ImageIcon, Mic, MicOff, Sliders, FunctionSquare, ArrowRight } from 'lucide-react'
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
  const textareaRef = useRef(null)

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

  const handleSubmit = (e) => {
    if (e && e.preventDefault) e.preventDefault()
    if (!topic.trim() || disabled || generating) return

    onGenerate({
      topic: topic.trim(),
      domain: selectedDomain,
      maxPapers,
      useMockData,
      constraints,
      dataset
    })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col w-full pb-16">
      {/* ── Studio Header & Architecture Telemetry (Clean, Modern AI Chat Banner) ── */}
      <section className="relative overflow-hidden rounded-2xl bg-surface-container-lowest shadow-sm border border-surface-container-high/60 mb-6 p-6 lg:p-7">
        <div className="absolute -top-32 -right-24 w-96 h-96 rounded-full bg-secondary-fixed opacity-30 blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 left-1/3 w-80 h-80 rounded-full bg-primary-fixed opacity-20 blur-3xl pointer-events-none"></div>

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div className="max-w-4xl flex flex-col gap-2.5">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high text-primary text-[11px] uppercase tracking-wider font-semibold">
                <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                Studio Environment // Autonomous v4.2
              </span>
              <span className="text-[11px] text-outline font-mono">SYS.ID // EXP-2025-089A</span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl text-on-surface font-bold tracking-tight">
              AI Scientific Experiment Studio
            </h1>

            <p className="text-on-surface-variant text-[13px] leading-relaxed max-w-3xl">
              Transform unstructured research questions into rigorously audited computational workflows. Hypothesise agents systematically scaffold equations, parameter spaces, Monte Carlo trials, and validation proofs.
            </p>

            {/* Key Metric Telemetry Badges */}
            <div className="flex flex-wrap items-center gap-2.5 pt-1">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[17px] text-primary">timer</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Formulation Latency</span>
                  <span className="text-[12px] text-on-surface font-bold">{latencyDisplay}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[17px] text-secondary">verified</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Verified Protocols</span>
                  <span className="text-[12px] text-secondary font-bold">
                    57 <span className="text-[10px] text-outline font-normal">canonical</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[17px] text-primary-container">format_image_left</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Anti-Hallucination</span>
                  <span className="text-[12px] text-primary font-bold">
                    Strict <span className="text-[10px] text-outline font-normal">Proof Gates</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 shadow-sm">
                <span className="material-symbols-outlined text-[17px] text-tertiary">alt_route</span>
                <div className="flex flex-col">
                  <span className="text-[10px] text-outline uppercase font-semibold">Proof Synthesizer</span>
                  <span className="text-[12px] text-tertiary font-bold">NumPy • SciPy • RK45</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Chat Option (FIRST) — Modern Conversational AI Interface ──────── */}
      <section className="flex flex-col gap-3 mb-6">
        <div className="p-5 md:p-6 rounded-2xl bg-surface-container-lowest border border-surface-container-high/80 shadow-sm hover:shadow-md transition-shadow flex flex-col gap-4">
          
          {/* Conversational Textarea Container */}
          <div className="relative rounded-xl bg-surface-container-low border border-surface-container-high/80 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all p-3.5">
            <textarea
              ref={textareaRef}
              className="w-full bg-transparent resize-y text-on-surface placeholder:text-outline/70 text-[14px] md:text-[15px] leading-relaxed focus:outline-none p-1 font-body-md min-h-[105px]"
              rows={4}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything, formulate a scientific problem, or state your research hypothesis... e.g. How does cryogenic nitrogen quenching affect micro-crack propagation velocity in Ti-6Al-4V octet-truss lattices?"
              disabled={disabled || generating}
              required
            />

            {/* Waveform Acoustic Visualizer & Live Metadata */}
            <div className="flex items-center justify-between px-1 pt-2.5 border-t border-surface-container-high/60">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-outline font-mono uppercase tracking-wider">Live Acoustic / Semantic Parser</span>
                <div className="flex items-end gap-1 h-3.5">
                  <span className="w-1 bg-primary rounded-full h-2 animate-pulse"></span>
                  <span className="w-1 bg-secondary rounded-full h-3 animate-pulse" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-1 bg-secondary-container rounded-full h-3.5 animate-pulse" style={{ animationDelay: '300ms' }}></span>
                  <span className="w-1 bg-primary rounded-full h-1.5 animate-pulse" style={{ animationDelay: '450ms' }}></span>
                  <span className="w-1 bg-tertiary rounded-full h-2.5 animate-pulse" style={{ animationDelay: '200ms' }}></span>
                </div>
              </div>
              <span className="text-[11px] text-outline font-mono">
                {wordCount} words detected • {selectedDomain?.toUpperCase() || 'MULTI-PHYSICS'}
              </span>
            </div>
          </div>

          {/* Chat Tool Actions & The Search Image / Twinkling Star Action Button */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 pt-1">
            
            {/* Left Tools: Voice Input, Parameter Bounds, TeX Equation */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={toggleVoiceInput}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-[12px] font-medium transition-colors ${
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
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container-high hover:bg-surface-container text-on-surface text-[12px] font-medium transition-colors border border-surface-container-high"
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
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container-high hover:bg-surface-container text-on-surface text-[12px] font-medium transition-colors border border-surface-container-high"
              >
                <span className="material-symbols-outlined text-[16px] text-primary">functions</span>
                <span>Insert TeX Equation</span>
              </button>
            </div>

            {/* Right Side: Complexity Meter & Search Image Formulate/Simulate Button */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
              
              {/* Dynamic Solvability & Complexity Gauge */}
              <div className="flex items-center justify-between sm:justify-end gap-3 px-1">
                <div className="flex flex-col items-start sm:items-end">
                  <span className="text-[10px] text-outline uppercase font-semibold">Semantic Complexity</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-surface-container-high rounded-full overflow-hidden">
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

              {/* ── SEARCH IMAGE BUTTON WITH SMALL TWINKLING STAR AT THE TOP ── */}
              {/* Acts as the Formulate Hypothesis & Simulate Button */}
              <button
                type="button"
                onClick={handleSubmit}
                disabled={disabled || generating || !topic.trim()}
                className="relative group px-5 py-2.5 bg-gradient-to-r from-primary-container via-primary to-blue-700 hover:from-primary hover:to-primary-container text-white rounded-xl text-[13px] md:text-[14px] font-bold shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2.5 disabled:opacity-50 disabled:cursor-not-allowed select-none overflow-visible shrink-0"
                title="Search reference diagrams, formulate multi-agent hypothesis, and run simulation"
              >
                {/* Small Twinkling Star at the Top */}
                <span className="absolute -top-2.5 right-3 flex items-center justify-center pointer-events-none z-20">
                  <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative flex items-center justify-center text-amber-400 text-[14px] font-black drop-shadow-[0_0_6px_rgba(251,191,36,0.85)] animate-pulse">
                    ✦
                  </span>
                </span>

                {generating ? (
                  <>
                    <RefreshCw size={17} className="animate-spin text-white" />
                    <span>Synthesizing &amp; Simulating...</span>
                  </>
                ) : (
                  <>
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[19px] text-white">image_search</span>
                    </span>
                    <span>Formulate Hypothesis &amp; Simulate</span>
                    <span className="hidden xl:inline text-[11px] opacity-75 font-mono font-normal pl-0.5">↵ Enter</span>
                  </>
                )}
              </button>
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

      {/* ── Ontological Foundation (Domain Selection) — Below Chat Option ── */}
      <section className="flex flex-col gap-3.5 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-container text-white text-[13px] font-bold">
              01
            </span>
            <div>
              <h2 className="font-headline-sm text-base md:text-lg text-on-surface font-bold">Ontological Foundation</h2>
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
    </div>
  )
}

export default ExperimentComposer
