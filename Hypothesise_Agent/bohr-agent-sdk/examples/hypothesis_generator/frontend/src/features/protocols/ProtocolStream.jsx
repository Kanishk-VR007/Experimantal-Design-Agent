import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import ExportToolbar from './ExportToolbar'

function cleanMarkdownFence(text) {
  if (!text) return ''
  let out = text.replace(/^\s*```(?:markdown|md)?\s*\r?\n/i, '')
  out = out.replace(/\r?\n```\s*$/i, '')
  return out
}

function ProtocolStream({
  design,
  streaming,
  complete,
  topic,
  papers,
  onRunSimulation,
  hasSimulation,
  simulating
}) {
  const contentRef = useRef(null)

  useEffect(() => {
    if (streaming && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [design, streaming])

  const wordCount = design ? design.trim().split(/\s+/).length : 0

  return (
    <div className="protocol-stream-container">
      <div className="protocol-stream-header">
        <div className="stream-status-group">
          <h3>🧪 Autonomous Experimental Protocol</h3>
          {streaming && (
            <span className="streaming-badge">
              <span className="pulse-dot" />
              Streaming tokens via SSE...
            </span>
          )}
          {complete && !streaming && (
            <span className="complete-badge">
              ✓ Protocol Synthesis Complete ({wordCount} words)
            </span>
          )}
        </div>

        <div className="stream-header-actions">
          <ExportToolbar designText={design} topic={topic} papers={papers} />
          {complete && !streaming && onRunSimulation && (
            <button
              type="button"
              className="btn-run-simulation-cta"
              onClick={onRunSimulation}
              disabled={simulating}
            >
              {simulating ? 'Running Simulation...' : hasSimulation ? '🔄 Re-run Simulation' : '▶️ Run Numerical Simulation'}
            </button>
          )}
        </div>
      </div>

      <div className="protocol-stream-body" ref={contentRef}>
        {design ? (
          <div className="markdown-body">
            <ReactMarkdown>{cleanMarkdownFence(design)}</ReactMarkdown>
            {streaming && <span className="stream-cursor">▊</span>}
          </div>
        ) : (
          <div className="empty-stream-state">
            <p>Protocol stream will appear here in real-time as the agent designs the experiment.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ProtocolStream

