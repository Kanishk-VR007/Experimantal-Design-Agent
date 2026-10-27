import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import LiquidLoader from './LiquidLoader'

function ExperimentOutput({ papers, design, streaming, complete, error, onRunSimulation, hasSimulation }) {
  const outputRef = useRef(null)

  // Auto-scroll as content streams in
  useEffect(() => {
    if (streaming && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [design, streaming])

  if (error) {
    return (
      <div className="output-container">
        <div className="error-message">
          <h3>❌ Error</h3>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (!papers.length && !design && !streaming) {
    return (
      <div className="output-container">
        <div className="empty-state">
          <div className="empty-icon">🔬</div>
          <h3>Ready to Generate</h3>
          <p>Enter your research topic and click "Generate Design" to start.</p>
          <div className="features">
            <div className="feature">
              <span className="feature-icon">📚</span>
              <span>Analyzes research papers</span>
            </div>
            <div className="feature">
              <span className="feature-icon">🎯</span>
              <span>Generates testable hypotheses</span>
            </div>
            <div className="feature">
              <span className="feature-icon">⚡</span>
              <span>Real-time streaming output</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Show liquid loader when starting generation (fetching papers)
  if (streaming && !papers.length && !design) {
    return (
      <div className="output-container">
        <LiquidLoader message="Analyzing Research Papers..." />
      </div>
    )
  }

  return (
    <div className="output-container">
      {/* Research Papers Section */}
      {papers.length > 0 && (
        <div className="papers-section">
          <h2>📚 Research Papers ({papers.length})</h2>
          <div className="papers-grid">
            {papers.map((paper, index) => (
              <div key={index} className="paper-card">
                <div className="paper-header">
                  <span className="paper-badge">{paper.source}</span>
                  {paper.citations > 0 && (
                    <span className="citation-count">📊 {paper.citations} citations</span>
                  )}
                </div>
                <h3>{paper.title}</h3>
                <p className="paper-authors">
                  {paper.authors.slice(0, 3).join(', ')}
                  {paper.authors.length > 3 && ' et al.'}
                </p>
                <p className="paper-abstract">{paper.abstract}</p>
                {paper.url && (
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" className="paper-link">
                    View Paper →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Experimental Design Section */}
      {(design || streaming) && (
        <div className="design-section">
          <div className="design-header">
            <h2>🧪 Experimental Design</h2>
            <div className="design-actions">
              {streaming && (
                <span className="streaming-indicator">
                  <span className="pulse"></span>
                  Streaming...
                </span>
              )}
              {complete && !streaming && onRunSimulation && (
                <button 
                  className="simulation-button"
                  onClick={onRunSimulation}
                >
                  {hasSimulation ? '🔄 Re-run Simulation' : '▶️ Run Simulation'}
                </button>
              )}
              {complete && (
                <span className="complete-indicator">
                  ✓ Complete
                </span>
              )}
            </div>
          </div>

          <div className="design-content" ref={outputRef}>
            <ReactMarkdown>{design}</ReactMarkdown>
            {streaming && <span className="cursor">▊</span>}
          </div>

          {complete && (
            <div className="design-actions">
              <button 
                className="btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(design)
                }}
              >
                📋 Copy to Clipboard
              </button>
              <button 
                className="btn-secondary"
                onClick={() => {
                  const blob = new Blob([design], { type: 'text/markdown' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'experimental_design.md'
                  a.click()
                }}
              >
                💾 Download
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ExperimentOutput
