"""
Unsupported / Fallback Handler (No Fabricated Scientific Data)
==============================================================
Replaces the legacy random sine-wave generator.

Non-negotiable scientific integrity rules:
  - NEVER fabricate random sinusoidal noise as scientific experimental data.
  - When no registered deterministic solver applies, return an explicit
    `status="unsupported"` (or `status="failed"` on solver error) with
    clear diagnostic reasons and guidance on supported experiments.
"""

from typing import Dict, Any, Optional


def build_unsupported_response(
    procedure: dict,
    reason: str = "",
    supported_examples: Optional[list] = None,
) -> Dict[str, Any]:
    """Return an honest unsupported-experiment result with zero fabricated data."""
    domain = str(procedure.get("domain", "general") or "general")
    exp_type = str(procedure.get("experiment_type") or "unspecified")
    topic = str(procedure.get("topic") or procedure.get("hypothesis") or "Unknown experiment")
    detail = reason or f"No registered deterministic scientific solver for domain='{domain}', experiment_type='{exp_type}'."

    obs = [
        f"Unsupported experiment: {detail}",
        "No fabricated or synthetic fallback curve was generated.",
    ]
    if supported_examples:
        obs.append("Supported experiments in this domain: " + ", ".join(supported_examples[:8]))

    return {
        "status": "unsupported",
        "simulation_status": "unsupported",
        "simulation_type": "unsupported",
        "engine_used": "none",
        "experiment_id": exp_type,
        "domain": domain,
        "solver": {
            "name": "none",
            "version": "2.0",
            "method": "No registered deterministic solver",
            "equations": [],
        },
        "numerical_results": {},
        "plot_data": [],
        "visual_data": None,
        "visualization_type": "none",
        "observations": obs,
        "assumptions": [],
        "limitations": [detail],
        "warnings": [detail],
        "error": detail,
        "simulation_log": [
            f"[unsupported] Topic='{topic[:120]}', domain='{domain}', experiment_type='{exp_type}'",
            f"[unsupported] Reason: {detail}",
        ],
    }


def build_failed_response(procedure: dict, error_context: str) -> Dict[str, Any]:
    """Return an honest failed-simulation result when a solver raises or fails validation."""
    domain = str(procedure.get("domain", "general") or "general")
    exp_type = str(procedure.get("experiment_type") or "unspecified")
    detail = str(error_context or "Numerical solver failed.")

    return {
        "status": "failed",
        "simulation_status": "failed",
        "simulation_type": "unsupported",
        "engine_used": "failed_solver",
        "experiment_id": exp_type,
        "domain": domain,
        "solver": {
            "name": exp_type,
            "version": "2.0",
            "method": "Solver execution failed",
            "equations": [],
        },
        "numerical_results": {},
        "plot_data": [],
        "visual_data": None,
        "visualization_type": "none",
        "observations": [
            f"Simulation failed: {detail}",
            "No fabricated fallback data was substituted.",
        ],
        "assumptions": [],
        "limitations": [detail],
        "warnings": [detail],
        "error": detail,
        "simulation_log": [f"[failed] {detail}"],
    }


def get_minimal_fallback(procedure: dict, error_context: str = "") -> Dict[str, Any]:
    """
    Legacy compatibility symbol.
    Previously generated random `sin(x) + normal(0, 0.1)` noise; now strictly returns
    an honest `unsupported` status with zero fabricated measurements.
    """
    return build_unsupported_response(
        procedure,
        reason=error_context or "Requested experiment has no verified deterministic solver.",
    )


def run(procedure: dict, error_context: str = "") -> Dict[str, Any]:
    """
    Main entry point when routing cannot execute a registered deterministic solver.
    Distinguishes solver failure from unsupported experiment without fabricating data.
    """
    err = str(error_context or "").strip()
    if err and not err.lower().startswith("unknown") and "unsupported" not in err.lower():
        return build_failed_response(procedure, err)
    return build_unsupported_response(procedure, reason=err)
