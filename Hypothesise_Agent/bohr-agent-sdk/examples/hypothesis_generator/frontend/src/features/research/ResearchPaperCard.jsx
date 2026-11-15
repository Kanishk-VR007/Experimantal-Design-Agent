import { useState } from 'react'
import { ExternalLink, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'

function ResearchPaperCard({ paper }) {
  const [expanded, setExpanded] = useState(false)
  const isSemantic = paper.source?.toLowerCase().includes('semantic')
  const badgeColor = isSemantic ? '#0284c7' : '#d97706'

  const authorsText = Array.isArray(paper.authors)
    ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '')
    : (paper.authors || 'Unknown Authors')

  return (
    <div className="research-paper-card">
      <div className="card-top-row">
        <span className="source-pill" style={{ background: `${badgeColor}20`, color: badgeColor, borderColor: `${badgeColor}50` }}>
          {paper.source || 'arXiv'}
        </span>
        {paper.citations > 0 && (
          <span className="citations-pill">
            ★ {paper.citations} citations
          </span>
        )}
      </div>

      <h4 className="paper-card-title">{paper.title}</h4>
      <p className="paper-card-authors">{authorsText}</p>

      <div className={`paper-card-abstract ${expanded ? 'expanded' : 'collapsed'}`}>
        {paper.abstract}
      </div>

      <div className="paper-card-footer">
        {paper.abstract && paper.abstract.length > 180 && (
          <button
            type="button"
            className="btn-expand-abstract"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <><span>Less</span><ChevronUp size={14} /></>
            ) : (
              <><span>Read Abstract</span><ChevronDown size={14} /></>
            )}
          </button>
        )}

        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="paper-direct-link"
          >
            <span>Source</span>
            <ExternalLink size={13} />
          </a>
        )}
      </div>
    </div>
  )
}

export default ResearchPaperCard

