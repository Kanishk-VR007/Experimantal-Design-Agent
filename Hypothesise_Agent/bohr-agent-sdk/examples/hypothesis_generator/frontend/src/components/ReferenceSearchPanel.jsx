import React from 'react'

export default function ReferenceSearchPanel({ papers = [] }) {
  if (!papers || papers.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-surface-container-low border border-surface-container-high text-center">
        <span className="material-symbols-outlined text-[24px] text-outline mb-1">menu_book</span>
        <h4 className="text-[13px] font-bold text-on-surface">Scientific Reference Repository</h4>
        <p className="text-[11px] text-on-surface-variant mt-1">
          No external academic references retrieved for this experiment topic yet.
        </p>
      </div>
    )
  }

  return (
    <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
      <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[19px] text-primary">menu_book</span>
          <h3 className="font-headline-sm text-sm font-bold text-on-surface">
            Grounding Academic Literature (arXiv &amp; Semantic Scholar)
          </h3>
        </div>
        <span className="text-[11px] text-outline font-mono">
          {papers.length} CITATION(S) RETRIEVED
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {papers.map((p, idx) => (
          <div
            key={idx}
            className="p-4 rounded-xl bg-surface-container-low border border-surface-container-high/70 flex flex-col gap-2 hover:border-primary/40 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <h4 className="text-[13px] font-bold text-on-surface leading-snug">
                {p.title}
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-primary shrink-0 font-semibold">
                {p.source || 'Open Access'}
              </span>
            </div>

            {p.authors && p.authors.length > 0 && (
              <span className="text-[11px] text-on-surface-variant font-medium">
                Authors: {Array.isArray(p.authors) ? p.authors.join(', ') : p.authors}
              </span>
            )}

            {p.abstract && (
              <p className="text-[12px] text-outline line-clamp-3 leading-relaxed">
                {p.abstract}
              </p>
            )}

            <div className="flex items-center justify-between pt-1 text-[11px] font-mono">
              <span className="text-secondary font-semibold">
                {p.citations != null ? `${p.citations} citations` : 'Peer-Reviewed'}
              </span>
              {p.url && (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Read Publication</span>
                  <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

