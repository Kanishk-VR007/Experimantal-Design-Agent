import { useState, useEffect } from 'react'
import ExperimentForm from './components/ExperimentForm'
import ExperimentOutput from './components/ExperimentOutput'
import SimulationRunner from './components/SimulationRunner'
import SimulationResults from './components/SimulationResults'
import EvaluationDashboard from './components/EvaluationDashboard'
import StatusBar from './components/StatusBar'
import './App.css'

function App() {
  const [status, setStatus] = useState({ loading: true })
  const [generating, setGenerating] = useState(false)
  const [showSimulationRunner, setShowSimulationRunner] = useState(false)
  const [output, setOutput] = useState({
    papers: [],
    design: '',
    streaming: false,
    complete: false
  })
  const [simulation, setSimulation] = useState(null)
  const [currentTopic, setCurrentTopic] = useState('')
  const [activeView, setActiveView] = useState('design') // 'design' | 'simulation' | 'evaluation'

  // Check backend health on mount
  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/health')
      const data = await response.json()
      setStatus({
        loading: false,
        healthy: data.status === 'healthy',
        ollamaAvailable: data.ollama_available,
        models: data.models
      })
    } catch (error) {
      setStatus({
        loading: false,
        healthy: false,
        error: 'Cannot connect to backend server'
      })
    }
  }

  const handleGenerate = async (formData) => {
    setGenerating(true)
    setCurrentTopic(formData.topic)
    setSimulation(null)  // Clear previous simulation
    setOutput({
      papers: [],
      design: '',
      streaming: true,
      complete: false
    })

    try {
      // Use EventSource for Server-Sent Events
      const eventSource = new EventSource(
        `http://localhost:8000/api/generate-design?${new URLSearchParams({
          topic: formData.topic,
          max_papers: formData.maxPapers,
          use_mock_data: formData.useMockData
        })}`
      )

      // For POST requests, we need to use fetch with streaming
      const response = await fetch('http://localhost:8000/api/generate-design', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: formData.topic,
          max_papers: formData.maxPapers,
          use_mock_data: formData.useMockData
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              switch (data.type) {
                case 'start':
                  console.log('Generation started')
                  break
                
                case 'papers':
                  setOutput(prev => ({
                    ...prev,
                    papers: data.papers
                  }))
                  break
                
                case 'chunk':
                  setOutput(prev => ({
                    ...prev,
                    design: prev.design + data.text
                  }))
                  break
                
                case 'complete':
                  setOutput(prev => ({
                    ...prev,
                    streaming: false,
                    complete: true
                  }))
                  setGenerating(false)
                  break
                
                case 'error':
                  console.error('Error:', data.message)
                  setGenerating(false)
                  setOutput(prev => ({
                    ...prev,
                    streaming: false,
                    error: data.message
                  }))
                  break
              }
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Generation error:', error)
      setGenerating(false)
      setOutput(prev => ({
        ...prev,
        streaming: false,
        error: error.message
      }))
    }
  }

  const handleRunSimulation = () => {
    if (!output.design || !output.complete) {
      alert('Please generate an experimental design first!')
      return
    }
    setShowSimulationRunner(true)
    setActiveView('simulation')
  }

  const handleSimulationComplete = (simulationData) => {
    setSimulation(simulationData)
  }

  const handleCloseSimulationRunner = () => {
    setShowSimulationRunner(false)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔬 Experimental Design Agent</h1>
        <p>AI-powered scientific experiment designer using Ollama</p>
      </header>

      <StatusBar status={status} onRefresh={checkHealth} />

      {/* ── Top-level navigation ───────────────────────────────── */}
      <nav className="app-nav">
        <button
          className={`app-nav-btn ${activeView !== 'evaluation' ? 'active' : ''}`}
          onClick={() => setActiveView(simulation ? 'simulation' : 'design')}
        >
          🔬 Lab
        </button>
        <button
          className={`app-nav-btn ${activeView === 'evaluation' ? 'active' : ''}`}
          onClick={() => setActiveView('evaluation')}
        >
          📊 Evaluation
        </button>
      </nav>

      {/* ── Evaluation view ─────────────────────────────────────── */}
      {activeView === 'evaluation' && (
        <div className="eval-page">
          <EvaluationDashboard simulation={simulation} design={output.design} />
        </div>
      )}

      {/* ── Lab view ────────────────────────────────────────────── */}
      {activeView !== 'evaluation' && (
      <div className="app-container">
        <div className="sidebar">
          <ExperimentForm 
            onGenerate={handleGenerate}
            generating={generating}
            disabled={!status.healthy || status.loading}
          />
        </div>

        <div className="main-content">
          {/* View Toggle (only show when simulation exists) */}
          {simulation && (
            <div className="view-toggle">
              <button 
                className={`toggle-btn ${activeView === 'design' ? 'active' : ''}`}
                onClick={() => setActiveView('design')}
              >
                📄 Experimental Design
              </button>
              <button 
                className={`toggle-btn ${activeView === 'simulation' ? 'active' : ''}`}
                onClick={() => setActiveView('simulation')}
              >
                🔬 Simulation Report
              </button>
            </div>
          )}

          {/* Design View */}
          {activeView === 'design' && (
            <ExperimentOutput 
              papers={output.papers}
              design={output.design}
              streaming={output.streaming}
              complete={output.complete}
              error={output.error}
              onRunSimulation={handleRunSimulation}
              hasSimulation={simulation !== null}
            />
          )}

          {/* Simulation Report View */}
          {activeView === 'simulation' && simulation && (
            <SimulationResults simulation={simulation} />
          )}
        </div>
      </div>
      )} {/* end lab view */}

      {/* Simulation Runner Modal */}
      {showSimulationRunner && (
        <SimulationRunner
          topic={currentTopic}
          design={output.design}
          onSimulationComplete={handleSimulationComplete}
          onClose={handleCloseSimulationRunner}
        />
      )}
    </div>
  )
}

export default App
