import { X, Beaker, FileText, Atom } from 'lucide-react'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useExperimentStore } from '../../stores/experimentStore'

function InspectorPanel() {
  const toggleInspector = useWorkspaceStore((s) => s.toggleInspector)
  const activeView = useWorkspaceStore((s) => s.activeView)

  const topic = useExperimentStore((s) => s.topic)
  const domain = useExperimentStore((s) => s.domain)
  const papers = useExperimentStore((s) => s.papers)
  const generating = useExperimentStore((s) => s.generating)
  const simulating = useExperimentStore((s) => s.simulating)
  const complete = useExperimentStore((s) => s.complete)
  const streaming = useExperimentStore((s) => s.streaming)
  const simulation = useExperimentStore((s) => s.simulation)

  const getStatusLabel = () => {
    if (generating && streaming) return 'Streaming design...'
    if (generating) return 'Generating...'
    if (simulating) return 'Running simulation...'
    if (complete) return 'Complete'
    return 'Idle'
  }

  const getStatusColor = () => {
    if (generating || simulating) return 'var(--accent-primary)'
    if (complete) return 'var(--accent-success)'
    return 'var(--text-muted)'
  }

  return (
    <aside className="inspector-panel glass-strong">
      {/* Header */}
      <div className="inspector-header">
        <h3 className="inspector-title">Inspector</h3>
        <button className="inspector-close-btn" onClick={toggleInspector}>
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div className="inspector-content">
        {/* Experiment Summary */}
        <div className="inspector-section">
          <div className="inspector-section-header">
            <Beaker size={14} />
            <span>Experiment</span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">Topic</span>
            <span className="inspector-field-value">
              {topic || <span className="text-muted">Not set</span>}
            </span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">Domain</span>
            <span className="inspector-field-value">
              {domain || <span className="text-muted">Auto-detect</span>}
            </span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">Papers</span>
            <span className="inspector-field-value">{papers.length}</span>
          </div>
        </div>

        {/* Status */}
        <div className="inspector-section">
          <div className="inspector-section-header">
            <FileText size={14} />
            <span>Status</span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">State</span>
            <span
              className="inspector-field-value"
              style={{ color: getStatusColor() }}
            >
              {getStatusLabel()}
            </span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">Simulation</span>
            <span className="inspector-field-value">
              {simulation ? (
                <span style={{ color: 'var(--accent-success)' }}>Available</span>
              ) : (
                <span className="text-muted">None</span>
              )}
            </span>
          </div>
        </div>

        {/* View info */}
        <div className="inspector-section">
          <div className="inspector-section-header">
            <Atom size={14} />
            <span>View</span>
          </div>
          <div className="inspector-field">
            <span className="inspector-field-label">Active</span>
            <span className="inspector-field-value">{activeView}</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default InspectorPanel
