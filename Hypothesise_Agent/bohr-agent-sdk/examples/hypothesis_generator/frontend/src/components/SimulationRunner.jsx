import { useState, useEffect } from 'react'
import './SimulationRunner.css'

function SimulationRunner({ topic, design, onSimulationComplete, onClose }) {
  const [status, setStatus] = useState('initializing') // initializing, running, success, error
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    runSimulation()
  }, [])

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev, { timestamp, message, type }])
  }

  const runSimulation = async () => {
    try {
      setStatus('running')
      addLog('🚀 Starting simulation engine...', 'info')
      setProgress(10)

      await new Promise(resolve => setTimeout(resolve, 500))
      addLog('📊 Analyzing experimental design...', 'info')
      setProgress(25)

      await new Promise(resolve => setTimeout(resolve, 300))
      addLog('🔍 Detecting domain and experiment type...', 'info')
      setProgress(40)

      const response = await fetch('http://localhost:8000/api/run-simulation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: topic,
          design: design,
          domain: null  // Auto-detect from design
        })
      })

      setProgress(60)
      addLog('⚙️ Running simulation algorithms...', 'info')

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `Simulation failed: ${response.statusText}`)
      }

      await new Promise(resolve => setTimeout(resolve, 500))
      addLog('📈 Generating plots and results...', 'info')
      setProgress(80)

      const data = await response.json()
      setResult(data.simulation)
      
      setProgress(100)
      addLog('✅ Simulation completed successfully!', 'success')
      setStatus('success')

      // Notify parent component
      if (onSimulationComplete) {
        onSimulationComplete(data.simulation)
      }

    } catch (error) {
      console.error('Simulation error:', error)
      setError(error.message)
      setStatus('error')
      addLog(`❌ Error: ${error.message}`, 'error')
    }
  }

  return (
    <div className="simulation-runner-overlay">
      <div className="simulation-runner-container">
        <div className="simulation-runner-header">
          <h2>🔬 Running Simulation</h2>
          {status === 'success' && (
            <button className="close-btn" onClick={onClose}>×</button>
          )}
        </div>

        {/* Progress Bar */}
        <div className="progress-section">
          <div className="progress-bar-container">
            <div 
              className={`progress-bar ${status}`}
              style={{ width: `${progress}%` }}
            >
              <span className="progress-text">{progress}%</span>
            </div>
          </div>
          <p className="status-text">
            {status === 'initializing' && '⏳ Initializing...'}
            {status === 'running' && '⚙️ Simulation in progress...'}
            {status === 'success' && '✅ Simulation completed!'}
            {status === 'error' && '❌ Simulation failed'}
          </p>
        </div>

        {/* Simulation Info */}
        <div className="simulation-info">
          <div className="info-card">
            <span className="info-label">Topic:</span>
            <span className="info-value">{topic}</span>
          </div>
          {result && (
            <>
              <div className="info-card">
                <span className="info-label">Engine Used:</span>
                <span className="info-value">{result.engine_used}</span>
              </div>
              <div className="info-card">
                <span className="info-label">Domain:</span>
                <span className="info-value">{result.domain}</span>
              </div>
              <div className="info-card">
                <span className="info-label">Confidence:</span>
                <span className="info-value">{(result.confidence_score * 100).toFixed(0)}%</span>
              </div>
            </>
          )}
        </div>

        {/* Simulation Logs */}
        <div className="logs-section">
          <h3>📋 Simulation Logs</h3>
          <div className="logs-container">
            {logs.map((log, index) => (
              <div key={index} className={`log-entry log-${log.type}`}>
                <span className="log-timestamp">[{log.timestamp}]</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-section">
            <h3>❌ Error Details</h3>
            <pre className="error-message">{error}</pre>
          </div>
        )}

        {/* Action Buttons */}
        <div className="action-buttons">
          {status === 'success' && (
            <button className="btn-primary" onClick={onClose}>
              📊 View Full Report
            </button>
          )}
          {status === 'error' && (
            <button className="btn-secondary" onClick={onClose}>
              Close
            </button>
          )}
          {status === 'running' && (
            <div className="spinner-container">
              <div className="spinner"></div>
              <span>Processing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SimulationRunner
