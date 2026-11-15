"""
Output Formatter & Quantitative Statistical Post-Processor
Normalizes engine outputs to SimulationOutput schema, performs deterministic
SciPy/NumPy statistical analysis across every domain, and generates the
validated 3D scene specification.
"""

import copy
from typing import Optional
import numpy as np
from scipy import stats as scipy_stats
from .schema import SimulationOutput, PlotData, SeriesData
from .visualization.scene_generator import generate_scene_specification


#: Engines that compute results directly from fixed physical/chemical/engineering models.
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
    """
    Honest data-provenance label for the numbers being reported.

    Derived from the engine/method that actually produced the data, so the output
    never claims an audit or validation step that did not take place.
    """
    engine = str(engine_used or "").strip().lower()
    method = str(generation_method or "").strip().lower()
    state = str(status or "").strip().lower()

    if state in ("fallback", "failed") or "fallback" in engine or "error" in engine or "synthetic" in engine:
        return "Synthetic illustrative data - NOT experimentally validated"
    if method == "python_backup":
        return "Generated via LLM Python code execution - review recommended"
    if method == "equation_model":
        return "Generated via LLM equation model - review recommended"
    if method == "deterministic_engine" or engine in _DETERMINISTIC_ENGINES:
        return "Generated via deterministic domain engine"
    if "llm" in engine or "dynamic" in engine:
        return "Generated via LLM code synthesis - review recommended"
    return f"Unverified provenance (engine '{engine_used}') - review recommended"


