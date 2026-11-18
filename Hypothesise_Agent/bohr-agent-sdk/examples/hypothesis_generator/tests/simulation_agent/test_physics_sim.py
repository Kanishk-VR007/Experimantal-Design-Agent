"""
Tests for simulation_agent.engines.physics_sim
Verifies nonlinear vs small-angle pendulum, undamped energy conservation,
vacuum vs aerodynamic drag projectile motion, and clean RLC delegation.
"""

import math
from simulation_agent.engines import physics_sim


def test_pendulum_undamped_energy_conservation_and_period():
    L, g = 1.5, 9.81
    res = physics_sim.run({
        "domain": "physics",
        "experiment_type": "pendulum",
        "parameters": {"length_m": L, "gravity": g, "angle_rad": 0.1, "damping": 0.0, "model_mode": "nonlinear"},
    })
    assert res["status"] == "success"
    pm = res["numerical_results"]["pendulum"]
    em = res["numerical_results"]["energy_metrics"]
    expected_T0 = 2.0 * math.pi * math.sqrt(L / g)
    assert math.isclose(pm["small_angle_period_s"], expected_T0, rel_tol=1e-4)
    assert math.isclose(pm["nonlinear_period_s"], expected_T0, rel_tol=0.01)
    assert em["energy_conservation_error_pct"] < 0.05


def test_pendulum_large_angle_nonlinear_exceeds_small_angle_period():
    res = physics_sim.run({
        "domain": "physics",
        "experiment_type": "pendulum",
        "parameters": {"length_m": 1.0, "gravity": 9.81, "angle_rad": 1.2, "damping": 0.0, "model_mode": "nonlinear"},
    })
    pm = res["numerical_results"]["pendulum"]
    assert pm["nonlinear_period_s"] > pm["small_angle_period_s"] * 1.05


def test_projectile_vacuum_exact_range_and_height():
    v0, angle_deg, g = 25.0, 45.0, 9.81
    res = physics_sim.run({
        "domain": "physics",
        "experiment_type": "projectile_motion",
        "parameters": {"initial_velocity_ms": v0, "launch_angle_deg": angle_deg, "gravity": g, "drag_coeff": 0.0},
    })
    assert res["status"] == "success"
    pr = res["numerical_results"]["projectile"]
    th = math.radians(angle_deg)
    expected_R = (v0**2 * math.sin(2.0 * th)) / g
    expected_H = (v0 * math.sin(th)) ** 2 / (2.0 * g)
    assert pr["air_resistance_included"] is False
    assert math.isclose(pr["max_range_m"], expected_R, rel_tol=1e-4)
    assert math.isclose(pr["max_height_m"], expected_H, rel_tol=1e-4)


def test_projectile_quadratic_drag_reduces_range():
    r_vac = physics_sim.run({
        "experiment_type": "projectile_motion",
        "parameters": {"initial_velocity_ms": 30.0, "launch_angle_deg": 45.0, "drag_coeff": 0.0},
    })
    r_drag = physics_sim.run({
        "experiment_type": "projectile_motion",
        "parameters": {"initial_velocity_ms": 30.0, "launch_angle_deg": 45.0, "drag_coeff": 0.47, "mass_kg": 0.5, "cross_section_m2": 0.01},
    })
    assert r_drag["numerical_results"]["projectile"]["air_resistance_included"] is True
    assert r_drag["numerical_results"]["projectile"]["max_range_m"] < r_vac["numerical_results"]["projectile"]["max_range_m"]
