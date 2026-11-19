import React from 'react'

export default function ScientificValidationPanel({ validation, solverName = null }) {
  if (!validation) {
    return (
      <div className="p-4 rounded-xl bg-surface-container-low border border-surface-container-high text-center">
        <span className="material-symbols-outlined text-[24px] text-outline mb-1">fact_check</span>
        <h4 className="text-[13px] font-bold text-on-surface">Scientific Validation Status</h4>
        <p className="text-[11px] text-on-surface-variant mt-1">
          No automated scientific validation summary generated for this run yet.
        </p>
      </div>
    )
  }

  const {
    overall_valid = false,
    input_valid = false,
    dimensional_valid = false,
    physical_constraints_valid = false,
    equilibrium_residuals_valid = false,
    checks = [],
    checks_passed = 0,
    checks_total = 0,
    warnings = [],
    errors = [],
    governing_equations = [],
  } = validation

  const passRate = checks_total > 0 ? ((checks_passed / checks_total) * 100).toFixed(0) : null

  return (
    <div className="p-5 rounded-2xl bg-surface-container-lowest border border-surface-container-high shadow-sm flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-container-high pb-3">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              overall_valid ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}
          >
            <span className="material-symbols-outlined text-[19px]">
              {overall_valid ? 'verified' : 'warning'}
            </span>
          </div>
          <div>
            <h3 className="font-headline-sm text-sm font-bold text-on-surface">
              Multi-Physics Scientific Validation Suite
            </h3>
            <span className="text-[11px] text-on-surface-variant font-mono">
              Solver: {solverName || 'Deterministic SciPy/NumPy Engine'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold ${
              overall_valid
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                overall_valid ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'
              }`}
            />
            {overall_valid ? 'VERIFIED (PASS)' : 'FLAGGED (REVIEW)'}
          </span>

          {passRate !== null && (
            <span className="px-2.5 py-1 rounded-lg bg-surface-container-high text-on-surface font-mono text-[11px] font-bold">
              {checks_passed} / {checks_total} CHECKS ({passRate}%)
            </span>
          )}
        </div>
      </div>

      {/* Validation Checks Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {checks && checks.length > 0 ? (
          checks.map((chk, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-xl border flex items-start justify-between gap-2 text-[12px] ${
                chk.passed
                  ? 'bg-surface-container-low/50 border-surface-container-high text-on-surface'
                  : 'bg-red-50/50 border-red-200 text-red-900'
              }`}
            >
              <div className="flex items-start gap-2">
                <span
                  className={`material-symbols-outlined text-[17px] mt-0.5 ${
                    chk.passed ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {chk.passed ? 'check_circle' : 'cancel'}
                </span>
                <div className="flex flex-col">
                  <span className="font-semibold">{chk.name}</span>
                  {chk.detail && (
                    <span className="text-[11px] text-outline font-mono mt-0.5 leading-snug">
                      {chk.detail}
                    </span>
                  )}
                </div>
              </div>
              <span
                className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                  chk.passed ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                }`}
              >
                {chk.passed ? 'PASS' : 'FAIL'}
              </span>
            </div>
          ))
        ) : (
          <div className="col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { name: 'Input Range', passed: input_valid },
              { name: 'Dimensions', passed: dimensional_valid },
              { name: 'Constraints', passed: physical_constraints_valid },
              { name: 'Residuals', passed: equilibrium_residuals_valid },
            ].map((item, i) => (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-surface-container-low border border-surface-container-high flex flex-col gap-1 text-[11px]"
              >
                <span className="text-outline">{item.name}</span>
                <span
                  className={`font-mono font-bold ${
                    item.passed ? 'text-emerald-600' : 'text-amber-600'
                  }`}
                >
                  {item.passed ? 'VALID' : 'UNVERIFIED'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Governing Equations if provided */}
      {governing_equations && governing_equations.length > 0 && (
        <div className="p-3 rounded-xl bg-surface-container-low border border-surface-container-high/60 flex flex-col gap-1.5">
          <span className="text-[10px] uppercase font-bold text-outline tracking-wider font-mono">
            Governing Analytical Equations
          </span>
          <div className="flex flex-col gap-1 font-mono text-[11px] text-on-surface">
            {governing_equations.map((eq, i) => (
              <div key={i} className="flex items-baseline gap-2">
                <span className="text-primary font-bold">[{i + 1}]</span>
                <span>{eq}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings & Errors */}
      {warnings && warnings.length > 0 && (
        <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-amber-900 text-[11px] flex flex-col gap-1">
          <span className="font-bold uppercase tracking-wider font-mono text-[10px]">
            Engineering Warnings ({warnings.length})
          </span>
          {warnings.map((w, i) => (
            <div key={i}>• {w}</div>
          ))}
        </div>
      )}

      {errors && errors.length > 0 && (
        <div className="p-3 rounded-xl bg-red-50/70 border border-red-200 text-red-900 text-[11px] flex flex-col gap-1">
          <span className="font-bold uppercase tracking-wider font-mono text-[10px]">
            Validation Errors ({errors.length})
          </span>
          {errors.map((e, i) => (
            <div key={i}>• {e}</div>
          ))}
        </div>
      )}
    </div>
  )
}

