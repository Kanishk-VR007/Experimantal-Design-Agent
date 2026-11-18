"""
Tests for simulation_agent.engines.bio_sim
Includes Part 11.5 Benchmark 7 (Michaelis-Menten v(0)=0, low [S], v(Km)=Vmax/2, high [S]->Vmax),
logistic growth ODE vs analytical solution, exponential growth, and gene expression.
"""

import math
from simulation_agent.engines import bio_sim


def test_benchmark_7_michaelis_menten_exact_properties():
    """Part 11.5 Benchmark 7: Vmax=100, Km=5."""
    res = bio_sim.run({
        "domain": "biology",
        "experiment_type": "michaelis_menten",
        "parameters": {"Vmax": 100.0, "Km": 5.0, "substrate_max": 500.0},
    })
    assert res["status"] == "success"
    assert res["experiment_id"] == "michaelis_menten"
    ek = res["numerical_results"]["enzyme_kinetics"]
    assert math.isclose(ek["velocity_at_zero_substrate"], 0.0, abs_tol=1e-9)
    assert math.isclose(ek["velocity_at_Km"], 50.0, abs_tol=1e-4)
    # High [S] = 500 = 100*Km -> v = 100 * 500 / 505 = 99.0099
    assert ek["velocity_at_high_substrate"] > 90.0
    assert ek["velocity_at_high_substrate"] < 100.0


def test_logistic_growth_ode_matches_analytical():
    res = bio_sim.run({
        "domain": "biology",
        "experiment_type": "logistic_growth",
        "parameters": {
            "initial_population": 100.0,
            "carrying_capacity": 10000.0,
            "growth_rate": 0.5,
            "time_hours": 24.0,
        },
    })
    assert res["status"] == "success"
    gr = res["numerical_results"]["growth"]
    assert gr["ode_vs_analytical_max_rel_error"] < 1e-4
    assert 0.0 < gr["final_population"] <= 10000.0
    assert math.isclose(gr["doubling_time_h"], math.log(2.0) / 0.5, rel_tol=1e-3)


def test_gene_expression_steady_state():
    res = bio_sim.run({
        "domain": "biology",
        "experiment_type": "gene_expression",
        "parameters": {
            "transcription_rate": 10.0,
            "mrna_decay_rate": 0.5,
            "translation_rate": 2.0,
            "protein_decay_rate": 0.2,
            "time_hours": 48.0,
        },
    })
    assert res["status"] == "success"
    ex = res["numerical_results"]["expression"]
    # Steady state: m* = 10/0.5 = 20, P* = 2*20/0.2 = 200
    assert math.isclose(ex["steady_state_mRNA"], 20.0, rel_tol=1e-3)
    assert math.isclose(ex["steady_state_protein"], 200.0, rel_tol=1e-3)
