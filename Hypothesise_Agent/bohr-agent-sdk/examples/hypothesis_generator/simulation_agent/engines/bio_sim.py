"""
Biology Simulation Engine
==========================
Explicit deterministic solvers:
  - michaelis_menten: Exact steady-state Michaelis-Menten enzyme kinetics v = Vmax*[S]/(Km+[S])
    with competitive and non-competitive inhibition + Lineweaver-Burk transformation.
  - logistic_growth: Verhulst logistic population ODE & analytical verification.
  - exponential_growth: Malthusian exponential population growth N(t) = N0 * exp(r*t).
  - gene_expression: Coupled linear transcription-translation ODEs with steady-state verification.

Explicitly validates all inputs & units; never claims genomic/BLAST analysis unless available.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List
import numpy as np
from scipy.integrate import solve_ivp

from .llm_fallback import build_unsupported_response, build_failed_response


def _michaelis_menten(params: dict) -> Dict[str, Any]:
    """Exact Michaelis-Menten enzyme kinetics: v = Vmax * [S] / (Km + [S])."""
    Vmax = float(params.get("Vmax") or params.get("v_max") or params.get("V_max") or params.get("max_velocity") or 100.0)
    Km = float(params.get("Km") or params.get("K_m") or params.get("michaelis_constant") or 5.0)
    Ki = float(params.get("Ki") or params.get("K_i") or params.get("inhibition_constant") or 2.5)
    raw_I = params.get("inhibitor_conc") if params.get("inhibitor_conc") is not None else params.get("I", 0.0)
    I_val = float(raw_I[0] if isinstance(raw_I, list) and raw_I else raw_I)
    S_max = float(params.get("substrate_max") or params.get("substrate_max_mm") or max(60.0, 12.0 * Km))
    inh_type = str(params.get("inhibition_type", "non_competitive")).lower().strip()

    if Vmax <= 0 or Km <= 0 or Ki <= 0 or I_val < 0 or S_max <= 0:
        return build_failed_response(
            {"domain": "biology", "experiment_type": "michaelis_menten"},
            f"Michaelis-Menten requires Vmax>0, Km>0, Ki>0, [I]>=0, S_max>0 (got Vmax={Vmax}, Km={Km}, I={I_val}).",
        )

    # Include exact benchmark points: [S]=0, low [S]=0.1*Km, [S]=Km, high [S]=S_max
    S_range = np.linspace(0.0, S_max, 121)
    v_control = (Vmax * S_range) / (Km + S_range)

    if inh_type == "competitive":
        Km_app = Km * (1.0 + I_val / Ki)
        Vmax_app = Vmax
    else:
        Km_app = Km
        Vmax_app = Vmax / (1.0 + I_val / Ki)

    v_inhibited = (Vmax_app * S_range) / (Km_app + S_range)

    # Evaluate exact canonical substrate test points
    v_at_0 = 0.0
    v_at_low = (Vmax * (0.1 * Km)) / (Km + 0.1 * Km)
    v_at_Km = (Vmax * Km) / (Km + Km)  # Exact Vmax / 2
    v_at_high = (Vmax * (100.0 * Km)) / (Km + 100.0 * Km)

    # Lineweaver-Burk (positive [S] only)
    lb_inv_S = np.linspace(1.0 / S_max, 1.0 / max(0.2 * Km, 1e-3), 80)
    lb_S = 1.0 / lb_inv_S
    lb_inv_v = (Km + lb_S) / (Vmax * lb_S)

    numerical = {
        "enzyme_kinetics": {
            "Vmax_uninhibited": round(Vmax, 6),
            "Km_uM": round(Km, 6),
            "Ki_uM": round(Ki, 6),
            "inhibitor_conc_uM": round(I_val, 6),
            "inhibition_type": inh_type,
            "Vmax_app": round(Vmax_app, 6),
            "Km_app_uM": round(Km_app, 6),
            "velocity_at_zero_substrate": round(v_at_0, 6),
            "velocity_at_low_substrate": round(v_at_low, 6),
            "velocity_at_Km": round(v_at_Km, 6),
            "velocity_at_high_substrate": round(v_at_high, 6),
            "catalytic_efficiency": round(Vmax / Km, 6),
            "inhibition_pct": round((1.0 - (Vmax_app / Vmax)) * 100.0, 3) if inh_type != "competitive" else 0.0,
        }
    }

    plots = [
        {
            "plot_type": "line",
            "title": "Michaelis-Menten Kinetics — Reaction Velocity v vs [S]",
            "x_label": "Substrate Concentration [S] (µM)",
            "y_label": "Initial Velocity v (µM/min)",
            "x": S_range.tolist(),
            "y": v_control.tolist(),
            "series_name": "Uninhibited v([S])",
            "extra_series": (
                [{"y": v_inhibited.tolist(), "name": f"Inhibited ([I]={I_val} µM, {inh_type})", "color": "#f59e0b"}]
                if I_val > 0 else None
            ),
        },
        {
            "plot_type": "line",
            "title": "Lineweaver-Burk Double Reciprocal Plot (1/v vs 1/[S])",
            "x_label": "1/[S] (µM⁻¹)",
            "y_label": "1/v (min/µM)",
            "x": lb_inv_S.tolist(),
            "y": lb_inv_v.tolist(),
            "series_name": "1/v Control",
        },
    ]

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "bio_sim", "experiment_id": "michaelis_menten",
        "solver": {
            "name": "michaelis_menten", "version": "2.0",
            "method": "Exact Briggs-Haldane Steady-State Michaelis-Menten Kinetics",
            "equations": ["v = (V_max * [S]) / (K_m + [S])", "At [S] = K_m: v = V_max / 2"],
        },
        "numerical_results": numerical, "plot_data": plots,
        "visual_data": None, "visualization_type": "graph",
        "observations": [
            f"Michaelis-Menten parameters: Vmax = {Vmax} µM/min, Km = {Km} µM.",
            f"Exact benchmark checks: v(0) = {v_at_0:.4f}, v(Km) = {v_at_Km:.4f} (= Vmax/2 = {Vmax/2:.4f}), v(100·Km) = {v_at_high:.4f}.",
            f"Apparent parameters at [I]={I_val} µM ({inh_type}): Vmax_app={Vmax_app:.3f}, Km_app={Km_app:.3f} µM.",
        ],
        "assumptions": ["Quasi-steady-state assumption ([S] >> [E]_0)", "Initial reaction velocity with negligible product accumulation"],
        "limitations": ["Single-substrate non-cooperative catalysis only"],
        "warnings": [],
        "simulation_log": [f"[bio_sim] Michaelis-Menten kinetics solved (Vmax={Vmax}, Km={Km}, v(Km)={v_at_Km})"],
    }


def _logistic_growth(params: dict) -> Dict[str, Any]:
    """Verhulst logistic population growth ODE + exact analytical comparison."""
    N0 = float(params.get("initial_population") or params.get("N0") or 100.0)
    K = float(params.get("carrying_capacity") or params.get("K") or 1e6)
    r = float(params.get("growth_rate") or params.get("r") or 0.5)
    t_end = float(params.get("time_hours") or params.get("t_end") or 24.0)

    if N0 <= 0 or K <= 0 or r <= 0 or t_end <= 0:
        return build_failed_response(
            {"domain": "biology", "experiment_type": "logistic_growth"},
            f"Logistic growth requires N0>0, K>0, r>0, time_hours>0 (got N0={N0}, K={K}, r={r}, t={t_end}).",
        )

    t_eval = np.linspace(0.0, t_end, 400)
    sol = solve_ivp(lambda t, N: [r * N[0] * (1.0 - N[0] / K)], (0.0, t_end), [N0], t_eval=t_eval, rtol=1e-9, atol=1e-11)
    N_ode = sol.y[0]
    N_analytic = K / (1.0 + ((K - N0) / N0) * np.exp(-r * t_eval))
    max_rel_err = float(np.max(np.abs(N_ode - N_analytic) / np.maximum(N_analytic, 1e-12)))

    doubling_h = math.log(2.0) / r
    inflection_h = math.log((K - N0) / N0) / r if K > N0 else 0.0

    numerical = {
        "growth": {
            "model": "logistic",
            "initial_population": N0,
            "carrying_capacity": K,
            "growth_rate_r_per_h": r,
            "time_hours": t_end,
            "final_population": round(float(N_ode[-1]), 4),
            "analytical_final_population": round(float(N_analytic[-1]), 4),
            "doubling_time_h": round(doubling_h, 4),
            "inflection_time_h": round(inflection_h, 4),
            "max_growth_rate_cells_per_h": round(r * K / 4.0, 4),
            "ode_vs_analytical_max_rel_error": float(f"{max_rel_err:.3e}"),
        }
    }
    per_capita_rate = r * (1.0 - N_ode / K)
    plots = [
        {
            "plot_type": "line",
            "title": f"Logistic Population Growth (N₀={N0:g}, K={K:g}, r={r} h⁻¹)",
            "x_label": "Time (hours)", "y_label": "Population N(t)",
            "x": t_eval.tolist(), "y": N_ode.tolist(), "series_name": "Logistic N(t)",
        },
        {
            "plot_type": "line",
            "title": "Density-Dependent Per-Capita Growth Rate vs Population",
            "x_label": "Population N", "y_label": "Per-Capita Rate (1/N)·dN/dt (h⁻¹)",
            "x": N_ode.tolist(), "y": per_capita_rate.tolist(), "series_name": "r·(1 - N/K)",
        },
    ]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_numerical",
        "engine_used": "bio_sim", "experiment_id": "logistic_growth",
        "solver": {"name": "logistic_growth", "version": "2.0", "method": "Verhulst Logistic ODE (RK45) + Analytical Verification", "equations": ["dN/dt = r*N*(1 - N/K)", "N(t) = K / (1 + ((K-N0)/N0)*exp(-r*t))"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "graph",
        "observations": [
            f"Logistic growth from N₀={N0:g} toward carrying capacity K={K:g} at r={r} h⁻¹ (doubling time = {doubling_h:.2f} h).",
            f"Final population at t={t_end}h: {N_ode[-1]:.2f} (ODE vs analytical max relative error = {max_rel_err:.2e}).",
        ],
        "assumptions": ["Homogeneous well-mixed population with constant r and K"],
        "limitations": ["No lag phase or stationary death phase"], "warnings": [],
        "simulation_log": [f"[bio_sim] Logistic growth solved (rel err={max_rel_err:.2e})"],
    }


def _exponential_growth(params: dict) -> Dict[str, Any]:
    """Malthusian exponential population growth N(t) = N0 * exp(r*t)."""
    N0 = float(params.get("initial_population") or params.get("N0") or 100.0)
    r = float(params.get("growth_rate") or params.get("r") or 0.5)
    t_end = float(params.get("time_hours") or params.get("t_end") or 12.0)

    if N0 <= 0 or r <= 0 or t_end <= 0:
        return build_failed_response(
            {"domain": "biology", "experiment_type": "exponential_growth"},
            f"Exponential growth requires N0>0, r>0, time_hours>0.",
        )

    t_eval = np.linspace(0.0, t_end, 300)
    N = N0 * np.exp(r * t_eval)
    doubling_h = math.log(2.0) / r

    numerical = {
        "growth": {
            "model": "exponential",
            "initial_population": N0,
            "growth_rate_r_per_h": r,
            "time_hours": t_end,
            "final_population": round(float(N[-1]), 4),
            "doubling_time_h": round(doubling_h, 4),
            "population_at_one_doubling": round(float(N0 * math.exp(r * doubling_h)), 4),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": f"Exponential Population Growth (N₀={N0:g}, r={r} h⁻¹)",
        "x_label": "Time (hours)", "y_label": "Population N(t)",
        "x": t_eval.tolist(), "y": N.tolist(), "series_name": "N(t) = N₀·exp(rt)",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "bio_sim", "experiment_id": "exponential_growth",
        "solver": {"name": "exponential_growth", "version": "2.0", "method": "Malthusian Exponential Growth Analytical Solution", "equations": ["dN/dt = r*N", "N(t) = N0 * exp(r*t)", "t_d = ln(2)/r"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "graph",
        "observations": [f"Exponential growth N₀={N0:g}, r={r} h⁻¹ → doubling time = {doubling_h:.3f} h, N({t_end}h) = {N[-1]:.2f}."],
        "assumptions": ["Unlimited nutrient availability (early log-phase approximation)"],
        "limitations": ["Unbounded; ignores carrying capacity and waste accumulation"], "warnings": [],
        "simulation_log": ["[bio_sim] Exponential population growth solved"],
    }


def _gene_expression(params: dict) -> Dict[str, Any]:
    t_eval = np.linspace(0.0, 48.0, 400)
    k_tx = float(params.get("transcription_rate", 0.8))
    k_tl = float(params.get("translation_rate", 0.5))
    d_m = float(params.get("mRNA_degradation") or params.get("mrna_decay_rate") or 0.3)
    d_p = float(params.get("protein_degradation") or params.get("protein_decay_rate") or 0.1)
    if min(k_tx, k_tl, d_m, d_p) <= 0:
        return build_failed_response({"domain": "biology", "experiment_type": "gene_expression"}, "All rate constants must be positive.")

    sol = solve_ivp(lambda t, y: [k_tx - d_m * y[0], k_tl * y[0] - d_p * y[1]], (0.0, 48.0), [0.0, 0.0], t_eval=t_eval, rtol=1e-9, atol=1e-11)
    numerical = {
        "expression": {
            "steady_state_mRNA": round(k_tx / d_m, 4),
            "steady_state_protein": round((k_tl * k_tx) / (d_m * d_p), 4),
            "final_mRNA": round(float(sol.y[0][-1]), 4),
            "final_protein": round(float(sol.y[1][-1]), 4),
        }
    }
    plots = [{
        "plot_type": "line", "title": "Gene Expression Dynamics (mRNA & Protein)",
        "x_label": "Time (hours)", "y_label": "Concentration (AU)",
        "x": t_eval.tolist(), "y": sol.y[1].tolist(), "series_name": "Protein",
        "extra_series": [{"y": sol.y[0].tolist(), "name": "mRNA", "color": "#10b981"}],
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_numerical",
        "engine_used": "bio_sim", "experiment_id": "gene_expression",
        "solver": {"name": "gene_expression", "version": "2.0", "method": "Linear Transcription-Translation ODE (RK45)", "equations": ["dm/dt = k_tx - d_m*m", "dp/dt = k_tl*m - d_p*p"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "graph",
        "observations": [f"Steady-state mRNA = {k_tx/d_m:.3f} AU, steady-state protein = {(k_tl*k_tx)/(d_m*d_p):.3f} AU."],
        "assumptions": ["Constitutive deterministic kinetics"], "limitations": ["Stochastic transcriptional bursting omitted"], "warnings": [],
        "simulation_log": ["[bio_sim] Gene expression ODE solved"],
    }


def run(procedure: dict) -> dict:
    """Explicit biology simulation dispatcher."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    if exp_type in ("", "biology", "biological", "bio"):
        if any(w in text for w in ("michaelis", "menten", "enzyme", "substrate", "lineweaver", "vmax")):
            exp_type = "michaelis_menten"
        elif any(w in text for w in ("exponential growth", "malthusian")):
            exp_type = "exponential_growth"
        elif any(w in text for w in ("logistic", "carrying capacity", "bacterial growth", "population growth", "growth curve")):
            exp_type = "logistic_growth"
        elif any(w in text for w in ("gene expression", "transcription", "translation", "mrna")):
            exp_type = "gene_expression"

    if exp_type in ("michaelis_menten", "enzyme_kinetics", "lineweaver_burk"):
        return _michaelis_menten(params)
    if exp_type in ("logistic_growth", "growth_curve", "bacterial_growth", "population_growth"):
        return _logistic_growth(params)
    if exp_type in ("exponential_growth", "malthusian_growth"):
        return _exponential_growth(params)
    if exp_type == "gene_expression":
        return _gene_expression(params)

    return build_unsupported_response(
        procedure,
        reason=f"Biology experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
        supported_examples=["michaelis_menten", "logistic_growth", "exponential_growth", "gene_expression"],
    )
