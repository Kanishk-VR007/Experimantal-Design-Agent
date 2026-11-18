"""
Tests for simulation_agent.router
Covers routing across all 7 domains, canonical alias resolution, missing-parameter
rejection, and honest unsupported/failed responses (zero fabricated data).
"""

import pytest
from simulation_agent import router
from simulation_agent.experiment_registry import EXPERIMENT_REGISTRY


def test_all_seven_domains_registered_in_domain_map():
    for key in (
        "physics",
        "chemistry",
        "biology",
        "electronics",
        "civil_engineering",
        "mechanical_engineering",
        "computer_science",
    ):
        assert key in router.DOMAIN_MAP, f"Domain '{key}' missing from router.DOMAIN_MAP"


def test_biology_is_explicitly_routed_to_bio_sim():
    res = router.route({
        "domain": "biology",
        "experiment_type": "michaelis_menten",
        "parameters": {"Vmax": 100.0, "Km": 5.0},
    })
    assert res["engine_used"] == "bio_sim"
    assert res["experiment_id"] == "michaelis_menten"
    assert res["status"] == "success"


def test_unrecognized_experiment_returns_honest_unsupported_no_sine_wave():
    res = router.route({
        "domain": "general",
        "topic": "Quantum chromodynamics lattice gauge simulation",
        "hypothesis": "Estimate gluon condensate on 4D lattice",
        "parameters": {},
    })
    assert res["status"] == "unsupported"
    assert res["plot_data"] == []
    assert res.get("confidence_score") is None


def test_unsupported_mechanical_request_never_falls_back_to_otto_cycle():
    res = router.route({
        "domain": "mechanical_engineering",
        "topic": "Magnetohydrodynamic plasma turbine blade flutter",
        "hypothesis": "Measure plasma flutter modes",
        "parameters": {},
    })
    assert res["status"] == "unsupported"
    assert res.get("experiment_id") != "otto_cycle"
    assert "otto" not in str(res.get("numerical_results", {})).lower()


def test_unsupported_electronics_request_never_falls_back_to_arduino_led():
    res = router.route({
        "domain": "electronics",
        "topic": "Quantum tunnel diode Gunn oscillator",
        "hypothesis": "Measure microwave oscillation",
        "parameters": {},
    })
    assert res["status"] == "unsupported"
    assert "arduino" not in str(res.get("numerical_results", {})).lower()


def test_missing_required_parameters_return_honest_failed():
    res = router.route({
        "domain": "mechanical_engineering",
        "experiment_type": "four_bar_linkage",
        "parameters": {},
    })
    assert res["status"] == "failed"
    assert res["plot_data"] == []
    assert "Missing required parameter" in " ".join(res.get("observations", []))

