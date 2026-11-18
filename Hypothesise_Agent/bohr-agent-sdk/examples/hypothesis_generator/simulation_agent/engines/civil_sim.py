"""
Civil Engineering Simulation Engine
====================================
Explicit linear-elastic structural solvers:
  - simply_supported_beam_point_load (Central point load: R=P/2, Mmax=PL/4, delta=PL^3/(48EI))
  - simply_supported_beam_eccentric_point_load (Eccentric point load at x=a)
  - simply_supported_beam_udl (Uniformly distributed load: R=wL/2, Mmax=wL^2/8, delta=5wL^4/(384EI))
  - simply_supported_beam_multiple_loads (Superposition of multiple concentrated loads)
  - simply_supported_beam_moment (Applied concentrated couple moment M0 at x=a)
  - cantilever_beam_point_load (Fixed-free cantilever with point load at x=a)
  - cantilever_beam_udl (Fixed-free cantilever with UDL)
  - truss_analysis (2D Direct Stiffness Method linear-elastic matrix solver with joint equilibrium check)
  - building_blueprint (Architectural floor plan & preliminary gravity load layout)

Unit discipline:
  - All internal deflection & stiffness math uses strict SI units (N, m, Pa, m^4).
  - Never silently substitutes UDL when point_load_kN is specified.
  - Explicitly reports when E or I is missing instead of fabricating absolute deflections.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .llm_fallback import build_unsupported_response, build_failed_response


# ─── Unit & Property Extraction Helpers ──────────────────────────────────────

def _extract_EI_SI(params: dict) -> Tuple[Optional[float], Optional[float], List[str]]:
    """
    Extract (E_Pa, I_m4, warnings) strictly in SI units.
    Returns None for E_Pa or I_m4 if not supplied by caller — never silently invents them.
    """
    warnings: List[str] = []
    E_Pa: Optional[float] = None
    if params.get("elastic_modulus_Pa") is not None:
        E_Pa = float(params["elastic_modulus_Pa"])
    elif params.get("E_Pa") is not None:
        E_Pa = float(params["E_Pa"])
    elif params.get("elastic_modulus_GPa") is not None:
        E_Pa = float(params["elastic_modulus_GPa"]) * 1e9
    elif params.get("E_GPa") is not None:
        E_Pa = float(params["E_GPa"]) * 1e9
    elif params.get("E") is not None:
        raw_E = float(params["E"])
        # Explicit magnitude disambiguation: GPa values are typically 1..1000, Pa > 1e6
        if raw_E > 1e6:
            E_Pa = raw_E
        else:
            E_Pa = raw_E * 1e9
            warnings.append(f"Interpreted E={raw_E} as GPa ({E_Pa:.3e} Pa); specify elastic_modulus_Pa or elastic_modulus_GPa explicitly.")

    I_m4: Optional[float] = None
    for k in ("second_moment_of_area_m4", "moment_of_inertia_m4", "I_m4", "I"):
        if params.get(k) is not None:
            I_m4 = float(params[k])
            break
    if I_m4 is None and params.get("second_moment_of_area_mm4") is not None:
        I_m4 = float(params["second_moment_of_area_mm4"]) * 1e-12
    elif I_m4 is None and params.get("beam_width_mm") is not None and params.get("beam_depth_mm") is not None:
        # Only compute rectangular I if caller explicitly provided both section dimensions AND E
        if E_Pa is not None and bool(params.get("compute_I_from_rect_section", False)):
            b_m = float(params["beam_width_mm"]) * 1e-3
            h_m = float(params["beam_depth_mm"]) * 1e-3
            I_m4 = b_m * (h_m ** 3) / 12.0

    if E_Pa is not None and E_Pa <= 0:
        raise ValueError(f"Elastic modulus E must be strictly positive, got {E_Pa} Pa.")
    if I_m4 is not None and I_m4 <= 0:
        raise ValueError(f"Second moment of area I must be strictly positive, got {I_m4} m^4.")

    return E_Pa, I_m4, warnings


def _extract_point_load_kN(params: dict) -> Optional[float]:
    for k in ("point_load_kN", "P_kN", "load_kN", "tip_load_kN"):
        if params.get(k) is not None:
            return float(params[k])
    if params.get("point_load_N") is not None:
        return float(params["point_load_N"]) / 1000.0
    if params.get("P") is not None:
        raw = float(params["P"])
        return raw / 1000.0 if raw > 500.0 else raw
    return None


def _extract_udl_kN_per_m(params: dict) -> Optional[float]:
    for k in ("load_kN_per_m", "udl_kN_per_m", "w_kN_per_m"):
        if params.get(k) is not None:
            return float(params[k])
    if params.get("load_N_per_m") is not None:
        return float(params["load_N_per_m"]) / 1000.0
    if params.get("w") is not None:
        raw = float(params["w"])
        return raw / 1000.0 if raw > 200.0 else raw
    return None


def _beam_blueprint_visual(
    title: str,
    L: float,
    support_type: str,
    reactions: Dict[str, float],
    load_elements: List[dict],
    M_max_kNm: float,
    delta_max_mm: Optional[float],
    sigma_max_MPa: Optional[float],
) -> dict:
    bx, by, bw, bh = 80, 140, 560, 40
    elements = [
        {"id": "BEAM", "type": "beam", "x": bx, "y": by, "width": bw, "height": bh, "label": f"Beam L={L}m", "properties": {"span_m": L}},
    ]
    if support_type == "cantilever":
        elements.append({
            "id": "FIXED_CLAMP", "type": "fixed_support",
            "x": bx - 20, "y": by - 20, "width": 20, "height": bh + 40,
            "label": f"Fixed (R={reactions.get('R_fixed', 0):.2f} kN, M={reactions.get('M_fixed', 0):.2f} kNm)",
            "properties": reactions,
        })
    else:
        elements.append({"id": "SUP_A", "type": "pin_support", "x": bx, "y": by + bh, "label": f"A (R={reactions.get('R_A', 0):.2f} kN)", "properties": {"reaction_kN": reactions.get("R_A", 0)}})
        elements.append({"id": "SUP_B", "type": "roller_support", "x": bx + bw, "y": by + bh, "label": f"B (R={reactions.get('R_B', 0):.2f} kN)", "properties": {"reaction_kN": reactions.get("R_B", 0)}})
    elements.extend(load_elements)
    elements.append({"id": "DIM_L", "type": "dimension", "x1": bx, "y1": by + bh + 70, "x2": bx + bw, "y2": by + bh + 70, "label": f"{L} m", "properties": {}})
    annotations = [{"x": bx + bw / 2, "y": by + bh + 38, "text": f"M_max = {M_max_kNm:.2f} kN·m", "color": "#f59e0b"}]
    if delta_max_mm is not None:
        annotations.append({"x": bx + bw - 140, "y": by + bh + 55, "text": f"δ_max = {delta_max_mm:.3f} mm", "color": "#3b82f6"})
    if sigma_max_MPa is not None:
        annotations.append({"x": bx + 10, "y": by + bh + 38, "text": f"σ_max = {sigma_max_MPa:.2f} MPa", "color": "#ef4444"})
    return {
        "blueprint_type": "structural",
        "title": title,
        "width": 720, "height": 420,
        "elements": elements,
        "annotations": annotations,
    }


# ─── 1. Simply Supported Beam — Central Point Load ───────────────────────────

def _beam_central_point_load(params: dict) -> Dict[str, Any]:
    """
    Simply supported beam of span L with central point load P at x = L/2:
      R_A = R_B = P / 2
      M_max = P * L / 4
      delta_max = P * L^3 / (48 * E * I)  (when E and I are provided)
    """
    L = float(params.get("span_m") or params.get("L") or params.get("length_m") or 0.0)
    P_kN = _extract_point_load_kN(params)
    if L <= 0 or P_kN is None or P_kN <= 0:
        return build_failed_response(
            {"domain": "civil", "experiment_type": "simply_supported_beam_point_load"},
            f"Central point-load beam requires positive span_m (got {L}) and point_load_kN (got {P_kN}).",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    P_N = P_kN * 1000.0
    R_A = P_kN / 2.0
    R_B = P_kN / 2.0
    M_max = P_kN * L / 4.0

    # Exact piecewise SFD & BMD
    x_left = np.linspace(0.0, L / 2.0, 200, endpoint=False)
    x_right = np.linspace(L / 2.0, L, 201)
    x = np.concatenate([x_left, x_right])
    V = np.where(x < L / 2.0, R_A, -R_B)
    M = np.where(x <= L / 2.0, R_A * x, R_A * x - P_kN * (x - L / 2.0))

    delta_max_mm: Optional[float] = None
    delta_profile_mm: Optional[np.ndarray] = None
    sigma_max_MPa: Optional[float] = None
    deflection_computed = False

    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4  # N*m^2
        # Euler-Bernoulli exact central point load deflection (meters, downward positive)
        y_left = (P_N * x_left / (48.0 * EI)) * (3.0 * (L ** 2) - 4.0 * (x_left ** 2))
        xr = L - x_right
        y_right = (P_N * xr / (48.0 * EI)) * (3.0 * (L ** 2) - 4.0 * (xr ** 2))
        y_m = np.concatenate([y_left, y_right])
        delta_profile_mm = y_m * 1000.0
        delta_max_mm = float((P_N * (L ** 3)) / (48.0 * EI) * 1000.0)
        deflection_computed = True
        b_depth_m = float(params.get("beam_depth_mm", 400.0)) * 1e-3
        sigma_max_MPa = float(((M_max * 1000.0) * (b_depth_m / 2.0) / I_m4) / 1e6)
    else:
        warnings.append(
            "Elastic deflection omitted: both elastic_modulus_Pa (E) and second_moment_of_area_m4 (I) "
            "must be supplied to compute absolute Euler-Bernoulli deflection delta = P*L^3 / (48*E*I)."
        )

    numerical: Dict[str, Any] = {
        "beam_analysis": {
            "load_case": "central_point_load",
            "support_type": "simply_supported",
            "span_m": L,
            "point_load_kN": P_kN,
            "load_position_m": L / 2.0,
            "reaction_A_kN": round(R_A, 6),
            "reaction_B_kN": round(R_B, 6),
            "max_bending_moment_kNm": round(M_max, 6),
            "max_shear_force_kN": round(R_A, 6),
            "deflection_computed": deflection_computed,
            "max_deflection_mm": round(delta_max_mm, 6) if delta_max_mm is not None else None,
            "max_bending_stress_MPa": round(sigma_max_MPa, 4) if sigma_max_MPa is not None else None,
            "elastic_modulus_Pa": E_Pa,
            "second_moment_of_area_m4": I_m4,
            "force_equilibrium_residual_kN": round((R_A + R_B) - P_kN, 12),
            "moment_equilibrium_residual_kNm": round(R_B * L - P_kN * (L / 2.0), 12),
        }
    }

    plots = [
        {"plot_type": "line", "title": "Shear Force Diagram (SFD) — Central Point Load", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Bending Moment Diagram (BMD) — Central Point Load", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    if delta_profile_mm is not None:
        plots.append({"plot_type": "line", "title": "Elastic Deflection Curve δ(x) — Central Point Load", "x_label": "Position x (m)", "y_label": "Downward Deflection δ (mm)", "x": x.tolist(), "y": delta_profile_mm.tolist(), "series_name": "Deflection δ(x)"})

    bx, by, bw = 80, 140, 560
    load_els = [{"id": "PL1", "type": "point_load", "x": bx + bw / 2.0, "y": by - 45, "label": f"P = {P_kN} kN", "properties": {"point_load_kN": P_kN}}]
    visual_data = _beam_blueprint_visual(
        f"Simply Supported Beam — {L}m span, Central Point Load P = {P_kN} kN",
        L, "simply_supported", {"R_A": R_A, "R_B": R_B}, load_els, M_max, delta_max_mm, sigma_max_MPa,
    )

    obs = [
        f"Simply supported beam (L = {L} m) under central point load P = {P_kN} kN at x = {L/2:.2f} m.",
        f"Support reactions: R_A = R_B = P/2 = {R_A:.3f} kN (ΣF_y = 0 verified).",
        f"Maximum bending moment at midspan: M_max = P·L/4 = {M_max:.3f} kN·m.",
    ]
    if delta_max_mm is not None:
        obs.append(f"Maximum elastic midspan deflection: δ_max = P·L³/(48·E·I) = {delta_max_mm:.4f} mm.")
    else:
        obs.append("Deflection not calculated because E and/or I were not provided.")

    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim",
        "experiment_id": "simply_supported_beam_point_load",
        "solver": {
            "name": "beam_central_point_load",
            "version": "2.0",
            "method": "Euler-Bernoulli Analytical Solution (Central Point Load)",
            "equations": ["R_A = R_B = P / 2", "M_max = P * L / 4", "delta_max = P * L^3 / (48 * E * I)"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": visual_data,
        "visualization_type": "blueprint",
        "observations": obs,
        "assumptions": ["Linear-elastic Euler-Bernoulli beam", "Pin support at x=0, roller support at x=L", "Small deflections"],
        "limitations": ["Shear deformation and self-weight neglected"],
        "warnings": warnings,
        "simulation_log": [f"[civil_sim] Central point-load beam solved: R_A={R_A} kN, R_B={R_B} kN, M_max={M_max} kN·m"],
    }


# ─── 2. Simply Supported Beam — Eccentric Point Load ─────────────────────────

def _beam_eccentric_point_load(params: dict) -> Dict[str, Any]:
    """Simply supported beam with single point load P at x = a (0 < a < L)."""
    L = float(params.get("span_m") or params.get("L") or 0.0)
    P_kN = _extract_point_load_kN(params)
    a = float(params.get("load_position_m") or params.get("a_m") or params.get("a") or (L / 2.0))
    if L <= 0 or P_kN is None or P_kN <= 0 or not (0.0 < a < L):
        return build_failed_response(
            {"domain": "civil", "experiment_type": "simply_supported_beam_eccentric_point_load"},
            f"Eccentric point load requires L>0, P>0, and 0 < a < L (got L={L}, P={P_kN}, a={a}).",
        )

    b = L - a
    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    P_N = P_kN * 1000.0
    R_A = P_kN * b / L
    R_B = P_kN * a / L
    M_max = P_kN * a * b / L

    x = np.linspace(0.0, L, 400)
    V = np.where(x < a, R_A, -R_B)
    M = np.where(x <= a, R_A * x, R_A * x - P_kN * (x - a))

    delta_max_mm: Optional[float] = None
    delta_profile_mm: Optional[np.ndarray] = None
    deflection_computed = False
    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4
        y_m = np.where(
            x <= a,
            (P_N * b * x / (6.0 * EI * L)) * (L ** 2 - b ** 2 - x ** 2),
            (P_N * a * (L - x) / (6.0 * EI * L)) * (2.0 * L * x - x ** 2 - a ** 2),
        )
        delta_profile_mm = y_m * 1000.0
        delta_max_mm = float(np.max(delta_profile_mm))
        deflection_computed = True
    else:
        warnings.append("Elastic deflection omitted: E and I required.")

    numerical = {
        "beam_analysis": {
            "load_case": "eccentric_point_load",
            "support_type": "simply_supported",
            "span_m": L,
            "point_load_kN": P_kN,
            "load_position_m": a,
            "reaction_A_kN": round(R_A, 6),
            "reaction_B_kN": round(R_B, 6),
            "max_bending_moment_kNm": round(M_max, 6),
            "max_shear_force_kN": round(max(R_A, R_B), 6),
            "deflection_computed": deflection_computed,
            "max_deflection_mm": round(delta_max_mm, 6) if delta_max_mm is not None else None,
            "force_equilibrium_residual_kN": round((R_A + R_B) - P_kN, 12),
            "moment_equilibrium_residual_kNm": round(R_B * L - P_kN * a, 12),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Shear Force Diagram (SFD) — Eccentric Point Load", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Bending Moment Diagram (BMD) — Eccentric Point Load", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    if delta_profile_mm is not None:
        plots.append({"plot_type": "line", "title": "Elastic Deflection Curve δ(x)", "x_label": "Position x (m)", "y_label": "Deflection δ (mm)", "x": x.tolist(), "y": delta_profile_mm.tolist(), "series_name": "Deflection δ(x)"})

    bx, by, bw = 80, 140, 560
    load_els = [{"id": "PL1", "type": "point_load", "x": bx + bw * (a / L), "y": by - 45, "label": f"P={P_kN}kN @ {a}m", "properties": {"point_load_kN": P_kN, "a_m": a}}]
    visual_data = _beam_blueprint_visual(f"Simply Supported Beam — Eccentric Load P={P_kN} kN at x={a} m", L, "simply_supported", {"R_A": R_A, "R_B": R_B}, load_els, M_max, delta_max_mm, None)
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "simply_supported_beam_eccentric_point_load",
        "solver": {"name": "beam_eccentric_point_load", "version": "2.0", "method": "Euler-Bernoulli Analytical Solution (Eccentric Point Load)", "equations": ["R_A = P*b/L", "R_B = P*a/L", "M_max = P*a*b/L"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [f"R_A = {R_A:.3f} kN, R_B = {R_B:.3f} kN, M_max = {M_max:.3f} kN·m at x = {a} m."],
        "assumptions": ["Linear-elastic Euler-Bernoulli beam"], "limitations": ["Single vertical load"],
        "warnings": warnings, "simulation_log": ["[civil_sim] Eccentric point-load beam solved"],
    }


# ─── 3. Simply Supported Beam — Uniformly Distributed Load (UDL) ─────────────

def _beam_udl(params: dict) -> Dict[str, Any]:
    """
    Simply supported beam under full-span UDL w (kN/m):
      R_A = R_B = w * L / 2
      M_max = w * L^2 / 8
      delta_max = 5 * w * L^4 / (384 * E * I)
    """
    L = float(params.get("span_m") or params.get("L") or params.get("length_m") or 6.0)
    w_kN_m = _extract_udl_kN_per_m(params)
    if L <= 0 or w_kN_m is None or w_kN_m <= 0:
        return build_failed_response(
            {"domain": "civil", "experiment_type": "simply_supported_beam_udl"},
            f"UDL beam requires positive span_m (got {L}) and load_kN_per_m (got {w_kN_m}).",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    w_N_m = w_kN_m * 1000.0
    R_A = w_kN_m * L / 2.0
    R_B = R_A
    M_max = w_kN_m * (L ** 2) / 8.0

    x = np.linspace(0.0, L, 400)
    V = R_A - w_kN_m * x
    M = R_A * x - 0.5 * w_kN_m * (x ** 2)

    delta_max_mm: Optional[float] = None
    delta_profile_mm: Optional[np.ndarray] = None
    sigma_max_MPa: Optional[float] = None
    deflection_computed = False

    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4
        y_m = (w_N_m * x / (24.0 * EI)) * (L ** 3 - 2.0 * L * (x ** 2) + x ** 3)
        delta_profile_mm = y_m * 1000.0
        delta_max_mm = float(5.0 * w_N_m * (L ** 4) / (384.0 * EI) * 1000.0)
        deflection_computed = True
        b_depth_m = float(params.get("beam_depth_mm", 500.0)) * 1e-3
        sigma_max_MPa = float(((M_max * 1000.0) * (b_depth_m / 2.0) / I_m4) / 1e6)
    else:
        warnings.append("Elastic deflection omitted: elastic_modulus_Pa (E) and second_moment_of_area_m4 (I) are required.")

    numerical = {
        "beam_analysis": {
            "load_case": "uniformly_distributed_load",
            "support_type": "simply_supported",
            "span_m": L,
            "load_kN_per_m": w_kN_m,
            "reaction_A_kN": round(R_A, 6),
            "reaction_B_kN": round(R_B, 6),
            "max_bending_moment_kNm": round(M_max, 6),
            "max_shear_force_kN": round(R_A, 6),
            "deflection_computed": deflection_computed,
            "max_deflection_mm": round(delta_max_mm, 6) if delta_max_mm is not None else None,
            "max_bending_stress_MPa": round(sigma_max_MPa, 4) if sigma_max_MPa is not None else None,
            "elastic_modulus_Pa": E_Pa,
            "second_moment_of_area_m4": I_m4,
            "force_equilibrium_residual_kN": round((R_A + R_B) - w_kN_m * L, 12),
            "moment_equilibrium_residual_kNm": round(R_B * L - (w_kN_m * L) * (L / 2.0), 12),
        }
    }

    plots = [
        {"plot_type": "line", "title": "Shear Force Diagram (SFD) — UDL", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Bending Moment Diagram (BMD) — UDL", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    if delta_profile_mm is not None:
        plots.append({"plot_type": "line", "title": "Elastic Deflection Curve δ(x) — UDL", "x_label": "Position x (m)", "y_label": "Deflection δ (mm)", "x": x.tolist(), "y": delta_profile_mm.tolist(), "series_name": "Deflection δ(x)"})

    bx, by, bw = 80, 140, 560
    load_els = [{"id": "UDL", "type": "distributed_load", "x": bx, "y": by - 55, "width": bw, "label": f"w = {w_kN_m} kN/m", "properties": {"load_kN_per_m": w_kN_m}}]
    visual_data = _beam_blueprint_visual(f"Simply Supported Beam — {L}m span, UDL w = {w_kN_m} kN/m", L, "simply_supported", {"R_A": R_A, "R_B": R_B}, load_els, M_max, delta_max_mm, sigma_max_MPa)

    obs = [
        f"Simply supported beam (L = {L} m) under full-span UDL w = {w_kN_m} kN/m (total load = {w_kN_m*L:.2f} kN).",
        f"Support reactions: R_A = R_B = w·L/2 = {R_A:.3f} kN.",
        f"Maximum bending moment at midspan: M_max = w·L²/8 = {M_max:.3f} kN·m.",
    ]
    if delta_max_mm is not None:
        obs.append(f"Maximum elastic deflection: δ_max = 5·w·L⁴/(384·E·I) = {delta_max_mm:.4f} mm.")

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "simply_supported_beam_udl",
        "solver": {"name": "beam_udl", "version": "2.0", "method": "Euler-Bernoulli Analytical Solution (UDL)", "equations": ["R_A = R_B = w*L/2", "M_max = w*L^2/8", "delta_max = 5*w*L^4/(384*E*I)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": obs, "assumptions": ["Linear-elastic Euler-Bernoulli beam", "Uniformly distributed load across full span"],
        "limitations": ["Shear deformation omitted"], "warnings": warnings,
        "simulation_log": [f"[civil_sim] Simply supported UDL beam solved: R_A={R_A} kN, M_max={M_max} kN·m"],
    }


# ─── 4. Simply Supported Beam — Multiple Point Loads ─────────────────────────

def _beam_multiple_loads(params: dict) -> Dict[str, Any]:
    """Superposition of multiple vertical point loads [{P_kN, a_m}, ...] on simply supported beam."""
    L = float(params.get("span_m") or params.get("L") or 0.0)
    loads = params.get("point_loads") or []
    if L <= 0 or not isinstance(loads, list) or not loads:
        return build_failed_response(
            {"domain": "civil", "experiment_type": "simply_supported_beam_multiple_loads"},
            "Multiple point-load beam requires positive span_m and non-empty point_loads list of {P_kN, a_m}.",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    parsed_loads: List[Tuple[float, float]] = []
    for item in loads:
        P_i = float(item.get("P_kN") or item.get("point_load_kN") or 0.0)
        a_i = float(item.get("a_m") or item.get("load_position_m") or 0.0)
        if P_i <= 0 or not (0.0 < a_i < L):
            return build_failed_response(
                {"domain": "civil", "experiment_type": "simply_supported_beam_multiple_loads"},
                f"Invalid point load entry {item}; requires P_kN > 0 and 0 < a_m < {L}.",
            )
        parsed_loads.append((P_i, a_i))

    total_P = sum(p for p, _ in parsed_loads)
    R_B = sum(p * a for p, a in parsed_loads) / L
    R_A = total_P - R_B

    x = np.linspace(0.0, L, 400)
    V = np.full_like(x, R_A)
    M = R_A * x
    y_m = np.zeros_like(x)

    for P_i, a_i in parsed_loads:
        V = V - np.where(x >= a_i, P_i, 0.0)
        M = M - np.where(x >= a_i, P_i * (x - a_i), 0.0)
        if E_Pa is not None and I_m4 is not None:
            EI = E_Pa * I_m4
            b_i = L - a_i
            P_N = P_i * 1000.0
            y_m += np.where(
                x <= a_i,
                (P_N * b_i * x / (6.0 * EI * L)) * (L ** 2 - b_i ** 2 - x ** 2),
                (P_N * a_i * (L - x) / (6.0 * EI * L)) * (2.0 * L * x - x ** 2 - a_i ** 2),
            )

    M_max = float(np.max(np.abs(M)))
    delta_max_mm = float(np.max(y_m) * 1000.0) if (E_Pa is not None and I_m4 is not None) else None
    if delta_max_mm is None:
        warnings.append("Elastic deflection omitted: E and I required.")

    numerical = {
        "beam_analysis": {
            "load_case": "multiple_point_loads",
            "span_m": L,
            "num_loads": len(parsed_loads),
            "total_load_kN": round(total_P, 6),
            "reaction_A_kN": round(R_A, 6),
            "reaction_B_kN": round(R_B, 6),
            "max_bending_moment_kNm": round(M_max, 6),
            "max_shear_force_kN": round(float(np.max(np.abs(V))), 6),
            "deflection_computed": delta_max_mm is not None,
            "max_deflection_mm": round(delta_max_mm, 6) if delta_max_mm is not None else None,
            "force_equilibrium_residual_kN": round((R_A + R_B) - total_P, 12),
            "moment_equilibrium_residual_kNm": round(R_B * L - sum(p * a for p, a in parsed_loads), 12),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Shear Force Diagram (SFD) — Multiple Point Loads", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Bending Moment Diagram (BMD) — Multiple Point Loads", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    bx, by, bw = 80, 140, 560
    load_els = [{"id": f"PL{i+1}", "type": "point_load", "x": bx + bw * (a_i / L), "y": by - 45, "label": f"{P_i}kN", "properties": {"P_kN": P_i, "a_m": a_i}} for i, (P_i, a_i) in enumerate(parsed_loads)]
    visual_data = _beam_blueprint_visual(f"Simply Supported Beam — {len(parsed_loads)} Point Loads", L, "simply_supported", {"R_A": R_A, "R_B": R_B}, load_els, M_max, delta_max_mm, None)
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "simply_supported_beam_multiple_loads",
        "solver": {"name": "beam_multiple_loads", "version": "2.0", "method": "Euler-Bernoulli Linear Superposition", "equations": ["R_B = sum(P_i * a_i)/L", "R_A = sum(P_i) - R_B"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [f"Superposition of {len(parsed_loads)} loads: R_A={R_A:.3f} kN, R_B={R_B:.3f} kN, M_max={M_max:.3f} kN·m."],
        "assumptions": ["Linear-elastic superposition valid"], "limitations": ["Small deflections only"],
        "warnings": warnings, "simulation_log": ["[civil_sim] Multiple point-load beam solved"],
    }


# ─── 5. Simply Supported Beam — Applied Bending Moment ───────────────────────

def _beam_applied_moment(params: dict) -> Dict[str, Any]:
    """Simply supported beam with clockwise applied bending moment M0 (kN·m) at x = a."""
    L = float(params.get("span_m") or params.get("L") or 0.0)
    M0 = float(params.get("applied_moment_kNm") or params.get("M0_kNm") or params.get("moment_kNm") or 0.0)
    a = float(params.get("moment_position_m") if params.get("moment_position_m") is not None else (L / 2.0))
    if L <= 0 or M0 == 0 or not (0.0 <= a <= L):
        return build_failed_response(
            {"domain": "civil", "experiment_type": "simply_supported_beam_moment"},
            f"Applied moment beam requires L>0, non-zero M0, and 0 <= a <= L.",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    R_A = -M0 / L
    R_B = M0 / L

    x = np.linspace(0.0, L, 400)
    V = np.full_like(x, R_A)
    M = np.where(x < a, R_A * x, R_A * x + M0)
    M_max = float(np.max(np.abs(M)))

    delta_max_mm: Optional[float] = None
    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4
        M0_Nm = M0 * 1000.0
        b = L - a
        # Macaulay exact deflection for clockwise M0 at x=a
        y_m = (M0_Nm / (6.0 * EI * L)) * (
            x * (L ** 2 - 3.0 * (b ** 2) - x ** 2)
            + np.where(x >= a, 3.0 * L * ((x - a) ** 2), 0.0)
        )
        delta_max_mm = float(np.max(np.abs(y_m)) * 1000.0)
    else:
        warnings.append("Elastic deflection omitted: E and I required.")

    numerical = {
        "beam_analysis": {
            "load_case": "applied_bending_moment",
            "span_m": L,
            "applied_moment_kNm": M0,
            "moment_position_m": a,
            "reaction_A_kN": round(R_A, 6),
            "reaction_B_kN": round(R_B, 6),
            "max_bending_moment_kNm": round(M_max, 6),
            "deflection_computed": delta_max_mm is not None,
            "max_deflection_mm": round(delta_max_mm, 6) if delta_max_mm is not None else None,
            "force_equilibrium_residual_kN": round(R_A + R_B, 12),
            "moment_equilibrium_residual_kNm": round(R_B * L - M0, 12),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Shear Force Diagram (SFD) — Applied Moment", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Bending Moment Diagram (BMD) — Applied Moment", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    visual_data = _beam_blueprint_visual(f"Simply Supported Beam — Applied Moment M₀={M0} kN·m at x={a} m", L, "simply_supported", {"R_A": R_A, "R_B": R_B}, [], M_max, delta_max_mm, None)
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "simply_supported_beam_moment",
        "solver": {"name": "beam_applied_moment", "version": "2.0", "method": "Euler-Bernoulli Applied Moment Solution", "equations": ["R_A = -M0/L", "R_B = +M0/L"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [f"Applied moment M₀={M0} kN·m at x={a} m yields R_A={R_A:.3f} kN, R_B={R_B:.3f} kN, |M|_max={M_max:.3f} kN·m."],
        "assumptions": ["Linear-elastic Euler-Bernoulli beam"], "limitations": ["Small deflections"],
        "warnings": warnings, "simulation_log": ["[civil_sim] Applied bending moment beam solved"],
    }


# ─── 6. Cantilever Beam — Point Load ─────────────────────────────────────────

def _cantilever_point_load(params: dict) -> Dict[str, Any]:
    """Fixed-free cantilever beam with vertical point load P at x=a (default tip a=L)."""
    L = float(params.get("span_m") or params.get("L") or params.get("length_m") or 0.0)
    P_kN = _extract_point_load_kN(params)
    a = float(params.get("load_position_m") or params.get("a_m") or L)
    if L <= 0 or P_kN is None or P_kN <= 0 or not (0.0 < a <= L):
        return build_failed_response(
            {"domain": "civil", "experiment_type": "cantilever_beam_point_load"},
            f"Cantilever point load requires L>0, P>0, and 0 < a <= L (got L={L}, P={P_kN}, a={a}).",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    P_N = P_kN * 1000.0
    R_fixed = P_kN
    M_fixed = P_kN * a  # hogging magnitude at root

    x = np.linspace(0.0, L, 400)
    V = np.where(x <= a, P_kN, 0.0)
    M = np.where(x <= a, -P_kN * (a - x), 0.0)

    tip_deflection_mm: Optional[float] = None
    delta_profile_mm: Optional[np.ndarray] = None
    sigma_max_MPa: Optional[float] = None
    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4
        y_m = np.where(
            x <= a,
            (P_N * (x ** 2) * (3.0 * a - x)) / (6.0 * EI),
            (P_N * (a ** 2) * (3.0 * x - a)) / (6.0 * EI),
        )
        delta_profile_mm = y_m * 1000.0
        tip_deflection_mm = float((P_N * (a ** 2) * (3.0 * L - a)) / (6.0 * EI) * 1000.0)
        b_depth_m = float(params.get("beam_depth_mm", 400.0)) * 1e-3
        sigma_max_MPa = float(((M_fixed * 1000.0) * (b_depth_m / 2.0) / I_m4) / 1e6)
    else:
        warnings.append("Elastic deflection omitted: E and I required.")

    numerical = {
        "cantilever_analysis": {
            "load_case": "point_load",
            "support_type": "cantilever",
            "span_m": L,
            "point_load_kN": P_kN,
            "load_position_m": a,
            "fixed_reaction_kN": round(R_fixed, 6),
            "fixed_moment_kNm": round(M_fixed, 6),
            "deflection_computed": tip_deflection_mm is not None,
            "tip_deflection_mm": round(tip_deflection_mm, 6) if tip_deflection_mm is not None else None,
            "max_bending_stress_MPa": round(sigma_max_MPa, 4) if sigma_max_MPa is not None else None,
            "force_equilibrium_residual_kN": round(R_fixed - P_kN, 12),
            "moment_equilibrium_residual_kNm": round(M_fixed - P_kN * a, 12),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Cantilever Shear Force Diagram (SFD) — Point Load", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
        {"plot_type": "line", "title": "Cantilever Bending Moment Diagram (BMD) — Point Load", "x_label": "Position x (m)", "y_label": "Bending Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
    ]
    if delta_profile_mm is not None:
        plots.insert(0, {"plot_type": "line", "title": "Cantilever Elastic Deflection y(x) — Point Load", "x_label": "Position x (m)", "y_label": "Deflection y(x) (mm)", "x": x.tolist(), "y": delta_profile_mm.tolist(), "series_name": "Deflection y(x)"})

    bx, by, bw = 80, 140, 560
    load_els = [{"id": "PL1", "type": "point_load", "x": bx + bw * (a / L), "y": by - 45, "label": f"P={P_kN} kN", "properties": {"point_load_kN": P_kN}}]
    visual_data = _beam_blueprint_visual(f"Cantilever Beam — L={L}m, Point Load P={P_kN} kN @ x={a}m", L, "cantilever", {"R_fixed": R_fixed, "M_fixed": M_fixed}, load_els, M_fixed, tip_deflection_mm, sigma_max_MPa)
    obs = [f"Cantilever (L={L} m) with point load P={P_kN} kN at x={a} m: R_fixed={R_fixed:.3f} kN, M_fixed={M_fixed:.3f} kN·m."]
    if tip_deflection_mm is not None:
        obs.append(f"Tip deflection δ_tip = {tip_deflection_mm:.4f} mm.")
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "cantilever_beam_point_load",
        "solver": {"name": "cantilever_point_load", "version": "2.0", "method": "Euler-Bernoulli Cantilever Point Load", "equations": ["R_fixed = P", "M_fixed = -P*a", "delta_tip = P*a^2*(3L - a)/(6*E*I)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": obs, "assumptions": ["Fixed clamp at x=0, free at x=L", "Linear-elastic small deflection"],
        "limitations": ["Shear deformation omitted"], "warnings": warnings,
        "simulation_log": ["[civil_sim] Cantilever point-load beam solved"],
    }


# ─── 7. Cantilever Beam — UDL ────────────────────────────────────────────────

def _cantilever_udl(params: dict) -> Dict[str, Any]:
    """Fixed-free cantilever beam under uniform distributed load w (kN/m)."""
    L = float(params.get("span_m") or params.get("L") or params.get("length_m") or 3.0)
    w_kN_m = _extract_udl_kN_per_m(params)
    if L <= 0 or w_kN_m is None or w_kN_m <= 0:
        return build_failed_response(
            {"domain": "civil", "experiment_type": "cantilever_beam_udl"},
            f"Cantilever UDL beam requires positive span_m (got {L}) and load_kN_per_m (got {w_kN_m}).",
        )

    E_Pa, I_m4, warnings = _extract_EI_SI(params)
    w_N_m = w_kN_m * 1000.0
    R_fixed = w_kN_m * L
    M_fixed = w_kN_m * (L ** 2) / 2.0

    x = np.linspace(0.0, L, 400)
    V = w_kN_m * (L - x)
    M = -0.5 * w_kN_m * ((L - x) ** 2)

    tip_deflection_mm: Optional[float] = None
    delta_profile_mm: Optional[np.ndarray] = None
    sigma_max_MPa: Optional[float] = None
    if E_Pa is not None and I_m4 is not None:
        EI = E_Pa * I_m4
        y_m = (w_N_m * (x ** 2) / (24.0 * EI)) * (x ** 2 - 4.0 * L * x + 6.0 * (L ** 2))
        delta_profile_mm = y_m * 1000.0
        tip_deflection_mm = float((w_N_m * (L ** 4)) / (8.0 * EI) * 1000.0)
        b_depth_m = float(params.get("beam_depth_mm", 500.0)) * 1e-3
        sigma_max_MPa = float(((M_fixed * 1000.0) * (b_depth_m / 2.0) / I_m4) / 1e6)
    else:
        warnings.append("Elastic deflection omitted: E and I required.")

    numerical = {
        "cantilever_analysis": {
            "load_case": "uniformly_distributed_load",
            "support_type": "cantilever",
            "span_m": L,
            "load_kN_per_m": w_kN_m,
            "fixed_reaction_kN": round(R_fixed, 6),
            "fixed_moment_kNm": round(M_fixed, 6),
            "deflection_computed": tip_deflection_mm is not None,
            "tip_deflection_mm": round(tip_deflection_mm, 6) if tip_deflection_mm is not None else None,
            "max_bending_stress_MPa": round(sigma_max_MPa, 4) if sigma_max_MPa is not None else None,
            "force_equilibrium_residual_kN": round(R_fixed - w_kN_m * L, 12),
            "moment_equilibrium_residual_kNm": round(M_fixed - w_kN_m * L * L / 2.0, 12),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Cantilever Bending Moment Diagram (BMD) — UDL", "x_label": "Position x (m)", "y_label": "Moment M (kN·m)", "x": x.tolist(), "y": M.tolist(), "series_name": "Moment M(x)"},
        {"plot_type": "line", "title": "Cantilever Shear Force Diagram (SFD) — UDL", "x_label": "Position x (m)", "y_label": "Shear Force V (kN)", "x": x.tolist(), "y": V.tolist(), "series_name": "Shear V(x)"},
    ]
    if delta_profile_mm is not None:
        plots.insert(0, {"plot_type": "line", "title": "Cantilever Elastic Deflection y(x) — UDL", "x_label": "Position x (m)", "y_label": "Deflection y(x) (mm)", "x": x.tolist(), "y": delta_profile_mm.tolist(), "series_name": "Deflection y(x)"})

    bx, by, bw = 80, 140, 560
    load_els = [{"id": "UDL", "type": "distributed_load", "x": bx, "y": by - 55, "width": bw, "label": f"w={w_kN_m} kN/m", "properties": {"load_kN_per_m": w_kN_m}}]
    visual_data = _beam_blueprint_visual(f"Cantilever Beam — L={L}m, UDL w={w_kN_m} kN/m", L, "cantilever", {"R_fixed": R_fixed, "M_fixed": M_fixed}, load_els, M_fixed, tip_deflection_mm, sigma_max_MPa)
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "civil_sim", "experiment_id": "cantilever_beam_udl",
        "solver": {"name": "cantilever_udl", "version": "2.0", "method": "Euler-Bernoulli Cantilever UDL", "equations": ["R_fixed = w*L", "M_fixed = -w*L^2/2", "delta_tip = w*L^4/(8*E*I)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [f"Cantilever (L={L} m) under UDL w={w_kN_m} kN/m: R_fixed={R_fixed:.3f} kN, M_fixed={M_fixed:.3f} kN·m."],
        "assumptions": ["Linear-elastic Euler-Bernoulli cantilever beam"], "limitations": ["Small deflections only"],
        "warnings": warnings, "simulation_log": ["[civil_sim] Cantilever UDL beam solved"],
    }


# ─── 8. 2D Direct Stiffness Matrix Truss Solver ──────────────────────────────

def _truss_matrix_stiffness(params: dict) -> Dict[str, Any]:
    """
    2D Linear-Elastic Direct Stiffness Matrix Solver for a statically determinate Pratt Truss.
    Assembles K_global * u = F, solves nodal displacements, support reactions, axial member
    forces, axial stresses/strains, and verifies both global & nodal equilibrium.
    """
    span = float(params.get("span_m") or params.get("L") or 10.0)
    height = float(params.get("height_m") or 3.0)
    n_panels = int(params.get("panels") or 4)
    if n_panels < 2:
        n_panels = 2
    if n_panels % 2 != 0:
        n_panels += 1  # Ensure symmetric Pratt diagonals
    load_kN = float(params.get("point_load_kN") or 20.0)
    E_Pa, _, warnings = _extract_EI_SI(params)
    if E_Pa is None:
        E_Pa = 200e9
        warnings.append("Using standard structural steel E = 200 GPa for matrix stiffness calculation.")
    A_m2 = float(params.get("member_area_m2") or params.get("A_m2") or 0.0025)

    panel_w = span / n_panels

    # Node list: bottom chord 0..n_panels, top chord (n_panels+1)..(2*n_panels - 1)
    nodes: List[Tuple[float, float]] = []
    for i in range(n_panels + 1):
        nodes.append((i * panel_w, 0.0))
    for i in range(1, n_panels):
        nodes.append((i * panel_w, height))

    n_nodes = len(nodes)
    n_dof = 2 * n_nodes

    def top_idx(panel_i: int) -> int:
        return (n_panels + 1) + (panel_i - 1)

    # Members: (name, node_i, node_j, group)
    members: List[Tuple[str, int, int, str]] = []
    # Bottom chord
    for i in range(n_panels):
        members.append((f"BC{i+1}", i, i + 1, "bottom_chord"))
    # Top chord
    for i in range(1, n_panels - 1):
        members.append((f"TC{i}", top_idx(i), top_idx(i + 1), "top_chord"))
    # End sloped diagonals (connecting support to first/last top joint)
    members.append(("ED_L", 0, top_idx(1), "end_diagonal"))
    members.append(("ED_R", n_panels, top_idx(n_panels - 1), "end_diagonal"))
    # Interior verticals
    for i in range(1, n_panels):
        members.append((f"V{i}", i, top_idx(i), "vertical"))
    # Pratt interior diagonals (slope downward toward center)
    mid = n_panels // 2
    for i in range(1, n_panels - 1):
        if i < mid:
            members.append((f"D{i}", top_idx(i), i + 1, "diagonal"))
        else:
            members.append((f"D{i}", i, top_idx(i + 1), "diagonal"))

    # Assemble global stiffness matrix K (N/m)
    K = np.zeros((n_dof, n_dof), dtype=float)
    elem_meta = []
    for name, ni, nj, grp in members:
        x1, y1 = nodes[ni]
        x2, y2 = nodes[nj]
        L_e = math.hypot(x2 - x1, y2 - y1)
        c = (x2 - x1) / L_e
        s = (y2 - y1) / L_e
        k_axial = (E_Pa * A_m2) / L_e
        k_e = k_axial * np.array([
            [ c * c,  c * s, -c * c, -c * s],
            [ c * s,  s * s, -c * s, -s * s],
            [-c * c, -c * s,  c * c,  c * s],
            [-c * s, -s * s,  c * s,  s * s],
        ], dtype=float)
        dofs = [2 * ni, 2 * ni + 1, 2 * nj, 2 * nj + 1]
        for r_i in range(4):
            for c_i in range(4):
                K[dofs[r_i], dofs[c_i]] += k_e[r_i, c_i]
        elem_meta.append((name, ni, nj, grp, L_e, c, s, k_axial, dofs))

    # External load vector F (N): downward point_load_kN at each top chord joint
    F = np.zeros(n_dof, dtype=float)
    n_top = n_panels - 1
    for i in range(1, n_panels):
        ti = top_idx(i)
        F[2 * ti + 1] = -load_kN * 1000.0
    total_load_kN = load_kN * n_top

    # Boundary conditions: node 0 pinned (ux=0, uy=0), node n_panels roller (uy=0)
    fixed_dofs = {0, 1, 2 * n_panels + 1}
    free_dofs = [d for d in range(n_dof) if d not in fixed_dofs]

    K_ff = K[np.ix_(free_dofs, free_dofs)]
    F_f = F[free_dofs]
    u_f = np.linalg.solve(K_ff, F_f)

    u = np.zeros(n_dof, dtype=float)
    u[free_dofs] = u_f

    # Reactions R = K @ u - F (N)
    R = K @ u - F
    R_Ax_kN = float(R[0] / 1000.0)
    R_Ay_kN = float(R[1] / 1000.0)
    R_By_kN = float(R[2 * n_panels + 1] / 1000.0)

    # Compute member axial forces (positive = tension, negative = compression)
    member_results = []
    joint_sum = np.zeros((n_nodes, 2), dtype=float)
    # Add external + reaction forces to joint balance check
    for idx in range(n_nodes):
        joint_sum[idx, 0] += F[2 * idx] + R[2 * idx]
        joint_sum[idx, 1] += F[2 * idx + 1] + R[2 * idx + 1]

    for name, ni, nj, grp, L_e, c, s, k_axial, dofs in elem_meta:
        u_e = u[dofs]
        elongation = (-c * u_e[0] - s * u_e[1] + c * u_e[2] + s * u_e[3])
        force_N = k_axial * elongation
        force_kN = force_N / 1000.0
        stress_MPa = (force_N / A_m2) / 1e6
        strain = elongation / L_e
        member_results.append({
            "id": name, "node_i": ni, "node_j": nj, "group": grp,
            "length_m": round(L_e, 4),
            "axial_force_kN": round(float(force_kN), 4),
            "stress_MPa": round(float(stress_MPa), 4),
            "strain": float(f"{strain:.4e}"),
            "state": "tension" if force_kN > 1e-6 else ("compression" if force_kN < -1e-6 else "zero_force"),
        })
        # Member internal forces acting ON joints ni and nj
        joint_sum[ni, 0] += force_N * c
        joint_sum[ni, 1] += force_N * s
        joint_sum[nj, 0] -= force_N * c
        joint_sum[nj, 1] -= force_N * s

    max_joint_residual_N = float(np.max(np.abs(joint_sum)))
    max_tension_kN = max((m["axial_force_kN"] for m in member_results), default=0.0)
    max_compression_kN = abs(min((m["axial_force_kN"] for m in member_results), default=0.0))
    max_disp_mm = float(np.max(np.abs(u)) * 1000.0)
    max_stress_MPa = max((abs(m["stress_MPa"]) for m in member_results), default=0.0)

    numerical = {
        "truss": {
            "span_m": span,
            "height_m": height,
            "panels": n_panels,
            "point_load_kN": load_kN,
            "total_load_kN": round(total_load_kN, 4),
            "reaction_Ax_kN": round(R_Ax_kN, 6),
            "reaction_A_kN": round(R_Ay_kN, 6),
            "reaction_B_kN": round(R_By_kN, 6),
            "max_tension_kN": round(max_tension_kN, 4),
            "max_compression_kN": round(max_compression_kN, 4),
            "max_nodal_displacement_mm": round(max_disp_mm, 5),
            "max_axial_stress_MPa": round(max_stress_MPa, 4),
            "force_equilibrium_residual_kN": round((R_Ay_kN + R_By_kN) - total_load_kN, 10),
            "max_joint_equilibrium_residual_N": float(f"{max_joint_residual_N:.3e}"),
        },
        "truss_geometry": {
            "nodes": [[round(nx, 4), round(ny, 4)] for nx, ny in nodes],
            "displacements_mm": [[round(float(u[2 * i] * 1000.0), 5), round(float(u[2 * i + 1] * 1000.0), 5)] for i in range(n_nodes)],
            "members": member_results,
        },
    }

    plots = [{
        "plot_type": "bar",
        "title": "Pratt Truss Member Axial Forces (Direct Stiffness Method)",
        "x_label": "Member ID",
        "y_label": "Axial Force (kN) [+Tension / -Compression]",
        "x": [m["id"] for m in member_results],
        "y": [m["axial_force_kN"] for m in member_results],
        "series_name": "Axial Force (kN)",
    }]

    # Blueprint SVG coordinates
    scale = 500.0 / span
    ox, oy_bot = 110.0, 280.0
    elements = []
    for idx, (nx, ny) in enumerate(nodes):
        elements.append({"id": f"N{idx}", "type": "joint", "x": ox + nx * scale, "y": oy_bot - ny * scale, "label": f"N{idx}", "properties": {}})
    for m in member_results:
        x1, y1 = nodes[m["node_i"]]
        x2, y2 = nodes[m["node_j"]]
        elements.append({
            "id": m["id"], "type": "member",
            "x1": ox + x1 * scale, "y1": oy_bot - y1 * scale,
            "x2": ox + x2 * scale, "y2": oy_bot - y2 * scale,
            "member_type": m["group"], "label": f"{m['id']} ({m['axial_force_kN']:+.1f} kN)",
            "properties": {"force_kN": m["axial_force_kN"], "stress_MPa": m["stress_MPa"]},
        })
    elements.append({"id": "SA", "type": "pin_support", "x": ox, "y": oy_bot, "label": f"A ({R_Ay_kN:.1f} kN)", "properties": {"reaction_kN": round(R_Ay_kN, 2)}})
    elements.append({"id": "SB", "type": "roller_support", "x": ox + span * scale, "y": oy_bot, "label": f"B ({R_By_kN:.1f} kN)", "properties": {"reaction_kN": round(R_By_kN, 2)}})
    visual_data = {"blueprint_type": "structural", "title": f"Pratt Truss (Direct Stiffness) — {span}m span, {n_panels} panels", "width": 720, "height": 420, "elements": elements, "annotations": []}

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_numerical",
        "engine_used": "civil_sim", "experiment_id": "truss_analysis",
        "solver": {
            "name": "truss_matrix_stiffness",
            "version": "2.0",
            "method": "2D Direct Stiffness Method (Linear-Elastic Matrix Analysis)",
            "equations": ["K_global * u = F", "N_e = (E*A/L_e)*[-c,-s,c,s].u_e"],
        },
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [
            f"Direct stiffness solution for {n_panels}-panel Pratt truss ({span}m × {height}m, {len(members)} members, {n_nodes} joints).",
            f"Support reactions: R_A = {R_Ay_kN:.2f} kN, R_B = {R_By_kN:.2f} kN (total vertical load = {total_load_kN:.2f} kN).",
            f"Peak tension = {max_tension_kN:.2f} kN, peak compression = {max_compression_kN:.2f} kN, max nodal displacement = {max_disp_mm:.4f} mm.",
            f"Maximum joint equilibrium residual = {max_joint_residual_N:.2e} N (linear-elastic static equilibrium satisfied).",
        ],
        "assumptions": ["2D pin-jointed truss (axial force only)", "Linear-elastic isotropic material", "Small displacements"],
        "limitations": ["Does not check Euler member buckling or 3D out-of-plane bracing"],
        "warnings": warnings,
        "simulation_log": [f"[civil_sim] Direct stiffness matrix solved ({n_dof} DOFs, residual={max_joint_residual_N:.2e} N)"],
    }


# ─── 9. Building Blueprint (preserved) ───────────────────────────────────────

def _building_blueprint(params: dict) -> Dict[str, Any]:
    floors = int(params.get("floors", 2))
    width_m = float(params.get("width_m", 12.0))
    depth_m = float(params.get("depth_m", 8.0))
    floor_h = float(params.get("floor_height_m", 3.0))
    wall_thick = float(params.get("wall_thickness_mm", 230))
    col_size = float(params.get("column_size_mm", 300))
    n_rooms = int(params.get("rooms_per_floor", 4))

    floor_area = width_m * depth_m
    total_area = floor_area * floors
    col_spacing_x = width_m / 3.0
    col_spacing_y = depth_m / 2.0

    numerical = {
        "building": {
            "floors": floors,
            "floor_height_m": floor_h,
            "plan_width_m": width_m,
            "plan_depth_m": depth_m,
            "floor_area_sqm": round(floor_area, 2),
            "total_built_area_sqm": round(total_area, 2),
            "wall_thickness_mm": wall_thick,
            "column_size_mm": col_size,
            "column_grid": f"{round(col_spacing_x, 1)}m × {round(col_spacing_y, 1)}m",
        }
    }
    plots = [{
        "plot_type": "bar",
        "title": "Preliminary Gravity Load Distribution Per Floor",
        "x_label": "Level", "y_label": "Estimated Gravity Load (kN)",
        "x": [f"Floor {i+1}" for i in range(floors)] + ["Foundation"],
        "y": [round(floor_area * 5.0, 1) for _ in range(floors)] + [round(total_area * 5.0 * 1.2, 1)],
        "series_name": "Gravity Load",
    }]
    visual_data = {
        "blueprint_type": "floor_plan",
        "title": f"Floor Plan — {width_m}m × {depth_m}m ({floors} floors, {n_rooms} rooms)",
        "width": 720, "height": 520, "elements": [], "annotations": [],
    }
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "parametric_model",
        "engine_used": "civil_sim", "experiment_id": "building_blueprint",
        "solver": {"name": "building_blueprint", "version": "2.0", "method": "Architectural Plan & Preliminary Gravity Load", "equations": ["A_floor = W * D", "A_total = floors * A_floor"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "blueprint",
        "observations": [f"Building footprint: {width_m}m × {depth_m}m = {floor_area:.1f} m²/floor ({total_area:.1f} m² total)."],
        "assumptions": ["Preliminary 5 kN/m² combined gravity load estimate"],
        "limitations": ["Not a full 3D structural building FEA"], "warnings": [],
        "simulation_log": ["[civil_sim] Building blueprint generated"],
    }


# ─── Main Explicit Entry Point ───────────────────────────────────────────────

_CIVIL_DISPATCH = {
    "simply_supported_beam_point_load": _beam_central_point_load,
    "beam_point_load": _beam_central_point_load,
    "central_point_load_beam": _beam_central_point_load,
    "simply_supported_beam_eccentric_point_load": _beam_eccentric_point_load,
    "eccentric_point_load": _beam_eccentric_point_load,
    "simply_supported_beam_udl": _beam_udl,
    "beam_udl": _beam_udl,
    "simply_supported_beam_multiple_loads": _beam_multiple_loads,
    "simply_supported_beam_moment": _beam_applied_moment,
    "beam_applied_moment": _beam_applied_moment,
    "cantilever_beam_point_load": _cantilever_point_load,
    "cantilever_point_load": _cantilever_point_load,
    "cantilever_beam_udl": _cantilever_udl,
    "cantilever_udl": _cantilever_udl,
    "truss_analysis": _truss_matrix_stiffness,
    "truss": _truss_matrix_stiffness,
    "building_blueprint": _building_blueprint,
}


def run(procedure: dict) -> dict:
    """Explicit civil engineering dispatcher. Never confuses point loads with UDL."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    # Disambiguate legacy generic beam names using explicit parameters & text
    if exp_type in ("beam_analysis", "beam", "simply_supported_beam"):
        if "point_loads" in params:
            exp_type = "simply_supported_beam_multiple_loads"
        elif "applied_moment_kNm" in params or "applied moment" in text:
            exp_type = "simply_supported_beam_moment"
        elif (
            _extract_point_load_kN(params) is not None
            or any(w in text for w in ("point load", "central load", "concentrated load", "midspan load"))
        ) and not any(w in text for w in ("uniformly distributed", "udl", "kn/m", "n/m")):
            if "load_position_m" in params or "a_m" in params or "eccentric" in text:
                exp_type = "simply_supported_beam_eccentric_point_load"
            else:
                exp_type = "simply_supported_beam_point_load"
        else:
            exp_type = "simply_supported_beam_udl"
    elif exp_type in ("cantilever_beam", "cantilever"):
        if (
            _extract_point_load_kN(params) is not None
            or any(w in text for w in ("point load", "tip load", "end load", "concentrated load"))
        ) and not any(w in text for w in ("uniformly distributed", "udl", "kn/m")):
            exp_type = "cantilever_beam_point_load"
        else:
            exp_type = "cantilever_beam_udl"

    solver_fn = _CIVIL_DISPATCH.get(exp_type)
    if solver_fn is None and exp_type in ("", "civil", "civil_engineering", "structural"):
        if "truss" in text:
            solver_fn = _truss_matrix_stiffness
        elif "cantilever" in text:
            solver_fn = _cantilever_point_load if (_extract_point_load_kN(params) is not None or "point load" in text or "tip load" in text) else _cantilever_udl
        elif "beam" in text:
            if _extract_point_load_kN(params) is not None or "point load" in text or "central load" in text:
                solver_fn = _beam_central_point_load
            else:
                solver_fn = _beam_udl
        elif any(w in text for w in ("blueprint", "floor plan")):
            solver_fn = _building_blueprint

    if solver_fn is None:
        return build_unsupported_response(
            procedure,
            reason=f"Civil engineering experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
            supported_examples=list(_CIVIL_DISPATCH.keys()),
        )

    return solver_fn(params)
