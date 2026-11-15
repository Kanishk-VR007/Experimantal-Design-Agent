import { BookOpen, Database } from 'lucide-react'

function LiteratureSettings({ maxPapers, onChangeMaxPapers, useMockData, onToggleMockData, disabled }) {
  return (
    <div className="literature-settings">
      <div className="lit-setting-row">
        <div className="lit-label-group">
          <BookOpen size={15} color="var(--accent-secondary)" />
          <span className="lit-label">Literature Search Depth</span>
        </div>
        <div className="lit-input-group">
          <input
            type="range"
            min="1"
            max="10"
            value={maxPapers}
            onChange={(e) => onChangeMaxPapers(parseInt(e.target.value, 10))}
            disabled={disabled}
            className="papers-slider"
          />
          <span className="papers-count-badge">{maxPapers} papers</span>
        </div>
      </div>

      <div className="lit-setting-row">
        <label className="checkbox-toggle-container">
          <input
            type="checkbox"
            checked={useMockData}
            onChange={(e) => onToggleMockData(e.target.checked)}
            disabled={disabled}
          />
          <div className="checkbox-content">
            <span className="checkbox-title">Use Offline Simulation &amp; Mock Corpus</span>
            <span className="checkbox-desc">High-speed verification mode bypasses live arXiv / Semantic Scholar network latency</span>
          </div>
        </label>
      </div>
    </div>
  )
}

export default LiteratureSettings

