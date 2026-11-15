import { Sparkles, ArrowRight, CheckCircle2, Cpu } from 'lucide-react'

function RefinementPanel({ refinement }) {
  if (!refinement) return null

  const tf = refinement.token_filtering
  const extractedVars = refinement.extracted_variables || []
  const constants = refinement.physical_constants || []

  return (
    <div className="refinement-audit-panel">
      <div className="refinement-header">
        <div className="refinement-title">
          <Sparkles size={16} color="var(--accent-ai)" />
          <span>L1 Prompt Refinement &amp; Semantic Grounding</span>
        </div>
        {refinement.refiner_source && (
          <span className="refiner-engine-badge">
            <Cpu size={12} />
            {refinement.refiner_source}
          </span>
        )}
      </div>

      <div className="refinement-comparison">
        <div className="prompt-box original">
          <span className="box-tag">Original Input</span>
          <p>{refinement.original_prompt || '—'}</p>
        </div>
        <div className="arrow-divider">
          <ArrowRight size={18} color="var(--accent-ai)" />
        </div>
        <div className="prompt-box refined">
          <span className="box-tag">Refined Prompt</span>
          <p>{refinement.refined_prompt || '—'}</p>
        </div>
      </div>

      <div className="refinement-metadata-grid">
        {tf && (
          <div className="meta-card">
            <span className="meta-card-label">Stop-Word &amp; Token Optimization</span>
            <div className="token-stats">
              <span className="token-count">{tf.raw_token_count}</span>
              <span className="token-arrow">→</span>
              <span className="token-count-filtered">{tf.filtered_token_count}</span>
              <span className="token-reduction-badge">-{tf.reduction_pct}% tokens</span>
            </div>
          </div>
        )}

        {extractedVars.length > 0 && (
          <div className="meta-card">
            <span className="meta-card-label">Extracted Variables</span>
            <div className="tags-flex">
              {extractedVars.map((v, i) => (
                <span key={i} className="variable-tag">{v}</span>
              ))}
            </div>
          </div>
        )}

        {constants.length > 0 && (
          <div className="meta-card">
            <span className="meta-card-label">Identified Physical Constants</span>
            <div className="tags-flex">
              {constants.map((c, i) => (
                <span key={i} className="constant-tag">{c}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default RefinementPanel

