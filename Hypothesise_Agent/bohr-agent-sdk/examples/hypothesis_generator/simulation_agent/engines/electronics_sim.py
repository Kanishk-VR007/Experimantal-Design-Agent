"""
Electrical & Electronics Simulation Engine
===========================================
Explicit deterministic circuit solvers with Kirchhoff (KCL/KVL) & Power-Balance verification:
  - ohms_law
  - series_parallel_circuit
  - voltage_divider
  - current_divider
  - rc_circuit
  - rl_circuit
  - series_rlc (RK45 rtol=1e-9 + analytical resonance + KVL residual check)
  - ac_circuit (steady-state phasor impedance & power triangle)
  - transformer (ideal coupled magnetic turns-ratio & power conservation)
  - arduino_led
  - led_resistor

Never defaults an unrecognized electrical experiment to an Arduino LED blink circuit.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List
import numpy as np
from scipy.integrate import solve_ivp

from .llm_fallback import build_unsupported_response, build_failed_response


def _ohms_law(params: dict) -> Dict[str, Any]:
    R = float(params.get("resistance_ohm") or params.get("R") or params.get("R0") or 1000.0)
    V_min = float(params.get("voltage_min", 0.0))
    V_max = float(params.get("supply_voltage_V") or params.get("voltage_max") or params.get("V0") or 10.0)
    if R <= 0 or V_max < V_min:
        return build_failed_response({"domain": "electronics", "experiment_type": "ohms_law"}, f"Invalid Ohm's Law inputs: R={R}, V_min={V_min}, V_max={V_max}.")
    if V_max == V_min:
        V_max = V_min + 10.0

    V_arr = np.linspace(V_min, V_max, 120)
    I_A = V_arr / R
    I_mA = I_A * 1000.0
    P_W = V_arr * I_A
    P_mW = P_W * 1000.0
    power_err = float(np.max(np.abs(P_W - (I_A ** 2) * R)))

    numerical = {
        "ohms_law": {
            "resistance_ohm": round(R, 4),
            "conductance_S": round(1.0 / R, 6),
            "voltage_range_V": [round(V_min, 2), round(V_max, 2)],
            "max_current_A": round(float(I_A[-1]), 6),
            "max_current_mA": round(float(I_mA[-1]), 4),
            "max_power_mW": round(float(P_mW[-1]), 4),
            "kvl_residual_V": round(float(V_max - I_A[-1] * R), 12),
            "power_balance_error_W": float(f"{power_err:.3e}"),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Ohm's Law — Current I vs Voltage V", "x_label": "Voltage V (V)", "y_label": "Current I (mA)", "x": V_arr.tolist(), "y": I_mA.tolist(), "series_name": "I(V) = V/R"},
        {"plot_type": "line", "title": "Power Dissipation P = V²/R", "x_label": "Voltage V (V)", "y_label": "Power (mW)", "x": V_arr.tolist(), "y": P_mW.tolist(), "series_name": "P(V)"},
    ]
    visual_data = {
        "circuit_type": "dc_sweep", "title": f"Ohm's Law — R={R}Ω, V=0..{V_max}V",
        "width": 700, "height": 380,
        "components": [
            {"id": "V_SUPPLY", "type": "dc_source", "x": 100, "y": 140, "label": f"DC {V_max}V"},
            {"id": "RESISTOR", "type": "resistor", "x": 500, "y": 140, "label": f"R={R}Ω"},
        ],
        "wires": [{"from": "V_SUPPLY:pos", "to": "RESISTOR:in"}, {"from": "RESISTOR:out", "to": "V_SUPPLY:neg"}],
    }
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "ohms_law",
        "solver": {"name": "ohms_law", "version": "2.0", "method": "Linear Resistive Ohm's Law", "equations": ["I = V / R", "P = V * I = I^2 * R"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "circuit",
        "observations": [f"R={R} Ω: at V={V_max} V, I={I_mA[-1]:.3f} mA, P={P_mW[-1]:.3f} mW (power balance error={power_err:.2e} W)."],
        "assumptions": ["Constant linear ohmic resistance"], "limitations": ["Thermal drift omitted"], "warnings": [],
        "simulation_log": [f"[electronics_sim] Ohm's law computed for R={R} Ω"],
    }


def _series_parallel_circuit(params: dict) -> Dict[str, Any]:
    V = float(params.get("supply_voltage_V") or params.get("V") or 12.0)
    resistors = [float(r) for r in (params.get("resistors_ohm") or [100.0, 200.0, 300.0])]
    topo = str(params.get("topology", "parallel")).lower().strip()
    if V <= 0 or not resistors or any(r <= 0 for r in resistors):
        return build_failed_response({"domain": "electronics", "experiment_type": "series_parallel_circuit"}, "Voltage and all resistor values must be strictly positive.")

    if topo == "series":
        R_eq = sum(resistors)
        I_tot = V / R_eq
        branch_I = [I_tot for _ in resistors]
        branch_V = [I_tot * r for r in resistors]
        kcl_res = 0.0
        kvl_res = abs(V - sum(branch_V))
    else:
        R_eq = 1.0 / sum(1.0 / r for r in resistors)
        I_tot = V / R_eq
        branch_I = [V / r for r in resistors]
        branch_V = [V for _ in resistors]
        kcl_res = abs(I_tot - sum(branch_I))
        kvl_res = max(abs(V - vb) for vb in branch_V)

    P_src = V * I_tot
    P_diss = sum(i * v for i, v in zip(branch_I, branch_V))
    p_res = abs(P_src - P_diss)

    numerical = {
        "circuit": {
            "topology": topo,
            "supply_voltage_V": V,
            "resistors_ohm": resistors,
            "equivalent_resistance_ohm": round(R_eq, 6),
            "total_current_A": round(I_tot, 6),
            "branch_currents_A": [round(i, 6) for i in branch_I],
            "branch_voltages_V": [round(v, 6) for v in branch_V],
            "total_power_W": round(P_src, 6),
            "kcl_residual_A": float(f"{kcl_res:.3e}"),
            "kvl_residual_V": float(f"{kvl_res:.3e}"),
            "power_balance_residual_W": float(f"{p_res:.3e}"),
        }
    }
    plots = [{
        "plot_type": "bar", "title": f"{topo.title()} Resistor Network — Branch Currents",
        "x_label": "Resistor", "y_label": "Current (A)",
        "x": [f"R{i+1} ({r:g}Ω)" for i, r in enumerate(resistors)], "y": branch_I, "series_name": "Branch Current (A)",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "series_parallel_circuit",
        "solver": {"name": "series_parallel_circuit", "version": "2.0", "method": f"Exact {topo.title()} Nodal/Loop Reduction", "equations": ["R_s = sum(R_i)", "1/R_p = sum(1/R_i)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"{topo.title()} R_eq = {R_eq:.3f} Ω, I_total = {I_tot:.4f} A, P = {P_src:.4f} W (KCL/KVL/Power verified)."],
        "assumptions": ["Ideal DC voltage source and linear resistors"], "limitations": ["Purely resistive DC steady state"], "warnings": [],
        "simulation_log": [f"[electronics_sim] {topo} resistor network solved"],
    }


def _voltage_divider(params: dict) -> Dict[str, Any]:
    V = float(params.get("supply_voltage_V") or params.get("V_in") or 5.0)
    r1 = float(params.get("r1_ohm") or params.get("R1") or 1000.0)
    r2 = float(params.get("r2_ohm") or params.get("R2") or 1000.0)
    if V < 0 or r1 <= 0 or r2 <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "voltage_divider"}, "R1, R2 must be > 0 and supply_voltage_V >= 0.")

    I = V / (r1 + r2)
    V1 = I * r1
    Vout = I * r2
    kvl_res = abs(V - (V1 + Vout))
    p_res = abs(V * I - (I * I * r1 + I * I * r2))

    vin_s = np.linspace(0.0, max(12.0, V * 1.5), 100)
    vout_s = vin_s * r2 / (r1 + r2)

    numerical = {
        "voltage_divider": {
            "supply_V": V, "R1_ohm": r1, "R2_ohm": r2,
            "Vout_V": round(Vout, 6), "V_R1_V": round(V1, 6),
            "current_mA": round(I * 1000.0, 5),
            "division_ratio": round(r2 / (r1 + r2), 6),
            "kvl_residual_V": float(f"{kvl_res:.3e}"),
            "power_balance_residual_W": float(f"{p_res:.3e}"),
        }
    }
    plots = [{"plot_type": "line", "title": f"Voltage Divider Transfer Curve (R1={r1:g}Ω, R2={r2:g}Ω)", "x_label": "V_in (V)", "y_label": "V_out (V)", "x": vin_s.tolist(), "y": vout_s.tolist(), "series_name": "V_out"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "voltage_divider",
        "solver": {"name": "voltage_divider", "version": "2.0", "method": "Unloaded Resistive Voltage Divider", "equations": ["V_out = V_in * R2 / (R1 + R2)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": {"circuit_type": "schematic", "title": f"Voltage Divider Vout={Vout:.3f}V", "components": [], "wires": []}, "visualization_type": "circuit",
        "observations": [f"V_out = {Vout:.4f} V, I = {I*1000:.3f} mA (KVL residual = {kvl_res:.2e} V)."],
        "assumptions": ["Open-circuit (unloaded) output node"], "limitations": ["Finite load shifts V_out"], "warnings": [],
        "simulation_log": ["[electronics_sim] Voltage divider computed"],
    }


def _current_divider(params: dict) -> Dict[str, Any]:
    Itot = float(params.get("total_current_A") or params.get("I_total") or 0.1)
    r1 = float(params.get("r1_ohm") or params.get("R1") or 100.0)
    r2 = float(params.get("r2_ohm") or params.get("R2") or 300.0)
    if Itot < 0 or r1 <= 0 or r2 <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "current_divider"}, "R1, R2 must be > 0 and I_total >= 0.")

    I1 = Itot * r2 / (r1 + r2)
    I2 = Itot * r1 / (r1 + r2)
    V_node = I1 * r1
    kcl_res = abs(Itot - (I1 + I2))
    kvl_res = abs(I1 * r1 - I2 * r2)

    numerical = {
        "current_divider": {
            "total_current_A": Itot, "R1_ohm": r1, "R2_ohm": r2,
            "I1_A": round(I1, 6), "I2_A": round(I2, 6),
            "node_voltage_V": round(V_node, 6),
            "kcl_residual_A": float(f"{kcl_res:.3e}"),
            "kvl_residual_V": float(f"{kvl_res:.3e}"),
        }
    }
    plots = [{"plot_type": "bar", "title": "Current Divider Branch Currents", "x_label": "Branch", "y_label": "Current (A)", "x": ["I_total", f"I1 ({r1:g}Ω)", f"I2 ({r2:g}Ω)"], "y": [Itot, I1, I2], "series_name": "Current (A)"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "current_divider",
        "solver": {"name": "current_divider", "version": "2.0", "method": "Parallel Current Divider", "equations": ["I1 = I_tot * R2/(R1+R2)", "I2 = I_tot * R1/(R1+R2)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"I1 = {I1:.5f} A, I2 = {I2:.5f} A, V_node = {V_node:.4f} V (KCL residual = {kcl_res:.2e} A)."],
        "assumptions": ["Ideal DC current source"], "limitations": ["Two parallel resistors"], "warnings": [],
        "simulation_log": ["[electronics_sim] Current divider computed"],
    }


def _rc_transient(params: dict) -> Dict[str, Any]:
    R = float(params.get("resistance_ohm") or params.get("R") or 1000.0)
    C = float(params.get("capacitance_F") or params.get("C") or 1e-4)
    V0 = float(params.get("voltage_V") or params.get("supply_voltage_V") or 5.0)
    if R <= 0 or C <= 0 or V0 <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "rc_circuit"}, "R, C, V0 must be strictly positive.")

    tau = R * C
    t = np.linspace(0.0, 6.0 * tau, 300)
    vc = V0 * (1.0 - np.exp(-t / tau))
    i_t = (V0 / R) * np.exp(-t / tau)
    vr = i_t * R
    kvl_max_err = float(np.max(np.abs((vr + vc) - V0)))

    numerical = {
        "rc_circuit": {
            "resistance_ohm": R, "capacitance_F": C, "voltage_V": V0,
            "time_constant_s": round(tau, 6),
            "voltage_at_1tau_V": round(float(V0 * (1.0 - math.exp(-1.0))), 6),
            "steady_state_V": round(float(vc[-1]), 6),
            "initial_current_mA": round((V0 / R) * 1000.0, 5),
            "stored_energy_mJ": round(0.5 * C * V0 * V0 * 1000.0, 6),
            "kvl_max_residual_V": float(f"{kvl_max_err:.3e}"),
        }
    }
    plots = [{"plot_type": "line", "title": f"RC Step Response (τ = {tau:.4f} s)", "x_label": "Time (s)", "y_label": "Voltage (V)", "x": t.tolist(), "y": vc.tolist(), "series_name": "V_C(t)", "extra_series": [{"y": vr.tolist(), "name": "V_R(t)", "color": "#ef4444"}]}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "rc_circuit",
        "solver": {"name": "rc_transient", "version": "2.0", "method": "Exact First-Order RC Analytical Solution", "equations": ["tau = R*C", "V_C(t) = V0*(1 - exp(-t/tau))"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"Time constant τ = R·C = {tau:.5f} s; V_C(τ) = {V0*(1-math.exp(-1)):.4f} V (63.2% of {V0}V); KVL max residual = {kvl_max_err:.2e} V."],
        "assumptions": ["Zero initial capacitor charge V_C(0) = 0", "Ideal R and C"],
        "limitations": ["ESR and leakage omitted"], "warnings": [],
        "simulation_log": ["[electronics_sim] RC transient computed"],
    }


def _rl_transient(params: dict) -> Dict[str, Any]:
    R = float(params.get("resistance_ohm") or params.get("R") or 10.0)
    L = float(params.get("inductance_H") or params.get("L") or 0.1)
    V0 = float(params.get("voltage_V") or params.get("supply_voltage_V") or 5.0)
    if R <= 0 or L <= 0 or V0 <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "rl_circuit"}, "R, L, V0 must be strictly positive.")

    tau = L / R
    t = np.linspace(0.0, 6.0 * tau, 300)
    i_t = (V0 / R) * (1.0 - np.exp(-t / tau))
    vl = V0 * np.exp(-t / tau)
    vr = i_t * R
    kvl_max_err = float(np.max(np.abs((vr + vl) - V0)))

    numerical = {
        "rl_circuit": {
            "resistance_ohm": R, "inductance_H": L, "voltage_V": V0,
            "time_constant_s": round(tau, 6),
            "steady_state_current_A": round(V0 / R, 6),
            "stored_energy_mJ": round(0.5 * L * ((V0 / R) ** 2) * 1000.0, 6),
            "kvl_max_residual_V": float(f"{kvl_max_err:.3e}"),
        }
    }
    plots = [{"plot_type": "line", "title": f"RL Step Response (τ = {tau:.4f} s)", "x_label": "Time (s)", "y_label": "Current (A)", "x": t.tolist(), "y": i_t.tolist(), "series_name": "I(t)"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "rl_circuit",
        "solver": {"name": "rl_transient", "version": "2.0", "method": "Exact First-Order RL Analytical Solution", "equations": ["tau = L/R", "I(t) = (V0/R)*(1 - exp(-t/tau))"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"RL time constant τ = L/R = {tau:.5f} s; steady-state I = {V0/R:.4f} A (KVL max residual = {kvl_max_err:.2e} V)."],
        "assumptions": ["I(0) = 0; ideal linear R and L"], "limitations": ["Core saturation omitted"], "warnings": [],
        "simulation_log": ["[electronics_sim] RL transient computed"],
    }


def _rlc_series(params: dict) -> Dict[str, Any]:
    """Series RLC step response with high-precision RK45, exact analytical comparison, and KVL check."""
    R = float(params.get("resistance_ohm") or params.get("R") or 10.0)
    L = float(params.get("inductance_H") or params.get("L") or 0.1)
    C = float(params.get("capacitance_F") or params.get("C") or 0.001)
    V0 = float(params.get("voltage_V") or params.get("supply_voltage_V") or 5.0)
    if R <= 0 or L <= 0 or C <= 0 or V0 <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "series_rlc"}, f"Series RLC requires R>0, L>0, C>0, V0>0.")

    omega0 = 1.0 / math.sqrt(L * C)
    f0 = omega0 / (2.0 * math.pi)
    alpha = R / (2.0 * L)
    zeta = R / (2.0 * math.sqrt(L / C))
    Q_factor = (1.0 / R) * math.sqrt(L / C)

    # Adaptive time window covering ~8 decay time constants or ~6 resonant cycles
    t_end = float(params.get("duration_s") or max(8.0 / max(alpha, 1.0), 6.0 / max(f0, 1.0), 0.1))
    t_end = min(t_end, 10.0)
    t_eval = np.linspace(0.0, t_end, 600)

    def rlc_ode(t, y):
        q, i = y
        return [i, (V0 - R * i - q / C) / L]

    sol = solve_ivp(rlc_ode, (0.0, t_end), [0.0, 0.0], t_eval=t_eval, method="RK45", rtol=1e-9, atol=1e-11)
    q_arr, i_arr = sol.y[0], sol.y[1]
    vc_arr = q_arr / C
    vr_arr = R * i_arr
    # Exact di/dt from ODE gives V_L(t) = L * di/dt
    vl_arr = V0 - vr_arr - vc_arr
    # Verify KVL independently using numerical derivative of i(t) on interior points
    di_dt_num = np.gradient(i_arr, t_eval)
    kvl_num_res = float(np.max(np.abs((vr_arr[2:-2] + L * di_dt_num[2:-2] + vc_arr[2:-2]) - V0)))

    # Analytical underdamped comparison when zeta < 1
    analytical_max_err = None
    if zeta < 1.0 - 1e-6:
        wd = omega0 * math.sqrt(1.0 - zeta * zeta)
        i_exact = (V0 / (L * wd)) * np.exp(-alpha * t_eval) * np.sin(wd * t_eval)
        analytical_max_err = float(np.max(np.abs(i_arr - i_exact)))

    resp_type = "overdamped" if zeta > 1.0 + 1e-4 else ("critically_damped" if abs(zeta - 1.0) <= 1e-4 else "underdamped")

    freqs = np.linspace(max(0.5, f0 * 0.1), f0 * 3.0, 200)
    w_f = 2.0 * np.pi * freqs
    z_mag = np.sqrt(R ** 2 + (w_f * L - 1.0 / (w_f * C)) ** 2)
    i_freq = V0 / z_mag

    numerical = {
        "rlc": {
            "resistance_ohm": R,
            "inductance_H": L,
            "capacitance_F": C,
            "voltage_V": V0,
            "resonant_frequency_Hz": round(f0, 5),
            "angular_resonance_rad_s": round(omega0, 5),
            "damping_ratio_zeta": round(zeta, 6),
            "quality_factor_Q": round(Q_factor, 4),
            "peak_current_A": round(float(np.max(np.abs(i_arr))), 6),
            "steady_state_cap_V": round(float(vc_arr[-1]), 5),
            "response_type": resp_type,
            "kvl_residual_V": float(f"{kvl_num_res:.3e}"),
            "ode_vs_analytical_max_error_A": float(f"{analytical_max_err:.3e}") if analytical_max_err is not None else None,
        }
    }

    plots = [
        {"plot_type": "line", "title": f"Series RLC Transient Current i(t) ({resp_type}, ζ={zeta:.3f})", "x_label": "Time (s)", "y_label": "Current i(t) (A)", "x": t_eval.tolist(), "y": i_arr.tolist(), "series_name": "i(t)"},
        {"plot_type": "line", "title": "Series RLC Component Voltages (KVL)", "x_label": "Time (s)", "y_label": "Voltage (V)", "x": t_eval.tolist(), "y": vc_arr.tolist(), "series_name": "V_C(t)", "extra_series": [{"y": vr_arr.tolist(), "name": "V_R(t)", "color": "#ef4444"}, {"y": vl_arr.tolist(), "name": "V_L(t)", "color": "#a855f7"}]},
        {"plot_type": "line", "title": f"AC Frequency Resonance Sweep (f₀ = {f0:.2f} Hz)", "x_label": "Frequency (Hz)", "y_label": "|I(f)| (A)", "x": freqs.tolist(), "y": i_freq.tolist(), "series_name": "|I(f)|"},
    ]

    visual_data = {
        "circuit_type": "schematic",
        "title": f"Series RLC — R={R}Ω, L={L}H, C={C}F, V₀={V0}V (f₀={f0:.2f}Hz, ζ={zeta:.3f})",
        "width": 660, "height": 360,
        "components": [
            {"id": "VS", "type": "voltage_source", "label": f"V₀ {V0}V", "x": 100, "y": 180, "orientation": "horizontal", "properties": {"voltage_V": V0}},
            {"id": "R1", "type": "resistor", "label": f"R {R}Ω", "x": 265, "y": 80, "orientation": "horizontal", "properties": {"resistance_ohm": R}},
            {"id": "L1", "type": "inductor", "label": f"L {L}H", "x": 420, "y": 80, "orientation": "horizontal", "properties": {"inductance_H": L}},
            {"id": "C1", "type": "capacitor", "label": f"C {C}F", "x": 560, "y": 180, "orientation": "vertical", "properties": {"capacitance_F": C}},
        ],
        "wires": [
            {"id": "w1", "path": [[100, 148], [100, 80], [235, 80]], "color": "#ef4444", "label": f"+{V0}V"},
            {"id": "w2", "path": [[295, 80], [385, 80]], "color": "#f97316", "label": "i(t)"},
            {"id": "w3", "path": [[455, 80], [560, 80], [560, 148]], "color": "#a855f7", "label": ""},
            {"id": "w4", "path": [[560, 212], [560, 280], [100, 280], [100, 212]], "color": "#3b82f6", "label": "GND"},
        ],
    }

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_numerical",
        "engine_used": "electronics_sim", "experiment_id": "series_rlc",
        "solver": {
            "name": "rlc_series", "version": "2.0",
            "method": "Series RLC Second-Order RK45 ODE (rtol=1e-9) + Analytical Verification",
            "equations": ["L*q'' + R*q' + q/C = V0", "f0 = 1/(2*pi*sqrt(L*C))", "zeta = R/(2*sqrt(L/C))"],
        },
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "circuit",
        "observations": [
            f"Series RLC resonant frequency f₀ = {f0:.3f} Hz, damping ratio ζ = {zeta:.4f} ({resp_type}), Q = {Q_factor:.3f}.",
            f"Peak transient current = {float(np.max(np.abs(i_arr))):.5f} A; capacitor steady-state V_C = {vc_arr[-1]:.4f} V.",
            f"KVL verification (V_R + V_L + V_C = V₀): max numerical residual = {kvl_num_res:.2e} V.",
        ],
        "assumptions": ["Zero initial conditions q(0)=0, i(0)=0", "Linear time-invariant ideal R, L, C"],
        "limitations": ["Parasitic winding capacitance and core saturation omitted"], "warnings": [],
        "simulation_log": [f"[electronics_sim] Series RLC solved (f0={f0:.3f}Hz, zeta={zeta:.4f})"],
    }


def _ac_phasor_circuit(params: dict) -> Dict[str, Any]:
    V_rms = float(params.get("voltage_rms_V") or params.get("voltage_V") or 120.0)
    f = float(params.get("frequency_Hz") or params.get("freq") or 60.0)
    R = float(params.get("resistance_ohm") or params.get("R") or 50.0)
    L = float(params.get("inductance_H") or params.get("L") or 0.1)
    C = float(params.get("capacitance_F") or params.get("C") or 1e-4)
    if V_rms <= 0 or f <= 0 or R <= 0 or L < 0 or C <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "ac_circuit"}, "Invalid AC circuit parameters.")

    w = 2.0 * math.pi * f
    X_L = w * L
    X_C = 1.0 / (w * C)
    X_net = X_L - X_C
    Z_mag = math.hypot(R, X_net)
    phi_rad = math.atan2(X_net, R)
    I_rms = V_rms / Z_mag
    pf = math.cos(phi_rad)
    S_VA = V_rms * I_rms
    P_W = S_VA * pf
    Q_VAR = S_VA * math.sin(phi_rad)
    tri_err = abs(S_VA - math.hypot(P_W, Q_VAR))

    t = np.linspace(0.0, 2.0 / f, 200)
    v_t = V_rms * math.sqrt(2.0) * np.sin(w * t)
    i_t = I_rms * math.sqrt(2.0) * np.sin(w * t - phi_rad)

    numerical = {
        "ac_circuit": {
            "frequency_Hz": f, "voltage_rms_V": V_rms,
            "X_L_ohm": round(X_L, 4), "X_C_ohm": round(X_C, 4),
            "impedance_mag_ohm": round(Z_mag, 4),
            "phase_angle_deg": round(math.degrees(phi_rad), 3),
            "current_rms_A": round(I_rms, 5),
            "power_factor": round(pf, 5),
            "real_power_W": round(P_W, 4),
            "reactive_power_VAR": round(Q_VAR, 4),
            "apparent_power_VA": round(S_VA, 4),
            "power_triangle_residual_VA": float(f"{tri_err:.3e}"),
        }
    }
    plots = [{"plot_type": "line", "title": f"AC Steady-State Waveforms (f={f}Hz, φ={math.degrees(phi_rad):.1f}°)", "x_label": "Time (s)", "y_label": "Voltage (V) / Scaled Current", "x": t.tolist(), "y": v_t.tolist(), "series_name": "v(t) [V]", "extra_series": [{"y": (i_t * Z_mag).tolist(), "name": "i(t)*|Z| [phase ref]", "color": "#10b981"}]}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "ac_circuit",
        "solver": {"name": "ac_phasor_circuit", "version": "2.0", "method": "Steady-State Sinusoidal Phasor Analysis", "equations": ["Z = R + j(wL - 1/(wC))", "S^2 = P^2 + Q^2"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"|Z| = {Z_mag:.3f} Ω ∠ {math.degrees(phi_rad):.2f}°, I_rms = {I_rms:.4f} A, PF = {pf:.4f}, P = {P_W:.2f} W."],
        "assumptions": ["Pure sinusoidal steady state"], "limitations": ["No harmonics"], "warnings": [],
        "simulation_log": ["[electronics_sim] AC phasor circuit solved"],
    }


def _ideal_transformer(params: dict) -> Dict[str, Any]:
    Vp = float(params.get("primary_voltage_V") or params.get("Vp") or 240.0)
    Np = int(params.get("turns_primary") or params.get("Np") or 400)
    Ns = int(params.get("turns_secondary") or params.get("Ns") or 100)
    R_load = float(params.get("load_resistance_ohm") or params.get("R_load") or 12.0)
    if Vp <= 0 or Np <= 0 or Ns <= 0 or R_load <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "transformer"}, "Transformer voltage, turns, and load resistance must be > 0.")

    a_ratio = Np / Ns
    Vs = Vp * (Ns / Np)
    Is = Vs / R_load
    Ip = Is * (Ns / Np)
    P_p = Vp * Ip
    P_s = Vs * Is
    p_err = abs(P_p - P_s)

    numerical = {
        "transformer": {
            "primary_voltage_V": Vp, "turns_primary": Np, "turns_secondary": Ns,
            "turns_ratio_Np_Ns": round(a_ratio, 4),
            "secondary_voltage_V": round(Vs, 4),
            "secondary_current_A": round(Is, 5),
            "primary_current_A": round(Ip, 5),
            "power_primary_W": round(P_p, 4),
            "power_secondary_W": round(P_s, 4),
            "power_balance_error_W": float(f"{p_err:.3e}"),
        }
    }
    plots = [{"plot_type": "bar", "title": "Ideal Transformer Primary vs Secondary", "x_label": "Quantity", "y_label": "Value", "x": ["V_p (V)", "V_s (V)", "I_p (A)", "I_s (A)"], "y": [Vp, Vs, Ip, Is], "series_name": "Transformer"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "transformer",
        "solver": {"name": "ideal_transformer", "version": "2.0", "method": "Ideal Coupled-Magnetic Turns Ratio", "equations": ["Vs/Vp = Ns/Np", "Ip/Is = Ns/Np", "Vp*Ip = Vs*Is"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "circuit",
        "observations": [f"Turns ratio {Np}:{Ns} transforms {Vp}V → {Vs:.2f}V; I_s={Is:.3f}A, I_p={Ip:.3f}A, P={P_s:.2f}W (lossless balance error={p_err:.2e}W)."],
        "assumptions": ["Ideal lossless magnetic coupling k=1"], "limitations": ["Core/winding losses omitted"], "warnings": [],
        "simulation_log": ["[electronics_sim] Ideal transformer solved"],
    }


def _arduino_led(params: dict) -> Dict[str, Any]:
    supply_v = float(params.get("supply_voltage_V", 5.0))
    led_vf = float(params.get("led_forward_voltage_V") or params.get("led_vf") or 2.0)
    led_max_mA = float(params.get("led_current_mA", 20.0))
    resistance = params.get("resistance_ohm")
    freq = float(params.get("blink_frequency_Hz", 1.0))
    if supply_v <= led_vf:
        return build_failed_response({"domain": "electronics", "experiment_type": "arduino_led"}, f"Supply voltage ({supply_v}V) must exceed LED forward voltage ({led_vf}V).")
    resistance = float(resistance) if resistance is not None else (supply_v - led_vf) / (led_max_mA / 1000.0)
    actual_i = (supply_v - led_vf) / resistance
    power_r_mW = (actual_i ** 2) * resistance * 1000.0
    kvl_res = abs(supply_v - (actual_i * resistance + led_vf))
    t = np.linspace(0, 5, 500)
    led = (np.sin(2 * np.pi * freq * t) >= 0).astype(float)

    numerical = {
        "circuit": {
            "supply_voltage_V": supply_v, "resistor_value_ohm": round(resistance, 2),
            "led_current_mA": round(actual_i * 1000.0, 3), "led_forward_voltage_V": led_vf,
            "power_resistor_mW": round(power_r_mW, 3), "blink_frequency_Hz": freq,
            "kvl_residual_V": float(f"{kvl_res:.3e}"),
        }
    }
    plots = [{"plot_type": "line", "title": "LED Blink Digital Signal (Pin 13)", "x_label": "Time (s)", "y_label": "LED State", "x": t.tolist(), "y": led.tolist(), "series_name": "LED"}]
    visual_data = {"circuit_type": "schematic", "title": f"Arduino LED — R={resistance:.0f}Ω, I={actual_i*1000:.1f}mA", "width": 700, "height": 380, "components": [{"id": "U1", "type": "arduino_uno", "x": 30, "y": 70}, {"id": "R1", "type": "resistor", "x": 335, "y": 145}, {"id": "D1", "type": "led", "x": 510, "y": 145}], "wires": []}
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "arduino_led",
        "solver": {"name": "arduino_led", "version": "2.0", "method": "DC Limiting-Resistor KVL Loop", "equations": ["R = (Vs - Vf)/I"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "circuit",
        "observations": [f"R = {resistance:.1f} Ω limits LED current to {actual_i*1000:.2f} mA (P_R = {power_r_mW:.2f} mW)."],
        "assumptions": ["Constant LED forward drop Vf"], "limitations": ["Ideal pin drive"], "warnings": [],
        "simulation_log": ["[electronics_sim] Arduino LED circuit computed"],
    }


def _led_resistor(params: dict) -> Dict[str, Any]:
    supply_v = float(params.get("supply_voltage_V", 9.0))
    led_vf = float(params.get("led_forward_voltage_V") or params.get("led_vf") or 2.0)
    resistance = float(params.get("resistance_ohm", 470.0))
    if supply_v <= led_vf or resistance <= 0:
        return build_failed_response({"domain": "electronics", "experiment_type": "led_resistor"}, "Supply voltage must exceed Vf and R > 0.")
    current = (supply_v - led_vf) / resistance
    v_r = current * resistance
    power_mW = (current ** 2) * resistance * 1000.0
    kvl_res = abs(supply_v - (v_r + led_vf))
    numerical = {
        "circuit": {
            "supply_voltage_V": supply_v, "current_mA": round(current * 1000.0, 3),
            "voltage_across_resistor_V": round(v_r, 4), "voltage_across_led_V": led_vf,
            "power_resistor_mW": round(power_mW, 3), "kvl_residual_V": float(f"{kvl_res:.3e}"),
        }
    }
    plots = [{"plot_type": "bar", "title": "Voltage Distribution", "x_label": "Component", "y_label": "Voltage (V)", "x": ["Supply", "Resistor", "LED"], "y": [supply_v, v_r, led_vf], "series_name": "Voltage"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "electronics_sim", "experiment_id": "led_resistor",
        "solver": {"name": "led_resistor", "version": "2.0", "method": "Series LED-Resistor KVL Loop", "equations": ["I = (Vs - Vf)/R"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": {"circuit_type": "schematic", "title": "LED + Resistor", "components": [], "wires": []}, "visualization_type": "circuit",
        "observations": [f"I = {current*1000:.2f} mA, V_R = {v_r:.3f} V, V_LED = {led_vf} V."],
        "assumptions": ["Constant LED forward voltage drop"], "limitations": ["Shockley diode curve simplified"], "warnings": [],
        "simulation_log": ["[electronics_sim] LED + resistor circuit computed"],
    }


_ELEC_DISPATCH = {
    "ohms_law": _ohms_law, "ohm": _ohms_law, "iv_curve": _ohms_law,
    "series_parallel_circuit": _series_parallel_circuit, "series_circuit": _series_parallel_circuit, "parallel_circuit": _series_parallel_circuit,
    "voltage_divider": _voltage_divider,
    "current_divider": _current_divider,
    "rc_circuit": _rc_transient, "rc_charging": _rc_transient, "rc_transient": _rc_transient,
    "rl_circuit": _rl_transient, "rl_transient": _rl_transient,
    "series_rlc": _rlc_series, "rlc_circuit": _rlc_series, "rlc": _rlc_series, "physics_rlc": _rlc_series,
    "ac_circuit": _ac_phasor_circuit, "ac_impedance": _ac_phasor_circuit, "phasor_circuit": _ac_phasor_circuit,
    "transformer": _ideal_transformer, "ideal_transformer": _ideal_transformer,
    "arduino_led": _arduino_led, "arduino": _arduino_led, "arduino_blink": _arduino_led, "blink": _arduino_led,
    "led_resistor": _led_resistor,
}


def run(procedure: dict) -> dict:
    """Explicit electronics/electrical circuit dispatcher."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    if exp_type in ("", "electronics", "electrical", "circuit"):
        if "rlc" in text:
            exp_type = "series_rlc"
        elif "transformer" in text:
            exp_type = "transformer"
        elif "voltage divider" in text:
            exp_type = "voltage_divider"
        elif "current divider" in text:
            exp_type = "current_divider"
        elif "rc circuit" in text or "rc charging" in text:
            exp_type = "rc_circuit"
        elif "rl circuit" in text:
            exp_type = "rl_circuit"
        elif "ac circuit" in text or "phasor" in text or "impedance" in text:
            exp_type = "ac_circuit"
        elif "series" in text or "parallel" in text:
            exp_type = "series_parallel_circuit"
        elif any(w in text for w in ("arduino", "blink", "microcontroller")):
            exp_type = "arduino_led"
        elif "ohm" in text or "i-v" in text:
            exp_type = "ohms_law"
        elif "led" in text:
            exp_type = "led_resistor"

    solver_fn = _ELEC_DISPATCH.get(exp_type)
    if solver_fn is None:
        return build_unsupported_response(
            procedure,
            reason=f"Electrical/electronics experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
            supported_examples=sorted(set(_ELEC_DISPATCH.keys())),
        )
    return solver_fn(params)