def _enrich_scientific_analysis(
    numerical_results: dict,
    plots: list,
    observations: list,
    simulation_log: list,
    procedure: dict,
    engine_used: str,
    status: str = "success",
    generation_method: str = "",
    validation: Optional[dict] = None,
) -> tuple:
    """
    Compute genuine descriptive statistics, 95% confidence intervals, linear
    regression significance, and derivative sensitivity curves directly from the
    deterministic engine's simulated plot vectors.
    Never invents synthetic data; only analyzes existing simulated arrays.
    """
    enriched_num = copy.deepcopy(numerical_results) if isinstance(numerical_results, dict) else {}
    enriched_plots = list(plots)
    enriched_obs = list(observations)
    enriched_log = list(simulation_log)

    domain = str(procedure.get("domain", "general"))
    params = procedure.get("parameters", {})

    # Locate primary numeric series for statistical analysis
    numeric_plots = []
    for p in enriched_plots:
        try:
            xs = [float(v) for v in p.x]
            ys = [float(v) for v in p.y]
            if len(ys) >= 4 and len(xs) == len(ys):
                numeric_plots.append((p, np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)))
        except (ValueError, TypeError):
            continue

    total_points = sum(len(p.y) for p in enriched_plots)

    if numeric_plots:
        primary_plot, x_arr, y_arr = numeric_plots[0]
        mean_val = float(np.mean(y_arr))
        std_val = float(np.std(y_arr, ddof=1)) if len(y_arr) > 1 else 0.0
        median_val = float(np.median(y_arr))
        q25, q75 = np.percentile(y_arr, [25, 75])
        iqr_val = float(q75 - q25)
        sem_val = std_val / np.sqrt(len(y_arr)) if len(y_arr) > 1 else 0.0

        if sem_val > 0 and len(y_arr) > 2:
            ci_low, ci_high = scipy_stats.t.interval(0.95, df=len(y_arr) - 1, loc=mean_val, scale=sem_val)
        else:
            ci_low, ci_high = mean_val, mean_val

        enriched_num.setdefault("statistical_summary", {
            "sample_count": int(len(y_arr)),
            "mean": round(mean_val, 5),
            "std_dev": round(std_val, 5),
            "median": round(median_val, 5),
            "iqr": round(iqr_val, 5),
            "min": round(float(np.min(y_arr)), 5),
            "max": round(float(np.max(y_arr)), 5),
            "ci_95_lower": round(float(ci_low), 5),
            "ci_95_upper": round(float(ci_high), 5),
        })

        # Linear trend & correlation test
        if np.ptp(x_arr) > 1e-12 and np.ptp(y_arr) > 1e-12:
            reg = scipy_stats.linregress(x_arr, y_arr)
            enriched_num.setdefault("regression_analysis", {
                "slope": round(float(reg.slope), 6),
                "intercept": round(float(reg.intercept), 5),
                "r_squared": round(float(reg.rvalue ** 2), 5),
                "p_value": float(f"{reg.pvalue:.4e}"),
                "pearson_r": round(float(reg.rvalue), 5),
            })

            # Add first-derivative sensitivity plot if plot count < 4 and domain hasn't already provided 4
            if len(enriched_plots) < 4 and len(y_arr) >= 10:
                dy_dx = np.gradient(y_arr, x_arr)
                # Guard against duplicate x spikes causing inf
                finite_mask = np.isfinite(dy_dx)
                if np.any(finite_mask):
                    dy_dx = np.where(finite_mask, dy_dx, 0.0)
                    enriched_plots.append(PlotData(
                        plot_type="line",
                        title=f"Rate of Change Analysis: d({primary_plot.y_label})/d({primary_plot.x_label})",
                        x_label=primary_plot.x_label,
                        y_label=f"dY/dX",
                        x=x_arr.tolist(),
                        y=dy_dx.tolist(),
                        series_name="Derivative Sensitivity",
                    ))
                    enriched_num.setdefault("signal_dynamics", {
                        "peak_rate_of_change": round(float(np.max(np.abs(dy_dx))), 5),
                        "rms_magnitude": round(float(np.sqrt(np.mean(y_arr ** 2))), 5),
                        "dynamic_span": round(float(np.ptp(y_arr)), 5),
                    })

        # Add binned frequency / value distribution if still < 4 plots
        if len(enriched_plots) < 4 and len(y_arr) >= 12 and np.ptp(y_arr) > 1e-12:
            counts, edges = np.histogram(y_arr, bins=min(12, max(6, len(y_arr) // 15)))
            centers = 0.5 * (edges[:-1] + edges[1:])
            enriched_plots.append(PlotData(
                plot_type="bar",
                title=f"Response Distribution ({primary_plot.y_label})",
                x_label=primary_plot.y_label,
                y_label="Sample Frequency",
                x=[round(float(c), 4) for c in centers],
                y=[int(c) for c in counts],
                series_name="Frequency Distribution",
            ))

        stat_line = (
            f"Statistical analysis (n={len(y_arr)}): mean = {mean_val:.4f} ± {std_val:.4f} "
            f"(95% CI: [{ci_low:.4f}, {ci_high:.4f}])"
        )
        if stat_line not in enriched_obs:
            enriched_obs.append(stat_line)
    else:
        enriched_num.setdefault("statistical_summary", {
            "metric_groups": len(enriched_num),
            "plot_count": len(enriched_plots),
            "data_points": total_points,
        })

    provenance = _generation_provenance(engine_used, status, generation_method)

    model_validation = enriched_num.get("model_validation")
    if not isinstance(model_validation, dict):
        model_validation = {}
        enriched_num["model_validation"] = model_validation
    model_validation.update({
        "domain": domain,
        "engine": engine_used,
        "generation_method": generation_method or None,
        "data_provenance": provenance,
        "parameters_evaluated": len(params),
        "plots_generated": len(enriched_plots),
        "total_simulated_points": int(total_points),
    })
    if isinstance(validation, dict) and validation:
        model_validation["validation"] = {
            "valid": bool(validation.get("valid")),
            "checks_passed": validation.get("checks_passed", 0),
            "checks_total": validation.get("checks_total", 0),
            "warnings": list(validation.get("warnings") or []),
        }

    # Record provenance honestly instead of asserting an audit that did not happen.
    if len(enriched_obs) < 4:
        enriched_obs.append(
            f"{provenance} — engine '{engine_used}', domain '{domain}', {total_points} simulated points"
        )
    if len(enriched_obs) < 4 and params:
        enriched_obs.append(
            "Simulation inputs used as supplied (not independently verified): "
            + ", ".join(f"{k}={v}" for k, v in list(params.items())[:4])
        )

    # Audit log enrichment (records what was computed, not what was validated)
    enriched_log.extend([
        f"[L4_analysis] Computed descriptive statistics & 95% confidence bounds across {total_points} points",
        f"[L4_analysis] Output normalized: {len(enriched_num)} metric groups, {len(enriched_plots)} analytical plots",
        f"[L5_provenance] {provenance}",
        "[L7_review] Assembled SimulationOutput + declarative 3D scene specification for downstream review",
    ])
    if isinstance(validation, dict):
        for warning in (validation.get("warnings") or [])[:3]:
            enriched_log.append(f"[L5_provenance] WARNING: {warning}")

    return enriched_num, enriched_plots, enriched_obs, enriched_log


def format_output(raw: dict, procedure: dict) -> SimulationOutput:
    """
    Takes raw engine output dict and wraps it into the
    typed SimulationOutput schema for downstream consumers.
    Also runs statistical post-processing and produces a validated 3D scene specification.
    """
    plots = []
    for p in raw.get("plot_data", []):
        try:
            # Support both numeric and string x labels
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

            # Parse extra series for multi-line plots
            extra_series = None
            raw_extra = p.get("extra_series", [])
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
        except Exception as e:
            print(f"⚠️  Skipping invalid plot data: {e}")
            continue

    engine_used = raw.get("engine_used", "unknown")
    raw_num = raw.get("numerical_results", {})
    raw_obs = raw.get("observations", [])
    raw_log = raw.get("simulation_log", [])
    status_value = raw.get("status", "success" if "error" not in raw else "fallback")
    generation_method = str(raw.get("generation_method") or "")
    raw_validation = raw.get("validation") if isinstance(raw.get("validation"), dict) else None

    # Generate or retain validated 3D scene specification BEFORE adding statistical plot cards
    vis_spec = raw.get("visualization_spec")
    if not vis_spec:
        try:
            vis_spec = generate_scene_specification(
                procedure,
                raw_num,
                raw.get("plot_data", [])
            )
        except Exception as e:
            print(f"⚠️  Failed to generate 3D scene specification: {e}")
            vis_spec = None

    # Enrich L4 statistical metrics & visualizations across all domains
    enriched_num, enriched_plots, enriched_obs, enriched_log = _enrich_scientific_analysis(
        raw_num, plots, raw_obs, raw_log, procedure, engine_used,
        status=status_value,
        generation_method=generation_method,
        validation=raw_validation,
    )

    return SimulationOutput(
        status=status_value,
        engine_used=engine_used,
        domain=procedure.get("domain", "general"),
        hypothesis=procedure.get("hypothesis", ""),
        numerical_results=enriched_num,
        plot_data=enriched_plots,
        observations=enriched_obs,
        confidence_score=float(raw.get("confidence_score", 0.5)),
        simulation_log=enriched_log,
        visualization_type=raw.get("visualization_type", "graph"),
        visual_data=raw.get("visual_data", None),
        visualization_spec=vis_spec,
    )
