"""
Output Formatter & Scientific Post-Processor
=============================================
Normalizes engine outputs to the v2 `SimulationOutput` contract:
  1. Executes `ScientificValidator` BEFORE finalizing status and 3D scene generation.
  2. Never fabricates arbitrary confidence scores (`confidence_score=None`).
  3. Never computes Student-t 95% confidence intervals over deterministic ODE/analytical curves.
     Computes honest deterministic descriptive statistics (min, max, mean, std, range, RMS, derivative).
  4. Generates registry-synchronized 3D scenes and verifies them with `validate_scene_specification`.
  5. Preserves honest statuses: `success`, `partial`, `validation_failed`, `unsupported`, `failed`, `illustrative`.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

import numpy as np

from .experiment_registry import get_experiment_entry
from .schema import PlotData, SeriesData, SimulationOutput
from .validation.scientific_validator import validate_simulation_result
from .visualization.scene_generator import (
    generate_scene_specification,
    resolve_visualization_template,
)
from .visualization.scene_schema import SceneSpecification

try:
    from backend.visualization.scene_validator import validate_scene_specification
except Exception:
    validate_scene_specification = None


_DETERMINISTIC_ENGINES = {
    "chem_sim",
    "bio_sim",
    "physics_sim",
    "electronics_sim",
    "civil_sim",
    "mech_sim",
    "cs_sim",
    "deterministic_engine",
}


def _generation_provenance(engine_used: str, status: str = "success", generation_method: str = "") -> str:
    """Honest data-provenance label derived from the engine/method that actually ran."""
    engine = str(engine_used or "").strip().lower()
    method = str(generation_method or "").strip().lower()
    state = str(status or "").strip().lower()

    if state in ("unsupported", "failed") or "fallback" in engine or "error" in engine:
        return "Unsupported or failed simulation — no fabricated numerical data generated"
    if state == "illustrative" or method in ("parametric_model", "parametric_illustrative"):
        return "Illustrative parametric model — deterministic surrogate, not empirical dataset training"
    if state == "validation_failed":
        return "Solver output failed scientific validation checks — inspect validation report"
    if method == "python_backup":
        return "Generated via sandboxed LLM Python code execution — review recommended"
    if method == "equation_model":
        return "Generated via AST-checked LLM equation model — review recommended"
    if method == "deterministic_engine" or engine in _DETERMINISTIC_ENGINES:
        return "Computed via deterministic domain physics/math/algorithm solver"
    if "llm" in engine or "dynamic" in engine:
        return "Generated via LLM code synthesis — review recommended"
    return f"Unverified provenance (engine '{engine_used}') — review recommended"


def _enrich_scientific_analysis(
    numerical_results: dict,
    plots: List[PlotData],
    observations: List[str],
    simulation_log: List[str],
    procedure: dict,
    engine_used: str,
    status: str,
    generation_method: str,
    validation_dict: Dict[str, Any],
) -> tuple:
    """
    Compute honest deterministic descriptive statistics (min, max, mean, median, std,
    range, RMS, and derivative sensitivity) on existing simulated arrays.
    NEVER fabricates Student-t 95% confidence intervals on deterministic trajectories.
    """
    enriched_num = copy.deepcopy(numerical_results) if isinstance(numerical_results, dict) else {}
    enriched_plots = list(plots)
    enriched_obs = list(observations)
    enriched_log = list(simulation_log)

    domain = str(procedure.get("domain", "general"))
    params = procedure.get("parameters", {})
    total_points = sum(len(p.y) for p in enriched_plots)

    # For unsupported/failed runs, do not fabricate statistics or extra plots
    if status in ("unsupported", "failed"):
        provenance = _generation_provenance(engine_used, status, generation_method)
        enriched_num["model_validation"] = {
            "domain": domain,
            "engine": engine_used,
            "status": status,
            "data_provenance": provenance,
            "validation": {
                "status": validation_dict.get("status", status),
                "passed": False,
                "checks_passed": validation_dict.get("checks_passed", 0),
                "checks_total": validation_dict.get("checks_total", 0),
                "warnings": list(validation_dict.get("warnings") or []),
                "errors": list(validation_dict.get("errors") or []),
            },
        }
        enriched_log.append(f"[L5_provenance] {provenance}")
        return enriched_num, enriched_plots, enriched_obs, enriched_log

    # Locate primary numeric plot series for deterministic descriptive stats
    numeric_plots = []
    for p in enriched_plots:
        try:
            xs = [float(v) for v in p.x]
            ys = [float(v) for v in p.y]
            if len(ys) >= 4 and len(xs) == len(ys):
                xa = np.asarray(xs, dtype=float)
                ya = np.asarray(ys, dtype=float)
                if np.all(np.isfinite(xa)) and np.all(np.isfinite(ya)):
                    numeric_plots.append((p, xa, ya))
        except (ValueError, TypeError):
            continue

    if numeric_plots:
        primary_plot, x_arr, y_arr = numeric_plots[0]
        mean_val = float(np.mean(y_arr))
        std_val = float(np.std(y_arr, ddof=0))
        median_val = float(np.median(y_arr))
        min_val = float(np.min(y_arr))
        max_val = float(np.max(y_arr))
        range_val = float(max_val - min_val)
        rms_val = float(np.sqrt(np.mean(y_arr ** 2)))

        enriched_num.setdefault("statistical_summary", {
            "sample_count": int(len(y_arr)),
            "mean": round(mean_val, 6),
            "std_dev": round(std_val, 6),
            "median": round(median_val, 6),
            "min": round(min_val, 6),
            "max": round(max_val, 6),
            "range": round(range_val, 6),
            "rms_magnitude": round(rms_val, 6),
            "note": "Deterministic trajectory descriptive statistics (not experimental sample confidence intervals).",
        })

        # First-derivative sensitivity plot when x is strictly monotonic & plot count < 3
        if np.ptp(x_arr) > 1e-12 and np.ptp(y_arr) > 1e-12 and len(y_arr) >= 10:
            diffs = np.diff(x_arr)
            if np.all(diffs > 0) or np.all(diffs < 0):
                dy_dx = np.gradient(y_arr, x_arr)
                if np.all(np.isfinite(dy_dx)):
                    enriched_num.setdefault("signal_dynamics", {
                        "peak_rate_of_change": round(float(np.max(np.abs(dy_dx))), 6),
                        "rms_magnitude": round(rms_val, 6),
                        "dynamic_span": round(range_val, 6),
                    })
                    if len(enriched_plots) < 3:
                        enriched_plots.append(PlotData(
                            plot_type="line",
                            title=f"Rate of Change: d({primary_plot.y_label})/d({primary_plot.x_label})",
                            x_label=primary_plot.x_label,
                            y_label="dY/dX",
                            x=x_arr.tolist(),
                            y=dy_dx.tolist(),
                            series_name="Derivative Sensitivity",
                        ))

        desc_line = (
            f"Deterministic trajectory summary (n={len(y_arr)}): "
            f"min={min_val:.4g}, max={max_val:.4g}, mean={mean_val:.4g}, RMS={rms_val:.4g}"
        )
        if desc_line not in enriched_obs:
            enriched_obs.append(desc_line)
    else:
        enriched_num.setdefault("statistical_summary", {
            "metric_groups": len(enriched_num),
            "plot_count": len(enriched_plots),
            "data_points": total_points,
            "note": "Discrete / categorical simulation output summary.",
        })

    provenance = _generation_provenance(engine_used, status, generation_method)
    model_validation = enriched_num.get("model_validation")
    if not isinstance(model_validation, dict):
        model_validation = {}
        enriched_num["model_validation"] = model_validation

    model_validation.update({
        "domain": domain,
        "engine": engine_used,
        "status": status,
        "generation_method": generation_method or None,
        "data_provenance": provenance,
        "parameters_evaluated": len(params),
        "plots_generated": len(enriched_plots),
        "total_simulated_points": int(total_points),
        "validation": {
            "status": validation_dict.get("status", status),
            "passed": bool(validation_dict.get("passed", False)),
            "checks_passed": validation_dict.get("checks_passed", 0),
            "checks_total": validation_dict.get("checks_total", 0),
            "warnings": list(validation_dict.get("warnings") or []),
            "errors": list(validation_dict.get("errors") or []),
        },
    })

    if len(enriched_obs) < 4:
        enriched_obs.append(
            f"{provenance} — engine '{engine_used}', domain '{domain}', {total_points} simulated points"
        )
    if len(enriched_obs) < 4:
        enriched_obs.append(
            f"ScientificValidator: {validation_dict.get('checks_passed', 0)}/{validation_dict.get('checks_total', 0)} checks passed ({validation_dict.get('status')})."
        )

    enriched_log.extend([
        f"[L4_analysis] Computed deterministic descriptive summary across {total_points} simulated points",
        f"[L4_analysis] Normalized {len(enriched_num)} metric groups and {len(enriched_plots)} analytical plots",
        f"[L5_validation] ScientificValidator status={validation_dict.get('status')} "
        f"({validation_dict.get('checks_passed', 0)}/{validation_dict.get('checks_total', 0)} checks passed)",
        f"[L5_provenance] {provenance}",
        f"[L7_output] Assembled validated v2 SimulationOutput contract for domain '{domain}'",
    ])
    for w in (validation_dict.get("warnings") or [])[:5]:
        enriched_log.append(f"[L5_validation] WARNING: {w}")
    for err in (validation_dict.get("errors") or [])[:5]:
        enriched_log.append(f"[L5_validation] ERROR: {err}")

    return enriched_num, enriched_plots, enriched_obs, enriched_log


def format_output(raw: dict, procedure: dict) -> SimulationOutput:
    """
    Validate raw engine output via `ScientificValidator`, generate and validate a
    synchronized 3D scene specification, and wrap into the v2 `SimulationOutput` schema.
    """
    plots: List[PlotData] = []
    for p in raw.get("plot_data", []) or []:
        try:
            raw_x = p.get("x", [])
            try:
                x_vals = [float(v) for v in raw_x]
            except (ValueError, TypeError):
                x_vals = list(raw_x)

            raw_y = p.get("y", [])
            try:
                y_vals = [float(v) for v in raw_y]
            except (ValueError, TypeError):
                y_vals = list(raw_y)

            extra_series = None
            raw_extra = p.get("extra_series") or []
            if raw_extra:
                extra_series = []
                for s in raw_extra:
                    try:
                        sy = [float(v) for v in s.get("y", [])]
                    except (ValueError, TypeError):
                        sy = list(s.get("y", []))
                    extra_series.append(SeriesData(
                        y=sy,
                        name=s.get("name", "Series"),
                        color=s.get("color"),
                    ))

            plots.append(PlotData(
                plot_type=p.get("plot_type", "line"),
                title=p.get("title", "Simulation Result"),
                x_label=p.get("x_label", "X"),
                y_label=p.get("y_label", "Y"),
                x=x_vals,
                y=y_vals,
                series_name=p.get("series_name"),
                extra_series=extra_series,
            ))
        except Exception as exc:
            print(f"⚠️  Skipping invalid plot data: {exc}")
            continue

    engine_used = str(raw.get("engine_used", "unknown"))
    raw_num = raw.get("numerical_results") if isinstance(raw.get("numerical_results"), dict) else {}
    raw_obs = list(raw.get("observations") or [])
    raw_log = list(raw.get("simulation_log") or [])
    generation_method = str(raw.get("generation_method") or raw.get("simulation_type") or "")

    # 1. Resolve canonical experiment_id & expected visualization template
    exp_id_resolved, expected_template = resolve_visualization_template(procedure, raw)
    exp_id = str(raw.get("experiment_id") or exp_id_resolved or procedure.get("experiment_type") or "").strip() or None
    if exp_id:
        entry = get_experiment_entry(exp_id)
        if entry:
            expected_template = entry.visualization_template

    # 2. Run ScientificValidator BEFORE finalizing status & 3D scene
    validation_summary, validated_status = validate_simulation_result(raw, procedure)
    checks_total = len(validation_summary.checks)
    checks_passed = sum(1 for c in validation_summary.checks if c.passed)
    validation_dict = validation_summary.model_dump()
    validation_dict.update({
        "status": validated_status,
        "passed": bool(validation_summary.overall_valid),
        "checks_passed": checks_passed,
        "checks_total": checks_total,
    })

    raw_status = str(raw.get("simulation_status") or raw.get("status") or "").lower().strip()
    if raw_status in ("unsupported", "failed"):
        final_status = raw_status
    elif validated_status == "validation_failed":
        final_status = "validation_failed"
    elif raw_status == "illustrative" or str(raw.get("simulation_type", "")).lower() in ("parametric_model", "parametric_illustrative"):
        final_status = "illustrative"
    elif raw_status == "partial" or validated_status == "partial":
        final_status = "partial"
    else:
        final_status = validated_status

    sim_type = str(raw.get("simulation_type") or (
        "unsupported" if final_status in ("unsupported", "failed")
        else "parametric_illustrative" if final_status == "illustrative"
        else "deterministic"
    ))

    # Collect solver metadata, assumptions, limitations, uncertainties, warnings
    solver_info = raw.get("solver") if isinstance(raw.get("solver"), dict) else {
        "name": exp_id or engine_used,
        "engine": engine_used,
        "method": generation_method or "deterministic",
        "equations": [],
    }
    assumptions = list(raw.get("assumptions") or [])
    limitations = list(raw.get("limitations") or [])
    uncertainties = list(raw.get("uncertainties") or [])
    warnings = list(raw.get("warnings") or [])
    for w in validation_summary.warnings:
        if w not in warnings:
            warnings.append(w)
    for err in validation_summary.errors:
        if err not in warnings:
            warnings.append(f"Validation error: {err}")

    # 3. Generate & validate synchronized 3D scene specification
    vis_spec = raw.get("visualization_spec")
    scene_valid = False
    scene_issues: List[str] = []
    scene_reason = ""

    if final_status in ("unsupported", "failed"):
        vis_spec = None
        scene_reason = f"3D visualization disabled because simulation status is '{final_status}'."
    else:
        if not vis_spec:
            try:
                vis_spec = generate_scene_specification(
                    procedure,
                    raw_num,
                    raw.get("plot_data", []),
                    simulation_status=final_status,
                )
            except Exception as exc:
                scene_issues.append(f"3D scene generation failed: {exc}")
                vis_spec = None

        if vis_spec and validate_scene_specification is not None:
            try:
                spec_obj = SceneSpecification(**vis_spec)
                scene_valid, scene_issues = validate_scene_specification(
                    spec_obj,
                    expected_experiment_id=exp_id,
                    expected_template=expected_template,
                )
                if not scene_valid:
                    warnings.append(
                        f"3D scene rejected by validator ({'; '.join(scene_issues[:2])}); omitting mismatched scene."
                    )
                    scene_reason = "Scene rejected due to template/integrity mismatch."
                    vis_spec = None
                else:
                    vis_spec = spec_obj.model_dump()
            except Exception as exc:
                scene_valid = False
                scene_issues.append(str(exc))
                warnings.append(f"3D scene validation error: {exc}")
                vis_spec = None
        elif vis_spec:
            scene_valid = True

    visualization_contract = {
        "template": vis_spec.get("scene_template") if isinstance(vis_spec, dict) else expected_template,
        "experiment_id": vis_spec.get("experiment_id") if isinstance(vis_spec, dict) else exp_id,
        "is_simulation_backed": bool(vis_spec.get("is_simulation_backed", False)) if isinstance(vis_spec, dict) else False,
        "scene_valid": scene_valid,
        "scene_issues": scene_issues,
        "reason": scene_reason or ("Validated simulation-backed 3D scene" if scene_valid else "No 3D scene available"),
    }

    # 4. Deterministic post-processing (NO Student-t CI fabrication!)
    enriched_num, enriched_plots, enriched_obs, enriched_log = _enrich_scientific_analysis(
        raw_num,
        plots,
        raw_obs,
        raw_log,
        procedure,
        engine_used,
        status=final_status,
        generation_method=generation_method,
        validation_dict=validation_dict,
    )

    return SimulationOutput(
        status=final_status,
        simulation_status=final_status,
        simulation_type=sim_type,
        engine_used=engine_used,
        domain=str(procedure.get("domain", "general")),
        experiment_id=exp_id,
        hypothesis=str(procedure.get("hypothesis", "")),
        solver=solver_info,
        numerical_results=enriched_num,
        plot_data=enriched_plots,
        observations=enriched_obs,
        validation=validation_dict,
        visualization=visualization_contract,
        assumptions=assumptions,
        limitations=limitations,
        uncertainties=uncertainties,
        warnings=warnings,
        confidence_score=None,
        simulation_log=enriched_log,
        visualization_type=raw.get("visualization_type", "graph"),
        visual_data=raw.get("visual_data", None),
        visualization_spec=vis_spec,
    )
