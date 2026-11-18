"""
Tests for simulation_agent.engines.chem_sim
Includes Part 11.4 Benchmark 6 (4-regime weak-acid/strong-base exact charge-balance titration),
0th/1st/2nd-order reaction kinetics, chemical equilibrium ICE, and top-level experiment_type fix.
"""

import math
from simulation_agent.engines import chem_sim


def test_benchmark_6_weak_acid_titration_four_regimes():
    """Part 11.4 Benchmark 6: 25 mL of 0.1 M CH3COOH (pKa=4.76) titrated with 0.1 M NaOH."""
    res = chem_sim.run({
        "domain": "chemistry",
        "experiment_type": "acid_base_titration",
        "parameters": {
            "acid_concentration_M": 0.1,
            "acid_volume_mL": 25.0,
            "base_concentration_M": 0.1,
            "pKa": 4.76,
        },
    })
    assert res["status"] == "success"
    assert res["experiment_id"] == "acid_base_titration"
    tit = res["numerical_results"]["titration"]

    # Regime 1: Initial pH ~ 2.88 (exact cubic root of [H+]^2 + Ka[H+] - Ka*Ca = 0)
    assert 2.85 <= tit["initial_pH"] <= 2.91
    # Regime 2: Half-equivalence pH == pKa = 4.76
    assert math.isclose(tit["half_equivalence_pH"], 4.76, abs_tol=0.03)
    # Regime 3: Equivalence volume = 25.0 mL, pH ~ 8.72 (basic hydrolysis of acetate)
    assert math.isclose(tit["equivalence_volume_mL"], 25.0, abs_tol=1e-6)
    assert 8.65 <= tit["equivalence_pH"] <= 8.80
    # Regime 4: Charge-balance residual essentially zero
    assert tit["max_charge_balance_residual_M"] < 1e-8


def test_top_level_experiment_type_is_honored_not_ignored():
    """Regression 7: chem_sim must read top-level procedure['experiment_type'], not silently default to kinetics."""
    res = chem_sim.run({
        "domain": "chemistry",
        "experiment_type": "titration",
        "parameters": {"pKa": 4.76, "acid_concentration_M": 0.1, "acid_volume_mL": 25.0, "base_concentration_M": 0.1},
    })
    assert "titration" in res["numerical_results"]
    assert res["experiment_id"] == "acid_base_titration"


def test_first_order_reaction_kinetics_matches_analytical():
    res = chem_sim.run({
        "domain": "chemistry",
        "experiment_type": "reaction_kinetics",
        "parameters": {
            "reaction_order": 1,
            "initial_concentration_M": 1.0,
            "rate_constant_k": 0.05,
            "reaction_time_s": 60.0,
        },
    })
    assert res["status"] == "success"
    kin = res["numerical_results"]["kinetics"]
    assert kin["ode_vs_analytical_max_error_M"] < 1e-4
    assert kin["mass_balance_error_M"] < 1e-6
    assert math.isclose(kin["half_life_s"], math.log(2.0) / 0.05, rel_tol=1e-3)


def test_chemical_equilibrium_mass_action_residual():
    res = chem_sim.run({
        "domain": "chemistry",
        "experiment_type": "chemical_equilibrium",
        "parameters": {"K_eq": 4.0, "initial_A_M": 1.0, "initial_B_M": 1.0},
    })
    assert res["status"] == "success"
    ce = res["numerical_results"]["chemical_equilibrium"]
    assert ce["mass_action_residual"] < 1e-4
    assert ce["mass_balance_error_M"] < 1e-6
