import React from 'react'

export default function VisionAnalysisPanel({ visualSpec, reference, instructions = [] }) {
  if (!visualSpec && (!instructions || instructions.length === 0)) {
    return (
      <div className="p-4 rounded-xl bg-surface-container-low border border-surface-container-high text-center">
        <span className="material-symbols-outlined text-[24px] text-outline mb-1">visibility</span>
        <h4 className="text-[13px] font-bold text-on-surface">Visual Structure Analysis</h4>
        <p className="text-[11px] text-on-surface-variant mt-1">
          No vision-guided diagram analysis generated for this experiment yet.
        </p>
      </div>
    )
  }

  const objects = visualSpec?.objects || []

  return (
    <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
      <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[19px] text-secondary">visibility</span>
          <h3 className="font-headline-sm text-sm font-bold text-on-surface">
            Qwen3-VL Visual Topology &amp; Diagram Guidance
          </h3>
        </div>
        <span className="text-[11px] text-outline font-mono">
          {objects.length} 3D PRIMITIVE(S) EXTRACTED
        </span>
      </div>

      {reference && (
        <div className="p-3 rounded-xl bg-surface-container-low border border-surface-container-high/60 flex items-center justify-between text-[12px]">
          <div className="flex items-center gap-2 truncate">
            <span className="material-symbols-outlined text-[17px] text-primary">image</span>
            <span className="font-semibold text-on-surface truncate">
              {reference.source_name || reference.title || 'Open Scientific Repository'}
            </span>
          </div>
          {reference.domain && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-secondary font-bold uppercase">
              {reference.domain}
            </span>
          )}
        </div>
      )}

      {/* Extracted 3D Objects Matrix */}
      {objects.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[11px] uppercase font-bold text-outline font-mono">
            Allowlisted Scene Geometries (SceneValidator Confirmed)
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {objects.map((obj, i) => (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high/60 flex flex-col gap-1 text-[11px]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-on-surface capitalize font-mono">
                    {obj.name || obj.type}
                  </span>
                  <span className="text-[9px] font-mono text-outline uppercase">{obj.type}</span>
                </div>
                {obj.position && (
                  <span className="text-[10px] text-outline font-mono">
                    Pos: [{obj.position.map((v) => Number(v).toFixed(1)).join(', ')}]
                  </span>
                )}
                {obj.color && (
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full border border-black/10"
                      style={{ backgroundColor: obj.color }}
                    />
                    <span className="text-[10px] font-mono text-outline">{obj.color}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Visual Reconstruction Instructions */}
      {instructions && instructions.length > 0 && (
        <div className="p-3 rounded-xl bg-surface-container-low border border-surface-container-high/60 flex flex-col gap-1.5">
          <span className="text-[10px] uppercase font-bold text-outline font-mono">
            Spatial Apparatus Grounding Directives
          </span>
          <div className="flex flex-col gap-1 text-[11px] text-on-surface font-mono">
            {instructions.map((inst, i) => (
              <div key={i} className="flex items-baseline gap-2">
                <span className="text-secondary font-bold">•</span>
                <span>{inst}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

