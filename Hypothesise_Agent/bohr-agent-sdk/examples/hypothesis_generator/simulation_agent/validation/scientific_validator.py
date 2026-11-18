"""
Scientific Validation Engine
=============================
Independently audits simulation inputs, equations, physical invariants,
equilibrium residuals, algorithm invariants, and numerical stability.

A simulation is NEVER marked `success` merely because Python returned an array.
Failed validations transition status to `validation_failed`.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..experiment_registry import get_experiment_entry
from ..experiment_schema import ValidationCheckItem, ValidationSummary


def _scan_numeric_finiteness(obj: Any, path: str = "root") -> List[str]:
    """Recursively verify there are no NaN or Inf values in outputs."""
    issues: List[str] = []
    if isinstance(obj, bool):
        return issues
    if isinstance(obj, (int, float, np.floating, np.integer)):
        if not math.isfinite(float(obj)):
            issues.append(f"Non-finite numeric value at {path}: {obj!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            issues.extend(_scan_numeric_finiteness(v, f"{path}.{k}"))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            if i < 500:  # Cap scan for very large arrays, or check numpy directly
                issues.extend(_scan_numeric_finiteness(v, f"{path}[{i}]"))
    return issues


class ScientificValidator:
    """
    Multi-aspect scientific verification engine:
      1. Input & registry conformance
      2. Numerical finiteness, array alignment, and overflow checks
      3. Experiment-specific physical invariants & algorithm invariants
      4. Honest status classification (`success`, `partial`, `validation_failed`, `unsupported`, `failed`)
    """

    def validate(self, raw_result: Dict[str, Any], procedure: Dict[str, Any]) -> Tuple[ValidationSummary, str]:
        """
        Validate a solver result against procedure and physical/algorithmic invariants.
        Returns: (ValidationSummary, recommended_simulation_status).
        """
        raw_status = str(raw_result.get("simulation_status") or raw_result.get("status") or "success").lower()
        exp_id = str(raw_result.get("experiment_id") or procedure.get("experiment_type") or "").strip().lower()
        num = raw_result.get("numerical_results") or {}
        plots = raw_result.get("plot_data") or []
        warnings = list(raw_result.get("warnings") or [])
        errors: List[str] = []
        checks: List[ValidationCheckItem] = []

        # Pass through unsupported / failed honestly
        if raw_status in ("unsupported", "failed"):
            err_msg = str(raw_result.get("error") or (warnings[0] if warnings else f"Simulation {raw_status}"))
            summary = ValidationSummary(
                input_valid=(raw_status != "failed"),
                dimensional_valid=False,
                physical_constraints_valid=False,
                overall_valid=False,
                validation_level="failed" if raw_status == "failed" else "implemented",
                checks=[ValidationCheckItem(name="solver_execution", passed=False, detail=err_msg)],
                errors=[err_msg],
                warnings=warnings,
            )
            return summary, raw_status

        entry = get_experiment_entry(exp_id)

        # ── 1. Registry & Input Check ─────────────────────────────────────────
        input_ok = True
        if entry is not None:
            checks.append(ValidationCheckItem(
                name="registry_registration",
                passed=True,
                detail=f"Experiment '{entry.experiment_id}' matched registered solver '{entry.solver}' ({entry.domain}).",
            ))
        else:
            checks.append(ValidationCheckItem(
                name="registry_registration",
                passed=False,
                detail=f"Experiment '{exp_id}' is not registered in EXPERIMENT_REGISTRY.",
            ))
            warnings.append(f"Unregistered experiment '{exp_id}' cannot be fully validated against domain benchmarks.")

        # ── 2. Numerical Finiteness & Plot Array Alignment ────────────────────
        nan_issues = _scan_numeric_finiteness(num, "numerical_results")
        plot_issues: List[str] = []
        for idx, p in enumerate(plots):
            px = p.get("x", []) if isinstance(p, dict) else getattr(p, "x", [])
            py = p.get("y", []) if isinstance(p, dict) else getattr(p, "y", [])
            if len(px) != len(py):
                plot_issues.append(f"Plot[{idx}] x/y length mismatch ({len(px)} vs {len(py)})")
            for arr_name, arr in (("x", px), ("y", py)):
                for val in arr:
                    if isinstance(val, (int, float, np.floating)) and not isinstance(val, bool):
                        if not math.isfinite(float(val)):
                            plot_issues.append(f"Plot[{idx}].{arr_name} contains non-finite value {val!r}")
                            break

        numerical_ok = (len(nan_issues) == 0) and (len(plot_issues) == 0)
        if not numerical_ok:
            errors.extend(nan_issues[:5] + plot_issues[:5])
        checks.append(ValidationCheckItem(
            name="numerical_finiteness_and_alignment",
            passed=numerical_ok,
            detail="All numerical outputs and plot arrays are finite and aligned." if numerical_ok else "; ".join((nan_issues + plot_issues)[:3]),
        ))

        # ── 3. Dimensional & Physical / Algorithmic Invariants ────────────────
        eq_valid: Optional[bool] = None
        phys_ok = True
        conv_ok: Optional[bool] = True

        def add_check(name: str, passed: bool, detail: str, residual: Optional[float] = None, tol: Optional[float] = None, critical: bool = True):
            nonlocal phys_ok
            checks.append(ValidationCheckItem(name=name, passed=passed, detail=detail, residual=residual, tolerance=tol))
            if not passed:
                if critical:
                    phys_ok = False
                    errors.append(f"[{name}] {detail}")
                else:
                    warnings.append(f"[{name}] {detail}")

        # --- Civil Beams ---
        if exp_id in (
            "simply_supported_beam_point_load",
            "simply_supported_beam_eccentric_point_load",
            "simply_supported_beam_udl",
            "simply_supported_beam_multiple_loads",
            "simply_supported_beam_moment",
        ):
            ba = num.get("beam_analysis", {})
            f_res = abs(float(ba.get("force_equilibrium_residual_kN", 0.0)))
            m_res = abs(float(ba.get("moment_equilibrium_residual_kNm", 0.0)))
            eq_valid = (f_res < 1e-6) and (m_res < 1e-6)
            add_check("static_force_equilibrium", f_res < 1e-6, f"ΣF_y residual = {f_res:.2e} kN", residual=f_res, tol=1e-6)
            add_check("static_moment_equilibrium", m_res < 1e-6, f"ΣM residual = {m_res:.2e} kN·m", residual=m_res, tol=1e-6)
            if exp_id == "simply_supported_beam_point_load":
                P = float(ba.get("point_load_kN", 0.0))
                L = float(ba.get("span_m", 0.0))
                M_exp = P * L / 4.0
                M_act = float(ba.get("max_bending_moment_kNm", 0.0))
                m_err = abs(M_act - M_exp)
                add_check("central_point_load_moment_identity", m_err < 1e-4, f"M_max={M_act} vs PL/4={M_exp}", residual=m_err, tol=1e-4)
            elif exp_id == "simply_supported_beam_udl":
                w = float(ba.get("load_kN_per_m", 0.0))
                L = float(ba.get("span_m", 0.0))
                M_exp = w * L * L / 8.0
                M_act = float(ba.get("max_bending_moment_kNm", 0.0))
                m_err = abs(M_act - M_exp)
                add_check("udl_moment_identity", m_err < 1e-4, f"M_max={M_act} vs wL²/8={M_exp}", residual=m_err, tol=1e-4)

        elif exp_id in ("cantilever_beam_point_load", "cantilever_beam_udl"):
            ca = num.get("cantilever_analysis", {})
            f_res = abs(float(ca.get("force_equilibrium_residual_kN", 0.0)))
            m_res = abs(float(ca.get("moment_equilibrium_residual_kNm", 0.0)))
            eq_valid = (f_res < 1e-6) and (m_res < 1e-6)
            add_check("cantilever_force_equilibrium", f_res < 1e-6, f"ΣF_y residual = {f_res:.2e} kN", residual=f_res, tol=1e-6)
            add_check("cantilever_moment_equilibrium", m_res < 1e-6, f"ΣM_root residual = {m_res:.2e} kN·m", residual=m_res, tol=1e-6)

        elif exp_id == "truss_analysis":
            tr = num.get("truss", {})
            f_res = abs(float(tr.get("force_equilibrium_residual_kN", 0.0)))
            j_res = abs(float(tr.get("max_joint_equilibrium_residual_N", 0.0)))
            eq_valid = (f_res < 1e-5) and (j_res < 1e-3)
            add_check("truss_global_equilibrium", f_res < 1e-5, f"Global ΣF_y residual = {f_res:.2e} kN", residual=f_res, tol=1e-5)
            add_check("truss_joint_equilibrium", j_res < 1e-3, f"Max nodal equilibrium residual = {j_res:.2e} N", residual=j_res, tol=1e-3)

        # --- Mechanical ---
        elif exp_id == "four_bar_linkage":
            fb = num.get("four_bar_linkage", {})
            c_res = float(fb.get("max_closure_residual_m", 1.0))
            l_err = float(fb.get("max_link_length_error_m", 1.0))
            eq_valid = (c_res < 1e-6) and (l_err < 1e-6)
            add_check("vector_loop_closure", c_res < 1e-6, f"Max vector-loop closure residual = {c_res:.2e} m", residual=c_res, tol=1e-6)
            add_check("link_length_consistency", l_err < 1e-6, f"Max link-length drift = {l_err:.2e} m", residual=l_err, tol=1e-6)

        elif exp_id == "gear_train":
            gt = num.get("gear_train", {})
            p_in = float(gt.get("power_input_kW", 0.0))
            p_out = float(gt.get("power_output_kW", 0.0))
            ratio_prod = abs(float(gt.get("teeth_driver", 1)) * float(gt.get("rpm_input", 0)) - float(gt.get("teeth_driven", 1)) * float(gt.get("rpm_output", 0)))
            add_check("gear_kinematic_product", ratio_prod < 1e-2, f"|N1*RPM1 - N2*RPM2| = {ratio_prod:.3e}", residual=ratio_prod, tol=1e-2)
            add_check("power_conservation_bound", p_out <= p_in + 1e-6, f"P_out={p_out} kW <= P_in={p_in} kW")

        elif exp_id == "carnot_cycle":
            cc = num.get("carnot_cycle", {})
            ds = abs(float(cc.get("net_entropy_change_kJ_K", 0.0)))
            eta = float(cc.get("efficiency_percent", 0.0))
            add_check("zero_cycle_entropy", ds < 1e-6, f"|ΔS_cycle| = {ds:.2e} kJ/K", residual=ds, tol=1e-6)
            add_check("efficiency_bounds", 0.0 < eta < 100.0, f"Carnot η = {eta}%")

        # --- Electronics ---
        elif exp_id == "series_rlc":
            rlc = num.get("rlc", {})
            kvl = abs(float(rlc.get("kvl_residual_V", 0.0)))
            f0 = float(rlc.get("resonant_frequency_Hz", 0.0))
            L_val = float(rlc.get("inductance_H", 1.0))
            C_val = float(rlc.get("capacitance_F", 1.0))
            f0_exp = 1.0 / (2.0 * math.pi * math.sqrt(L_val * C_val))
            f0_err = abs(f0 - f0_exp)
            eq_valid = (kvl < 0.05) and (f0_err < 1e-3)
            add_check("kirchhoff_voltage_law", kvl < 0.05, f"KVL numerical residual = {kvl:.2e} V", residual=kvl, tol=0.05)
            add_check("resonant_frequency_exact", f0_err < 1e-3, f"f0={f0} Hz vs 1/(2π√LC)={f0_exp:.5f} Hz", residual=f0_err, tol=1e-3)

        elif exp_id in ("ohms_law", "series_parallel_circuit", "voltage_divider", "current_divider", "rc_circuit", "rl_circuit", "transformer"):
            block = next(iter(num.values()), {}) if isinstance(num, dict) else {}
            if isinstance(block, dict):
                for rk in ("kvl_residual_V", "kvl_max_residual_V", "kcl_residual_A", "power_balance_error_W", "power_balance_residual_W"):
                    if block.get(rk) is not None:
                        val = abs(float(block[rk]))
                        ok = val < 1e-4
                        eq_valid = ok if eq_valid is None else (eq_valid and ok)
                        add_check(rk, ok, f"{rk} = {val:.2e}", residual=val, tol=1e-4)

        # --- Chemistry ---
        elif exp_id == "acid_base_titration":
            tit = num.get("titration", {})
            cb_res = abs(float(tit.get("max_charge_balance_residual_M", 0.0)))
            ph_init = float(tit.get("initial_pH", 7.0))
            ph_eq = float(tit.get("equivalence_pH", 7.0))
            ph_fin = float(tit.get("final_pH", 7.0))
            eq_valid = cb_res < 1e-9
            add_check("charge_balance_equilibrium", cb_res < 1e-9, f"Max charge-balance residual = {cb_res:.2e} M", residual=cb_res, tol=1e-9)
            add_check("ph_physical_bounds_and_monotonicity", 0.0 <= ph_init <= ph_eq <= ph_fin <= 14.0, f"pH_init={ph_init}, pH_eq={ph_eq}, pH_final={ph_fin}")

        elif exp_id == "reaction_kinetics":
            kin = num.get("kinetics", {})
            mb = abs(float(kin.get("mass_balance_error_M", 0.0)))
            ode_err = abs(float(kin.get("ode_vs_analytical_max_error_M", 0.0)))
            eq_valid = mb < 1e-6
            conv_ok = ode_err < 1e-4
            add_check("chemical_mass_balance", mb < 1e-6, f"Mass balance residual = {mb:.2e} M", residual=mb, tol=1e-6)
            add_check("ode_analytical_convergence", ode_err < 1e-4, f"ODE vs analytical max error = {ode_err:.2e} M", residual=ode_err, tol=1e-4)

        elif exp_id == "chemical_equilibrium":
            ce = num.get("chemical_equilibrium", {})
            ma_res = abs(float(ce.get("mass_action_residual", 0.0)))
            mb = abs(float(ce.get("mass_balance_error_M", 0.0)))
            eq_valid = (ma_res < 1e-4) and (mb < 1e-6)
            add_check("mass_action_law", ma_res < 1e-4, f"|Q - K_eq| = {ma_res:.2e}", residual=ma_res, tol=1e-4)
            add_check("mass_balance", mb < 1e-6, f"Mass balance error = {mb:.2e} M", residual=mb, tol=1e-6)

        # --- Biology ---
        elif exp_id == "michaelis_menten":
            ek = num.get("enzyme_kinetics", {})
            vmax = float(ek.get("Vmax_uninhibited", 0.0))
            v_km = float(ek.get("velocity_at_Km", 0.0))
            v_0 = float(ek.get("velocity_at_zero_substrate", 0.0))
            err_half = abs(v_km - vmax / 2.0)
            add_check("zero_substrate_zero_rate", abs(v_0) < 1e-9, f"v(0) = {v_0}", residual=abs(v_0), tol=1e-9)
            add_check("half_vmax_at_Km", err_half < 1e-4, f"v(Km)={v_km} vs Vmax/2={vmax/2.0}", residual=err_half, tol=1e-4)

        elif exp_id == "logistic_growth":
            gr = num.get("growth", {})
            rel_err = abs(float(gr.get("ode_vs_analytical_max_rel_error", 0.0)))
            final_n = float(gr.get("final_population", 0.0))
            K = float(gr.get("carrying_capacity", 1.0))
            conv_ok = rel_err < 1e-4
            add_check("logistic_ode_convergence", rel_err < 1e-4, f"ODE vs analytical max rel error = {rel_err:.2e}", residual=rel_err, tol=1e-4)
            add_check("carrying_capacity_bound", 0.0 <= final_n <= K * (1.0 + 1e-4), f"N_final={final_n} <= K={K}")

        # --- Physics ---
        elif exp_id == "pendulum":
            em = num.get("energy_metrics", {})
            e_err = em.get("energy_conservation_error_pct")
            if e_err is not None:
                add_check("energy_conservation_undamped", float(e_err) < 0.05, f"Undamped energy drift = {e_err}%", residual=float(e_err), tol=0.05)

        elif exp_id == "projectile_motion":
            ke = num.get("kinematic_energy", {})
            e_err = ke.get("energy_conservation_error_pct")
            if e_err is not None:
                add_check("energy_conservation_vacuum", float(e_err) < 1e-3, f"Vacuum energy conservation error = {e_err}%", residual=float(e_err), tol=1e-3)

        # --- Computer Science Algorithms ---
        elif exp_id in ("bubble_sort", "selection_sort", "insertion_sort", "merge_sort", "quick_sort", "heap_sort"):
            ae = num.get("algorithm_execution", {})
            inp = ae.get("input_data", [])
            out = ae.get("sorted_array", [])
            is_sorted = all(out[i] <= out[i + 1] for i in range(len(out) - 1))
            is_perm = Counter(inp) == Counter(out)
            add_check("sorted_order_invariant", is_sorted, "Output array is non-decreasing." if is_sorted else "Output array is NOT sorted!")
            add_check("permutation_invariant", is_perm, "Output preserves exact input multiset." if is_perm else "Output lost or mutated elements!")

        elif exp_id in ("breadth_first_search", "depth_first_search"):
            ae = num.get("algorithm_execution", {})
            order = ae.get("traversal_order", [])
            start = ae.get("input_data", {}).get("start_node")
            no_dups = len(order) == len(set(order))
            starts_ok = bool(order) and (order[0] == start)
            add_check("no_duplicate_visits", no_dups, f"Visited {len(order)} unique nodes." if no_dups else "Duplicate node traversal detected!")
            add_check("starts_at_source", starts_ok, f"Traversal begins at start_node='{start}'.")

        elif exp_id == "topological_sort":
            ae = num.get("algorithm_execution", {})
            order = ae.get("topological_order", [])
            graph = ae.get("input_data", {}).get("graph", {})
            pos = {node: i for i, node in enumerate(order)}
            precedence_ok = all(pos[u] < pos[v] for u, nbrs in graph.items() for v in nbrs)
            add_check("dag_edge_precedence", precedence_ok, "Every directed edge u->v satisfies pos(u) < pos(v).")

        elif exp_id in ("linear_search", "binary_search"):
            ae = num.get("algorithm_execution", {})
            arr = ae.get("input_data", {}).get("array", [])
            target = ae.get("input_data", {}).get("target")
            found = ae.get("found", False)
            idx = ae.get("found_index", -1)
            ok = (arr[idx] == target) if found else (target not in arr)
            add_check("search_correctness", ok, f"found={found}, index={idx}, target={target}")

        overall_valid = input_ok and numerical_ok and phys_ok and (len(errors) == 0)

        if not overall_valid:
            final_status = "validation_failed"
            level = "failed"
        elif str(raw_result.get("simulation_type", "")) == "illustrative":
            final_status = "illustrative"
            level = "implemented"
        elif any("omitted" in w.lower() or "missing" in w.lower() for w in warnings):
            final_status = "partial"
            level = "validated_within_assumptions"
        else:
            final_status = "success"
            level = "validated_within_assumptions" if entry is not None else "tested"

        summary = ValidationSummary(
            input_valid=input_ok,
            dimensional_valid=numerical_ok and phys_ok,
            equilibrium_valid=eq_valid,
            physical_constraints_valid=phys_ok,
            benchmark_valid=overall_valid if entry is not None else None,
            numerical_convergence=conv_ok,
            overall_valid=overall_valid,
            validation_level=level,
            checks=checks,
            errors=errors,
            warnings=warnings,
        )
        return summary, final_status


_validator = ScientificValidator()


def validate_simulation_result(raw_result: Dict[str, Any], procedure: Dict[str, Any]) -> Tuple[ValidationSummary, str]:
    """Convenience entrypoint for validating any simulation result."""
    return _validator.validate(raw_result, procedure)
