"""
Tests for simulation_agent.engines.mech_sim
Includes Part 11.2 Benchmarks 3 & 4 (four-bar linkage vector-loop closure,
Grashof check, impossible linkage rejection, spur gear ratio, Carnot vs Otto vs Diesel vs Brayton,
spring-mass-damper, shaft torsion).
"""

import math
import pytest
from simulation_agent.engines import mech_sim


def test_benchmark_3_four_bar_linkage_kinematic_closure():
    """Part 11.2 Benchmark 3: Grashof crank-rocker (d=3, a=1, b=2.5, c=2)."""
    res = mech_sim.run({
        "domain": "mechanical_engineering",
        "experiment_type": "four_bar_linkage",
        "parameters": {
            "ground_length_m": 3.0,
            "crank_length_m": 1.0,
            "coupler_length_m": 2.5,
            "rocker_length_m": 2.0,
            "rpm": 30.0,
            "assembly_mode": "open",
        },
    })
    assert res["status"] == "success"
    fb = res["numerical_results"]["four_bar_linkage"]
    assert fb["is_grashof"] is True
    assert fb["full_crank_rotation"] is True
    assert fb["max_closure_residual_m"] < 1e-6
    assert fb["max_link_length_error_m"] < 1e-6
    assert fb["valid_steps"] >= 24

    # Verify every frame preserves exact link lengths
    for fr in res["numerical_results"]["kinematic_trajectory"]["joint_positions"]:
        A, B, C, D = fr["A"], fr["B"], fr["C"], fr["D"]
        assert math.isclose(math.hypot(B[0] - A[0], B[1] - A[1]), 1.0, abs_tol=1e-5)
        assert math.isclose(math.hypot(C[0] - B[0], C[1] - B[1]), 2.5, abs_tol=1e-5)
        assert math.isclose(math.hypot(C[0] - D[0], C[1] - D[1]), 2.0, abs_tol=1e-5)


def test_four_bar_impossible_geometry_rejected():
    res = mech_sim.run({
        "domain": "mechanical_engineering",
        "experiment_type": "four_bar_linkage",
        "parameters": {
            "ground_length_m": 10.0,
            "crank_length_m": 1.0,
            "coupler_length_m": 1.0,
            "rocker_length_m": 1.0,
        },
    })
    assert res["status"] == "failed"


def test_benchmark_4_gear_train_exact_ratio_and_torque():
    """Part 11.2 Benchmark 4: N1=20, N2=60, 1800 RPM, 5 kW -> i=3.0, RPM_out=600, torque balance."""
    res = mech_sim.run({
        "domain": "mechanical_engineering",
        "experiment_type": "gear_train",
        "parameters": {
            "teeth_driver": 20,
            "teeth_driven": 60,
            "module_mm": 2.5,
            "rpm_input": 1800.0,
            "power_kW": 5.0,
        },
    })
    assert res["status"] == "success"
    gt = res["numerical_results"]["gear_train"]
    assert math.isclose(gt["gear_ratio_numeric"], 3.0, abs_tol=1e-6)
    assert math.isclose(gt["rpm_output"], 600.0, abs_tol=1e-6)
    expected_t_in = 5000.0 / (1800.0 * 2.0 * math.pi / 60.0)
    assert math.isclose(gt["torque_input_Nm"], expected_t_in, rel_tol=1e-3)
    assert math.isclose(gt["torque_output_Nm"], gt["torque_input_Nm"] * 3.0 * gt["efficiency"], rel_tol=1e-3)


def test_carnot_cycle_exact_efficiency():
    res = mech_sim.run({
        "domain": "mechanical_engineering",
        "experiment_type": "carnot_cycle",
        "parameters": {"T_hot_K": 1200.0, "T_cold_K": 300.0},
    })
    assert res["status"] == "success"
    cc = res["numerical_results"]["carnot_cycle"]
    assert math.isclose(cc["efficiency_percent"], 75.0, abs_tol=1e-4)


def test_otto_diesel_brayton_distinct_solvers():
    r_otto = mech_sim.run({"experiment_type": "otto_cycle", "parameters": {"compression_ratio": 8.0, "gamma": 1.4}})
    r_diesel = mech_sim.run({"experiment_type": "diesel_cycle", "parameters": {"compression_ratio": 16.0, "cutoff_ratio": 2.0, "gamma": 1.4}})
    r_brayton = mech_sim.run({"experiment_type": "brayton_cycle", "parameters": {"pressure_ratio": 10.0, "gamma": 1.4}})
    expected_otto = (1.0 - 8.0 ** (-0.4)) * 100.0
    expected_brayton = (1.0 - 10.0 ** (-0.4 / 1.4)) * 100.0
    assert math.isclose(r_otto["numerical_results"]["otto_cycle"]["efficiency_percent"], expected_otto, abs_tol=0.05)
    assert math.isclose(r_brayton["numerical_results"]["brayton_cycle"]["efficiency_percent"], expected_brayton, abs_tol=0.05)
    assert r_diesel["numerical_results"]["diesel_cycle"]["efficiency_percent"] > 50.0


def test_spring_mass_damper_natural_frequency_and_damping():
    res = mech_sim.run({
        "experiment_type": "spring_mass_damper",
        "parameters": {"mass_kg": 1.0, "stiffness_N_m": 100.0, "damping_Ns_m": 2.0, "initial_displacement_m": 0.1},
    })
    assert res["status"] == "success"
    smd = res["numerical_results"]["spring_mass_damper"]
    assert math.isclose(smd["natural_frequency_Hz"], 10.0 / (2.0 * math.pi), rel_tol=1e-3)
    assert math.isclose(smd["damping_ratio_zeta"], 0.1, rel_tol=1e-4)


def test_shaft_design_torsion_shear_stress():
    T, d_mm = 200.0, 40.0
    res = mech_sim.run({
        "experiment_type": "shaft_design",
        "parameters": {"torque_Nm": T, "bending_moment_Nm": 0.0, "diameter_mm": d_mm, "length_mm": 500.0},
    })
    sd = res["numerical_results"]["shaft_design"]
    r = (d_mm / 1000.0) / 2.0
    J = math.pi * (d_mm / 1000.0) ** 4 / 32.0
    expected_tau_MPa = (T * r / J) / 1e6
    assert math.isclose(sd["max_shear_stress_MPa"], expected_tau_MPa, rel_tol=1e-3)
