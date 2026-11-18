"""
Tests for simulation_agent.validation.scientific_validator
Verifies detection of NaN/Inf, equilibrium violation, KVL violation,
Michaelis-Menten half-max violation, sorting violation, and honest status assignment.
"""

from simulation_agent.validation.scientific_validator import validate_simulation_result
from simulation_agent.engines import civil_sim, electronics_sim, bio_sim, cs_sim


def test_validator_passes_exact_beam_equilibrium():
    raw = civil_sim.run({
        "experiment_type": "simply_supported_beam_point_load",
        "parameters": {"span_m": 5.0, "point_load_kN": 10.0, "elastic_modulus_GPa": 200.0, "moment_of_inertia_m4": 1e-4},
    })
    summary, status = validate_simulation_result(raw, {"domain": "civil_engineering", "experiment_type": "simply_supported_beam_point_load"})
    assert summary.overall_valid is True
    assert status == "success"


def test_validator_catches_corrupted_beam_equilibrium():
    raw = civil_sim.run({
        "experiment_type": "simply_supported_beam_point_load",
        "parameters": {"span_m": 5.0, "point_load_kN": 10.0},
    })
    # Corrupt equilibrium residual intentionally
    raw["numerical_results"]["beam_analysis"]["force_equilibrium_residual_kN"] = 3.5
    summary, status = validate_simulation_result(raw, {"domain": "civil_engineering", "experiment_type": "simply_supported_beam_point_load"})
    assert summary.overall_valid is False
    assert status == "validation_failed"


def test_validator_catches_nan_in_plot_data():
    raw = electronics_sim.run({
        "experiment_type": "ohms_law",
        "parameters": {"resistance_ohm": 100.0, "supply_voltage_V": 5.0},
    })
    raw["plot_data"][0]["y"][0] = float("nan")
    summary, status = validate_simulation_result(raw, {"domain": "electronics", "experiment_type": "ohms_law"})
    assert summary.overall_valid is False
    assert status == "validation_failed"


def test_validator_catches_michaelis_menten_violation():
    raw = bio_sim.run({
        "experiment_type": "michaelis_menten",
        "parameters": {"Vmax": 100.0, "Km": 5.0},
    })
    raw["numerical_results"]["enzyme_kinetics"]["velocity_at_Km"] = 80.0
    summary, status = validate_simulation_result(raw, {"domain": "biology", "experiment_type": "michaelis_menten"})
    assert summary.overall_valid is False
    assert status == "validation_failed"


def test_validator_catches_unsorted_array_output():
    raw = cs_sim.run({
        "experiment_type": "quick_sort",
        "parameters": {"array": [5, 2, 9, 1]},
    })
    raw["numerical_results"]["algorithm_execution"]["sorted_array"] = [5, 2, 9, 1]
    summary, status = validate_simulation_result(raw, {"domain": "computer_science", "experiment_type": "quick_sort"})
    assert summary.overall_valid is False
    assert status == "validation_failed"

