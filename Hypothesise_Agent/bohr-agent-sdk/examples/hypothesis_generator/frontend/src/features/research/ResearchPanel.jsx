import { useState } from 'react'
import { BookOpen, Search, FileText } from 'lucide-react'
import ResearchPaperCard from './ResearchPaperCard'

function ResearchPanel({ papers = [] }) {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredPapers = papers.filter((p) => {
    const q = searchTerm.toLowerCase()
    return (
      p.title?.toLowerCase().includes(q) ||
      p.abstract?.toLowerCase().includes(q) ||
      (Array.isArray(p.authors) ? p.authors.join(' ').toLowerCase().includes(q) : false)
    )
  })

  return (
    <div className="research-panel-container">
      <div className="research-panel-header">
        <div className="title-group">
          <BookOpen size={20} color="var(--accent-secondary)" />
          <h3>Scientific Literature Corpus ({papers.length})</h3>
        </div>

        {papers.length > 0 && (
          <div className="search-box">
            <Search size={15} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Filter papers by keyword or author..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        )}
      </div>

      {papers.length === 0 ? (
        <div className="empty-papers-view">
          <FileText size={36} color="var(--text-muted)" />
          <h4>No Research Papers Grounded Yet</h4>
          <p>Generate an experiment design or search papers to populate peer-reviewed literature citations.</p>
        </div>
      ) : (
        <div className="papers-cards-grid">
          {filteredPapers.map((paper, idx) => (
            <ResearchPaperCard key={idx} paper={paper} />
          ))}
        </div>
      )}
    </div>
  )
}

export default ResearchPanel

