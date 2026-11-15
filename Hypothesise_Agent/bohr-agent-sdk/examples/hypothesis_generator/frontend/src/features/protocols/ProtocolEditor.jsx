import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, Edit3, BookOpen } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import ExportToolbar from './ExportToolbar'

const PROTOCOL_SECTIONS = [
  { id: 'sec_hypo', title: '1. Formulated Hypothesis & Scientific Premise', icon: '🎯' },
  { id: 'sec_vars', title: '2. Independent, Dependent & Controlled Variables', icon: '⚖️' },
  { id: 'sec_design', title: '3. Experimental Architecture & Physical Controls', icon: '🏗️' },
  { id: 'sec_method', title: '4. Step-by-Step Methodology & Instrumentation', icon: '🔬' },
  { id: 'sec_data', title: '5. Statistical Data Analysis & Verification Solvers', icon: '📊' },
  { id: 'sec_outcomes', title: '6. Expected Numerical Outcomes & Boundary Limits', icon: '📈' },
  { id: 'sec_limits', title: '7. Experimental Limitations & Confounding Factors', icon: '⚠️' }
]

function ProtocolEditor({ design, topic, papers }) {
  const [openSections, setOpenSections] = useState({
    sec_hypo: true,
    sec_vars: true,
    sec_design: true,
    sec_method: true,
    sec_data: true,
    sec_outcomes: true,
    sec_limits: true,
  })

  const toggleSection = (id) => {
    setOpenSections((prev) => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  return (
    <div className="protocol-editor-container">
      <div className="editor-header">
        <div className="title-area">
          <BookOpen size={20} color="var(--accent-primary)" />
          <h3>7-Section Peer-Review Protocol Specification</h3>
        </div>
        <ExportToolbar designText={design} topic={topic} papers={papers} />
      </div>

      <div className="protocol-sections-accordion">
        {PROTOCOL_SECTIONS.map((sec) => {
          const isOpen = openSections[sec.id]
          return (
            <div key={sec.id} className="protocol-section-card">
              <div
                className="section-card-header"
                onClick={() => toggleSection(sec.id)}
              >
                <div className="header-left">
                  <span className="section-icon">{sec.icon}</span>
                  <span className="section-title">{sec.title}</span>
                </div>
                <div className="header-right">
                  <span className="status-indicator-badge">Validated</span>
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
              </div>

              {isOpen && (
                <div className="section-card-body">
                  <div className="section-rendered-content">
                    <ReactMarkdown>{design || '_Generating section protocol..._'}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ProtocolEditor

