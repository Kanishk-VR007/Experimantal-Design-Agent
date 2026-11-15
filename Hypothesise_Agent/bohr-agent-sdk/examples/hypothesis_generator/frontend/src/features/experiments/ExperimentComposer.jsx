import { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Send, Sparkles, RefreshCw, AlertCircle } from 'lucide-react'
import DomainSelector from './DomainSelector'
import PromptTemplateGallery from './PromptTemplateGallery'
import ConstraintEditor from './ConstraintEditor'
import DatasetUploader from './DatasetUploader'
import LiteratureSettings from './LiteratureSettings'

const DOMAIN_PLACEHOLDERS = {
  cs: "e.g. Compare convergence speed and validation accuracy of CNN vs Vision Transformer on CIFAR-10, or analyze Dijkstra's shortest path and BFS exploration on an 8-node weighted network graph...",
  civil: "e.g. Analyze the deflection and bending stress of a 4-meter structural steel cantilever beam under a 20 kN point load at the free tip, verifying Euler-Bernoulli theory...",
  mechanical: "e.g. Simulate torque multiplication, pitch line velocity, and angular speed ratio for a 20-tooth pinion driving a 60-tooth spur gear with 5 kW input power at 1800 RPM...",
  electronics: "e.g. Verify Ohm's Law (V = IR) and compute the current-limiting resistor for a 5V microcontroller driving an LED with 2.0V forward drop at 20 mA...",
  physics: "e.g. Simulate a damped simple pendulum of length 1.5m, bob mass 0.5kg, and release angle 30 degrees with air resistance damping...",
  chemistry: "e.g. Measure UV-Vis absorbance spectrum and molar extinction coefficient of aqueous Nickel(II) Chloride at 390nm and 720nm..."
}

function ExperimentComposer({ onGenerate, generating, disabled }) {
  const [topic, setTopic] = useState('')
  const [objective, setObjective] = useState('')
  const [hypothesis, setHypothesis] = useState('')
  const [selectedDomain, setSelectedDomain] = useState(null)
  const [maxPapers, setMaxPapers] = useState(3)
  const [useMockData, setUseMockData] = useState(false)
  const [constraints, setConstraints] = useState({
    temperature: 25,
    material: 'Structural Steel (E=200 GPa)',
    boundaryConditions: 'Fixed-Free (Cantilever)',
    uncertaintyTolerance: 5
  })
  const [dataset, setDataset] = useState(null)
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  // Initialize Web Speech API for voice-to-text if supported
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

      recognition.onerror = () => {
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
    }
  }, [])

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Google Chrome or Edge.')
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
    setTopic(tmpl.topic)
    setSelectedDomain(tmpl.domain)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!topic.trim()) return

    onGenerate({
      topic: topic.trim(),
      objective: objective.trim(),
      hypothesis: hypothesis.trim(),
      domain: selectedDomain,
      maxPapers,
      useMockData,
      constraints,
      dataset
    })
  }

  const activePlaceholder = selectedDomain
    ? DOMAIN_PLACEHOLDERS[selectedDomain] || "Describe your scientific premise, target variables, and physical parameters..."
    : "Select a scientific domain above or enter any research topic in Civil, Mechanical, Computer Science, Electronics, or Physics..."

  return (
    <div className="experiment-composer-container">
      <div className="composer-header">
        <div className="composer-title-group">
          <h2>🔬 AI Scientific Experiment Studio</h2>
          <p>Autonomous Research Formulation, Literature Synthesis &amp; Multi-Physics Simulation</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="composer-form">
        {/* Research Topic Card with Integrated Domain Selection */}
        <div className="composer-input-card">
          {/* Explicit Domain Selector (User-chosen to prevent hallucination) */}
          <DomainSelector
            selectedDomain={selectedDomain}
            onSelectDomain={setSelectedDomain}
            disabled={disabled || generating}
          />

          <div className="input-card-header" style={{ marginTop: '16px' }}>
            <label htmlFor="research-topic">
              Research Question / Experimental Premise <span className="required-star">*</span>
              {selectedDomain && (
                <span style={{ marginLeft: '8px', fontSize: '0.75rem', color: 'var(--accent-primary)', fontWeight: 500 }}>
                  (Targeting {selectedDomain.toUpperCase()})
                </span>
              )}
            </label>
            <button
              type="button"
              className={`voice-mic-btn ${isListening ? 'listening' : ''}`}
              onClick={toggleVoiceInput}
              disabled={disabled || generating}
              title={isListening ? 'Listening... click to stop' : 'Click to dictate prompt via voice'}
            >
              {isListening ? <MicOff size={15} color="#ef4444" /> : <Mic size={15} />}
              <span>{isListening ? 'Listening...' : 'Voice Input'}</span>
            </button>
          </div>

          <textarea
            id="research-topic"
            className="main-topic-textarea"
            rows={4}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={activePlaceholder}
            disabled={disabled || generating}
            required
          />

          {/* Benchmark scientific templates */}
          <PromptTemplateGallery
            onSelectTemplate={handleSelectTemplate}
            disabled={disabled || generating}
          />
        </div>

        {/* Advanced Constraints & Parameter Bounds */}
        <ConstraintEditor
          constraints={constraints}
          onChange={setConstraints}
          disabled={disabled || generating}
        />

        {/* Reference Empirical Dataset Uploader */}
        <DatasetUploader
          onDatasetLoaded={setDataset}
          disabled={disabled || generating}
        />

        {/* Literature & Mock Settings */}
        <LiteratureSettings
          maxPapers={maxPapers}
          onChangeMaxPapers={setMaxPapers}
          useMockData={useMockData}
          onToggleMockData={setUseMockData}
          disabled={disabled || generating}
        />

        {/* Submit Execution Action */}
        <div className="composer-action-bar">
          <button
            type="submit"
            className="btn-submit-generate"
            disabled={disabled || generating || !topic.trim()}
          >
            {generating ? (
              <>
                <RefreshCw size={18} className="spinner-rotate" />
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
      </form>
    </div>
  )
}

export default ExperimentComposer
