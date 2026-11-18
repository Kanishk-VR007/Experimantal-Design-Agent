"""
Tests for simulation_agent.engines.electronics_sim
Includes Part 11.3 Benchmark 5 (Series RLC resonance, damping ratio, KVL residual),
Ohm's law, voltage/current dividers, RC/RL transients, AC phasors, and transformer.
"""

import math
from simulation_agent.engines import electronics_sim


def test_benchmark_5_series_rlc_resonance_and_kvl():
    """Part 11.3 Benchmark 5: R=10 Ohm, L=0.1 H, C=1 mF, V=5 V."""
    R, L, C, V = 10.0, 0.1, 0.001, 5.0
    res = electronics_sim.run({
        "domain": "electronics",
        "experiment_type": "series_rlc",
        "parameters": {"resistance_ohm": R, "inductance_H": L, "capacitance_F": C, "voltage_V": V},
    })
    assert res["status"] == "success"
    rlc = res["numerical_results"]["rlc"]
    expected_f0 = 1.0 / (2.0 * math.pi * math.sqrt(L * C))
    expected_zeta = (R / 2.0) * math.sqrt(C / L)
    assert math.isclose(rlc["resonant_frequency_Hz"], expected_f0, rel_tol=1e-4)
    assert math.isclose(rlc["damping_ratio_zeta"], expected_zeta, rel_tol=1e-4)
    assert rlc["response_type"] == "underdamped"
    assert rlc["kvl_residual_V"] < 0.01  # < 0.2% of 5V supply
    assert rlc["ode_vs_analytical_max_error_A"] < 1e-4


def test_ohms_law_exact_and_power_balance():
    res = electronics_sim.run({
        "experiment_type": "ohms_law",
        "parameters": {"resistance_ohm": 250.0, "supply_voltage_V": 10.0},
    })
    assert res["status"] == "success"
    ol = res["numerical_results"]["ohms_law"]
    assert math.isclose(ol["max_current_mA"], 40.0, rel_tol=1e-6)
    assert math.isclose(ol["max_power_mW"], 400.0, rel_tol=1e-6)
    assert abs(ol["power_balance_error_W"]) < 1e-9


def test_voltage_divider_and_current_divider_exact():
    rv = electronics_sim.run({
        "experiment_type": "voltage_divider",
        "parameters": {"supply_voltage_V": 12.0, "r1_ohm": 1000.0, "r2_ohm": 3000.0},
    })
    vd = rv["numerical_results"]["voltage_divider"]
    assert math.isclose(vd["Vout_V"], 9.0, rel_tol=1e-6)
    assert abs(vd["kvl_residual_V"]) < 1e-9

    rc = electronics_sim.run({
        "experiment_type": "current_divider",
        "parameters": {"total_current_A": 3.0, "r1_ohm": 10.0, "r2_ohm": 20.0},
    })
    cd = rc["numerical_results"]["current_divider"]
    assert math.isclose(cd["I1_A"], 2.0, rel_tol=1e-6)
    assert math.isclose(cd["I2_A"], 1.0, rel_tol=1e-6)
    assert abs(cd["kcl_residual_A"]) < 1e-9


def test_rc_and_rl_time_constants():
    r_rc = electronics_sim.run({
        "experiment_type": "rc_circuit",
        "parameters": {"resistance_ohm": 1000.0, "capacitance_F": 1e-3, "supply_voltage_V": 5.0},
    })
    rc = r_rc["numerical_results"]["rc_circuit"]
    assert math.isclose(rc["time_constant_s"], 1.0, rel_tol=1e-6)
    assert math.isclose(rc["voltage_at_1tau_V"], 5.0 * (1.0 - math.exp(-1.0)), rel_tol=1e-3)

    r_rl = electronics_sim.run({
        "experiment_type": "rl_circuit",
        "parameters": {"resistance_ohm": 10.0, "inductance_H": 0.5, "supply_voltage_V": 10.0},
    })
    rl = r_rl["numerical_results"]["rl_circuit"]
    assert math.isclose(rl["time_constant_s"], 0.05, rel_tol=1e-6)
    assert math.isclose(rl["steady_state_current_A"], 1.0, rel_tol=1e-6)
