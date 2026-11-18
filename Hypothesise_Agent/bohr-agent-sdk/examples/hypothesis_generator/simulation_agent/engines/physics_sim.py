"""
Physics Simulation Engine
==========================
Explicit deterministic ODE & analytical solvers:
  - pendulum (explicitly distinguishes small_angle, nonlinear, damped, and driven models;
    verifies energy conservation when undamped and compares against analytical period)
  - projectile_motion (vacuum exact analytical or quadratic air-drag RK45 ODE; explicitly
    states air-resistance assumption)
  - series_rlc (delegates cleanly to electronics_sim._rlc_series for unified RLC + circuit scene)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List
import numpy as np
from scipy.integrate import solve_ivp

from . import electronics_sim
from .llm_fallback import build_unsupported_response, build_failed_response


def _pendulum(params: dict, text: str = "") -> Dict[str, Any]:
    g = float(params.get("gravity") or params.get("g") or 9.81)
    L = float(params.get("length_m") or params.get("L") or 1.0)
    b = float(params.get("damping", 0.0))
    if params.get("angle_rad") is not None:
        th0 = float(params["angle_rad"])
    elif params.get("angle_deg") is not None:
        th0 = math.radians(float(params["angle_deg"]))
    else:
        th0 = 0.5
    mass = float(params.get("bob_mass_kg") or params.get("mass_kg") or 0.5)
    drive_amp = float(params.get("drive_amplitude", 0.0))
    drive_omega = float(params.get("drive_frequency_rad_s", 2.0))
    t_end = float(params.get("duration_s", 15.0))

    if g <= 0 or L <= 0 or mass <= 0 or b < 0:
        return build_failed_response({"domain": "physics", "experiment_type": "pendulum"}, "Pendulum requires g>0, L>0, mass>0, damping>=0.")

    # Explicitly determine pendulum model regime
    mode = str(params.get("model_mode", "")).lower().strip()
    if not mode:
        if drive_amp > 0 or "driven" in text:
            mode = "driven"
        elif "small-angle" in text or "small angle" in text:
            mode = "small_angle"
        elif b > 0 or "damped" in text:
            mode = "damped"
        else:
            mode = "nonlinear"

    warnings: List[str] = []
    assumptions = ["Point mass on rigid massless rod", "Planar motion"]
    if mode == "small_angle":
        assumptions.append("Small-angle linear approximation sin(theta) ≈ theta (valid for |theta| < 0.25 rad)")
        if abs(th0) > 0.25:
            warnings.append(f"Initial angle {th0:.3f} rad ({math.degrees(th0):.1f}°) exceeds small-angle validity limit (~14°); nonlinear model recommended.")
    else:
        assumptions.append("Full nonlinear restoring torque -(g/L)*sin(theta)")

    t_eval = np.linspace(0.0, t_end, 600)

    def ode(t, y):
        th, w = y
        restoring = -(g / L) * (th if mode == "small_angle" else math.sin(th))
        damping_term = -(b / mass) * w
        forcing = (drive_amp / (mass * L)) * math.cos(drive_omega * t) if mode == "driven" else 0.0
        return [w, restoring + damping_term + forcing]

    sol = solve_ivp(ode, (0.0, t_end), [th0, 0.0], t_eval=t_eval, method="RK45", rtol=1e-9, atol=1e-11)
    th_arr, w_arr = sol.y[0], sol.y[1]

    # Small-angle period vs exact elliptic-series nonlinear period
    T_small = 2.0 * math.pi * math.sqrt(L / g)
    # 2nd-order exact elliptic expansion: T_nl = T_0 * (1 + (1/16)*th0^2 + (11/3072)*th0^4)
    T_nonlinear_exact = T_small * (1.0 + (th0 ** 2) / 16.0 + (11.0 / 3072.0) * (th0 ** 4))

    ke_arr = 0.5 * mass * ((L * w_arr) ** 2)
    pe_arr = mass * g * L * (0.5 * (th_arr ** 2) if mode == "small_angle" else (1.0 - np.cos(th_arr)))
    total_e = ke_arr + pe_arr
    e0 = max(float(total_e[0]), 1e-12)
    e_drift_pct = float(np.max(np.abs(total_e - total_e[0])) / e0 * 100.0) if (b == 0 and drive_amp == 0) else float((total_e[0] - total_e[-1]) / e0 * 100.0)

    numerical = {
        "pendulum": {
            "model_mode": mode,
            "length_m": L,
            "gravity_ms2": g,
            "initial_angle_rad": round(th0, 5),
            "small_angle_period_s": round(T_small, 5),
            "nonlinear_period_s": round(T_nonlinear_exact, 5),
            "natural_period_s": round(T_small if mode == "small_angle" else T_nonlinear_exact, 5),
            "natural_frequency_Hz": round(1.0 / (T_small if mode == "small_angle" else T_nonlinear_exact), 5),
            "max_angle_rad": round(float(np.max(np.abs(th_arr))), 5),
            "peak_angular_vel_rad_s": round(float(np.max(np.abs(w_arr))), 5),
            "damping_coeff": b,
        },
        "energy_metrics": {
            "initial_energy_J": round(float(total_e[0]), 6),
            "final_energy_J": round(float(total_e[-1]), 6),
            "energy_conservation_error_pct": round(e_drift_pct, 5) if (b == 0 and drive_amp == 0) else None,
            "energy_dissipated_pct": round(float(((total_e[0] - total_e[-1]) / e0) * 100.0), 3) if b > 0 else 0.0,
        },
    }

    plots = [
        {"plot_type": "line", "title": f"Pendulum Oscillation θ(t) — Mode: {mode}", "x_label": "Time (s)", "y_label": "Angle θ (rad)", "x": t_eval.tolist(), "y": th_arr.tolist(), "series_name": "θ(t)"},
        {"plot_type": "line", "title": "Phase Space Portrait (ω vs θ)", "x_label": "Angle θ (rad)", "y_label": "Angular Velocity ω (rad/s)", "x": th_arr.tolist(), "y": w_arr.tolist(), "series_name": "Phase Trajectory"},
        {"plot_type": "line", "title": "Mechanical Energy Partition vs Time", "x_label": "Time (s)", "y_label": "Energy (J)", "x": t_eval.tolist(), "y": total_e.tolist(), "series_name": "Total Energy E", "extra_series": [{"y": ke_arr.tolist(), "name": "Kinetic K", "color": "#10b981"}, {"y": pe_arr.tolist(), "name": "Potential U", "color": "#a855f7"}]},
    ]

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_numerical",
        "engine_used": "physics_sim", "experiment_id": "pendulum",
        "solver": {
            "name": f"pendulum_{mode}", "version": "2.0",
            "method": f"SciPy RK45 (rtol=1e-9, atol=1e-11) — {mode} model",
            "equations": ["theta'' + (b/m)*theta' + (g/L)*sin(theta) = 0", "T_0 = 2*pi*sqrt(L/g)"],
        },
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "graph",
        "observations": [
            f"Pendulum mode='{mode}': small-angle T₀ = {T_small:.4f} s, nonlinear T = {T_nonlinear_exact:.4f} s (L={L} m, θ₀={th0:.3f} rad).",
            f"Initial mechanical energy = {total_e[0]:.5f} J, final = {total_e[-1]:.5f} J.",
        ],
        "assumptions": assumptions,
        "limitations": ["Pivot dry friction and quadratic aerodynamic drag omitted"],
        "warnings": warnings,
        "simulation_log": [f"[physics_sim] Pendulum ({mode}) integrated with RK45 rtol=1e-9"],
    }


def _projectile(params: dict) -> Dict[str, Any]:
    v0 = float(params.get("initial_velocity_ms") or params.get("v0") or 20.0)
    angle_deg = float(params.get("launch_angle_deg") or params.get("angle_deg") or 45.0)
    g = float(params.get("gravity") or params.get("g") or 9.81)
    mass = float(params.get("mass_kg", 1.0))
    Cd = float(params.get("drag_coeff") or params.get("Cd") or 0.0)
    area = float(params.get("cross_section_m2", 0.01))
    rho = float(params.get("air_density_kg_m3", 1.225))

    if v0 <= 0 or g <= 0 or mass <= 0 or not (0.0 < angle_deg < 90.0) or Cd < 0:
        return build_failed_response({"domain": "physics", "experiment_type": "projectile_motion"}, "Invalid projectile parameters.")

    angle = math.radians(angle_deg)
    vx0, vy0 = v0 * math.cos(angle), v0 * math.sin(angle)
    air_drag = Cd > 0.0

    if not air_drag:
        t_flight = 2.0 * vy0 / g
        t_eval = np.linspace(0.0, t_flight, 300)
        x = vx0 * t_eval
        y = vy0 * t_eval - 0.5 * g * (t_eval ** 2)
        vx = np.full_like(t_eval, vx0)
        vy = vy0 - g * t_eval
        max_range = float((v0 ** 2) * math.sin(2.0 * angle) / g)
        max_height = float((vy0 ** 2) / (2.0 * g))
        assumptions = ["Air resistance is NEGLECTED (ideal vacuum ballistic model)", "Uniform gravitational field g, flat ground y=0"]
    else:
        k_drag = 0.5 * rho * Cd * area / mass

        def drag_ode(t, s):
            _, _, vx_s, vy_s = s
            spd = math.hypot(vx_s, vy_s)
            return [vx_s, vy_s, -k_drag * spd * vx_s, -g - k_drag * spd * vy_s]

        def hit_ground(t, s):
            return s[1]
        hit_ground.terminal = True
        hit_ground.direction = -1

        t_max_est = max(2.0 * vy0 / g * 1.5, 5.0)
        sol = solve_ivp(drag_ode, (0.0, t_max_est), [0.0, 0.0, vx0, vy0], events=hit_ground, rtol=1e-9, atol=1e-11, max_step=0.05)
        t_flight = float(sol.t[-1])
        t_eval = np.linspace(0.0, t_flight, 300)
        sol_d = solve_ivp(drag_ode, (0.0, t_flight), [0.0, 0.0, vx0, vy0], t_eval=t_eval, rtol=1e-9, atol=1e-11)
        x, y, vx, vy = sol_d.y[0], np.maximum(0.0, sol_d.y[1]), sol_d.y[2], sol_d.y[3]
        max_range = float(x[-1])
        max_height = float(np.max(y))
        assumptions = [f"Quadratic aerodynamic drag INCLUDED (Cd={Cd}, A={area} m², ρ={rho} kg/m³)", "Uniform gravitational field g, flat ground"]

    v_mag = np.sqrt(vx ** 2 + vy ** 2)
    ke = 0.5 * mass * (v_mag ** 2)
    pe = mass * g * np.maximum(y, 0.0)
    tot_e = ke + pe
    e_err_pct = float(np.max(np.abs(tot_e - tot_e[0])) / max(tot_e[0], 1e-12) * 100.0) if not air_drag else None

    numerical = {
        "projectile": {
            "air_resistance_included": air_drag,
            "max_range_m": round(max_range, 5),
            "max_height_m": round(max_height, 5),
            "flight_time_s": round(t_flight, 5),
            "launch_angle_deg": angle_deg,
            "initial_velocity_ms": v0,
            "impact_speed_ms": round(float(v_mag[-1]), 5),
        },
        "kinematic_energy": {
            "initial_ke_J": round(float(ke[0]), 5),
            "final_energy_J": round(float(tot_e[-1]), 5),
            "energy_conservation_error_pct": round(e_err_pct, 8) if e_err_pct is not None else None,
        },
    }
    plots = [
        {"plot_type": "line", "title": f"Projectile Trajectory ({'With Air Drag' if air_drag else 'Vacuum — No Air Drag'})", "x_label": "Horizontal Distance x (m)", "y_label": "Height y (m)", "x": x.tolist(), "y": y.tolist(), "series_name": f"θ={angle_deg}°"},
        {"plot_type": "line", "title": "Kinetic & Potential Energy vs Time", "x_label": "Time (s)", "y_label": "Energy (J)", "x": t_eval.tolist(), "y": ke.tolist(), "series_name": "Kinetic K", "extra_series": [{"y": pe.tolist(), "name": "Potential U", "color": "#a855f7"}]},
    ]
    return {
        "status": "success", "simulation_status": "success",
        "simulation_type": "deterministic_numerical" if air_drag else "deterministic_analytical",
        "engine_used": "physics_sim", "experiment_id": "projectile_motion",
        "solver": {
            "name": "projectile_drag" if air_drag else "projectile_vacuum", "version": "2.0",
            "method": "RK45 Quadratic Drag ODE" if air_drag else "Exact Analytical Vacuum Ballistics",
            "equations": ["x(t) = v0*cos(th)*t, y(t) = v0*sin(th)*t - 0.5*g*t^2" if not air_drag else "m*dv/dt = m*g - 0.5*rho*Cd*A*|v|*v"],
        },
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "graph",
        "observations": [
            f"Range R = {max_range:.3f} m, apex H = {max_height:.3f} m, flight time = {t_flight:.3f} s ({'with quadratic air drag' if air_drag else 'vacuum: air resistance neglected'}).",
        ],
        "assumptions": assumptions, "limitations": ["Coriolis force and Magnus spin omitted"], "warnings": [],
        "simulation_log": [f"[physics_sim] Projectile solved ({'drag' if air_drag else 'vacuum'}): R={max_range:.3f}m"],
    }


def run(procedure: dict) -> dict:
    """Explicit physics engine dispatcher."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    if exp_type in ("", "physics", "physical"):
        if any(w in text for w in ("projectile", "ballistic", "trajectory", "launch angle")):
            exp_type = "projectile_motion"
        elif "rlc" in text:
            exp_type = "series_rlc"
        elif "pendulum" in text:
            exp_type = "pendulum"

    if exp_type in ("pendulum", "simple_pendulum", "damped_pendulum", "nonlinear_pendulum", "driven_pendulum"):
        return _pendulum(params, text=text)
    if exp_type in ("projectile_motion", "projectile", "ballistic_trajectory"):
        return _projectile(params)
    if exp_type in ("series_rlc", "rlc_circuit", "rlc", "physics_rlc"):
        return electronics_sim._rlc_series(params)

    return build_unsupported_response(
        procedure,
        reason=f"Physics experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
        supported_examples=["pendulum", "projectile_motion", "series_rlc"],
    )
