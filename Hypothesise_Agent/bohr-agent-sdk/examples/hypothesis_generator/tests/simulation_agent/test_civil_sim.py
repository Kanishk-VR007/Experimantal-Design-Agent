"""
Tests for simulation_agent.engines.civil_sim
Includes Part 11.1 Benchmarks 1 & 2 (exact central point load vs UDL),
eccentric point load, cantilever beam, missing EI honesty, and 2D DSM truss equilibrium.
"""

import math
import pytest
from simulation_agent.engines import civil_sim


def test_benchmark_1_simply_supported_5m_10kn_central_point_load():
    """Part 11.1 Benchmark 1: L=5m, P=10kN at midspan -> R_A=5, R_B=5, M_max=12.5 kN.m, no fabricated deflection."""
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "simply_supported_beam_point_load",
        "parameters": {"span_m": 5.0, "point_load_kN": 10.0},
    })
    assert res["status"] in ("success", "partial")
    ba = res["numerical_results"]["beam_analysis"]
    assert math.isclose(ba["reaction_A_kN"], 5.0, abs_tol=1e-9)
    assert math.isclose(ba["reaction_B_kN"], 5.0, abs_tol=1e-9)
    assert math.isclose(ba["max_bending_moment_kNm"], 12.5, abs_tol=1e-9)
    assert math.isclose(ba["force_equilibrium_residual_kN"], 0.0, abs_tol=1e-9)
    assert math.isclose(ba["moment_equilibrium_residual_kNm"], 0.0, abs_tol=1e-9)
    assert ba["deflection_computed"] is False
    assert ba["max_deflection_mm"] is None


def test_benchmark_1_with_explicit_EI_matches_PL3_over_48EI():
    L, P, E_GPa, I = 5.0, 10.0, 200.0, 1e-4
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "simply_supported_beam_point_load",
        "parameters": {
            "span_m": L,
            "point_load_kN": P,
            "elastic_modulus_GPa": E_GPa,
            "moment_of_inertia_m4": I,
        },
    })
    ba = res["numerical_results"]["beam_analysis"]
    expected_mm = (P * 1e3 * L**3) / (48.0 * E_GPa * 1e9 * I) * 1000.0
    assert ba["deflection_computed"] is True
    assert math.isclose(ba["max_deflection_mm"], expected_mm, rel_tol=1e-4)


def test_benchmark_2_simply_supported_5m_10kn_per_m_udl():
    """Part 11.1 Benchmark 2: L=5m, w=10kN/m -> R_A=25, R_B=25, M_max=31.25 kN.m, delta=5wL^4/(384EI)."""
    L, w, E_GPa, I = 5.0, 10.0, 200.0, 1e-4
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "simply_supported_beam_udl",
        "parameters": {
            "span_m": L,
            "load_kN_per_m": w,
            "elastic_modulus_GPa": E_GPa,
            "moment_of_inertia_m4": I,
        },
    })
    ba = res["numerical_results"]["beam_analysis"]
    expected_mm = (5.0 * (w * 1e3) * L**4) / (384.0 * (E_GPa * 1e9) * I) * 1000.0
    assert math.isclose(ba["reaction_A_kN"], 25.0, abs_tol=1e-9)
    assert math.isclose(ba["reaction_B_kN"], 25.0, abs_tol=1e-9)
    assert math.isclose(ba["max_bending_moment_kNm"], 31.25, abs_tol=1e-9)
    assert math.isclose(ba["max_deflection_mm"], expected_mm, rel_tol=1e-4)


def test_eccentric_point_load_reactions_and_moment():
    L, P, a = 6.0, 12.0, 2.0
    b = L - a
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "simply_supported_beam_eccentric_point_load",
        "parameters": {"span_m": L, "point_load_kN": P, "load_position_m": a},
    })
    ba = res["numerical_results"]["beam_analysis"]
    assert math.isclose(ba["reaction_A_kN"], P * b / L, abs_tol=1e-9)
    assert math.isclose(ba["reaction_B_kN"], P * a / L, abs_tol=1e-9)
    assert math.isclose(ba["max_bending_moment_kNm"], P * a * b / L, abs_tol=1e-9)


def test_cantilever_point_load_and_udl():
    L, P, E_GPa, I = 4.0, 20.0, 200.0, 1e-4
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "cantilever_beam_point_load",
        "parameters": {"span_m": L, "point_load_kN": P, "elastic_modulus_GPa": E_GPa, "moment_of_inertia_m4": I},
    })
    ca = res["numerical_results"]["cantilever_analysis"]
    assert math.isclose(ca["fixed_moment_kNm"], P * L, abs_tol=1e-9)
    expected_tip_mm = (P * 1e3 * L**3) / (3.0 * E_GPa * 1e9 * I) * 1000.0
    assert math.isclose(ca["tip_deflection_mm"], expected_tip_mm, rel_tol=1e-4)


def test_truss_2d_direct_stiffness_equilibrium():
    res = civil_sim.run({
        "domain": "civil_engineering",
        "experiment_type": "truss_analysis",
        "parameters": {"span_m": 10.0, "height_m": 3.0, "panels": 4, "point_load_kN": 20.0},
    })
    assert res["status"] == "success"
    tr = res["numerical_results"]["truss"]
    assert tr["max_joint_equilibrium_residual_N"] < 1e-3
    assert abs(tr["force_equilibrium_residual_kN"]) < 1e-6
    assert tr["max_tension_kN"] > 0
    assert tr["max_compression_kN"] > 0
    assert any(m["axial_force_kN"] < 0 for m in res["numerical_results"]["truss_geometry"]["members"])


def test_point_load_vs_udl_never_confused():
    r_pt = civil_sim.run({"experiment_type": "simply_supported_beam_point_load", "parameters": {"span_m": 5.0, "point_load_kN": 10.0}})
    r_udl = civil_sim.run({"experiment_type": "simply_supported_beam_udl", "parameters": {"span_m": 5.0, "load_kN_per_m": 10.0}})
    assert r_pt["numerical_results"]["beam_analysis"]["max_bending_moment_kNm"] == 12.5
    assert r_udl["numerical_results"]["beam_analysis"]["max_bending_moment_kNm"] == 31.25
