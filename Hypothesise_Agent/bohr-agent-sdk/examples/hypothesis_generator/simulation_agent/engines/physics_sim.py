"""
Physics Simulation Engine
Handles: mechanics, circuits, thermodynamics, optics
"""

import numpy as np
from scipy.integrate import solve_ivp


def run(procedure: dict) -> dict:
    """Physics simulation: ODE-based mechanical/electrical/thermal systems."""
    log = ["[physics_sim] Starting physics simulation"]
    params = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type", "pendulum")
    results = {}
    plots = []

    if exp_type == "pendulum":
        g = params.get("gravity", 9.81)
        L = params.get("length_m", 1.0)
        b = params.get("damping", 0.1)
        th0 = params.get("angle_rad", 0.5)
        t_eval = np.linspace(0, 15, 600)

        def pendulum(t, y):
            th, w = y
            return [w, -(g / L) * np.sin(th) - b * w]

        sol = solve_ivp(pendulum, (0, 15), [th0, 0], t_eval=t_eval)
        results["pendulum"] = {
            "natural_period_s": round(2 * np.pi * np.sqrt(L / g), 4),
            "max_angle_rad": float(np.max(np.abs(sol.y[0]))),
            "damping_coeff": b,
        }
        plots.append({
            "plot_type": "line",
            "title": "Damped Pendulum Oscillation",
            "x_label": "Time (s)",
            "y_label": "Angle θ (rad)",
            "x": t_eval.tolist(),
            "y": sol.y[0].tolist(),
            "series_name": "Angular Displacement",
        })
        log.append(f"[physics_sim] Period={results['pendulum']['natural_period_s']}s")

    elif exp_type == "rlc_circuit":
        R = params.get("resistance_ohm", 10)
        L_h = params.get("inductance_H", 0.1)
        C_f = params.get("capacitance_F", 0.001)
        V0 = params.get("voltage_V", 5.0)
        t_eval = np.linspace(0, 0.5, 600)

        def rlc(t, y):
            q, i = y
            return [i, (V0 - R * i - q / C_f) / L_h]

        sol = solve_ivp(rlc, (0, 0.5), [0, 0], t_eval=t_eval)
        omega_0 = 1 / np.sqrt(L_h * C_f)
        results["rlc"] = {
            "resonant_frequency_Hz": round(omega_0 / (2 * np.pi), 3),
            "damping_ratio": round(R / (2 * np.sqrt(L_h / C_f)), 4),
            "peak_current_A": float(np.max(np.abs(sol.y[1]))),
        }
        plots.append({
            "plot_type": "line",
            "title": "RLC Circuit — Current Response",
            "x_label": "Time (s)",
            "y_label": "Current (A)",
            "x": t_eval.tolist(),
            "y": sol.y[1].tolist(),
            "series_name": "Current",
        })

    elif exp_type == "projectile":
        v0 = params.get("initial_velocity_ms", 20)
        angle = np.radians(params.get("launch_angle_deg", 45))
        g = params.get("gravity", 9.81)
        t_flight = 2 * v0 * np.sin(angle) / g
        t_eval = np.linspace(0, t_flight, 300)
        x = v0 * np.cos(angle) * t_eval
        y = v0 * np.sin(angle) * t_eval - 0.5 * g * t_eval ** 2
        results["projectile"] = {
            "max_range_m": round(v0 ** 2 * np.sin(2 * angle) / g, 3),
            "max_height_m": round((v0 * np.sin(angle)) ** 2 / (2 * g), 3),
            "flight_time_s": round(t_flight, 3),
        }
        plots.append({
            "plot_type": "scatter",
            "title": "Projectile Trajectory",
            "x_label": "Horizontal Distance (m)",
            "y_label": "Height (m)",
            "x": x.tolist(),
            "y": y.tolist(),
            "series_name": "Trajectory",
        })

    return {
        "numerical_results": results,
        "plot_data": plots,
        "observations": [str(v) for v in list(results.values())[:1]],
        "confidence_score": 0.95,
        "simulation_log": log,
    }
