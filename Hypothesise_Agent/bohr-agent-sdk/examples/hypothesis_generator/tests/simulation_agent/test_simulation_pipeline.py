"""
End-to-End Simulation Pipeline & Part 12 Mandatory Regression Suite
Covers all 12 regressions from Part 12 plus LM Studio 3-model configuration integrity.
"""

import math
from simulation_agent.agent import run_simulation
from backend.services.local_model_manager import (
    PROMPT_REFINER_MODEL_KEY,
    VISION_MODEL_KEY,
    MAIN_MODEL_KEY,
    ROLE_CONFIG,
    MAX_ACTIVE_MODELS,
)


def test_regression_01_point_load_beam_exact_and_no_udl_hijack():
    out = run_simulation({"topic": "5 m simply supported beam with 10 kN central point load", "design": ""})
    assert out["experiment_id"] == "simply_supported_beam_point_load"
    ba = out["numerical_results"]["beam_analysis"]
    assert math.isclose(ba["reaction_A_kN"], 5.0, abs_tol=1e-6)
    assert math.isclose(ba["reaction_B_kN"], 5.0, abs_tol=1e-6)
    assert math.isclose(ba["max_bending_moment_kNm"], 12.5, abs_tol=1e-6)
    assert ba["deflection_computed"] is False
    assert out["confidence_score"] is None


def test_regression_02_udl_beam_exact_distinct_from_point_load():
    out = run_simulation({"topic": "5 m simply supported beam with 10 kN/m uniformly distributed load", "design": ""})
    assert out["experiment_id"] == "simply_supported_beam_udl"
    ba = out["numerical_results"]["beam_analysis"]
    assert math.isclose(ba["reaction_A_kN"], 25.0, abs_tol=1e-6)
    assert math.isclose(ba["reaction_B_kN"], 25.0, abs_tol=1e-6)
    assert math.isclose(ba["max_bending_moment_kNm"], 31.25, abs_tol=1e-6)


def test_regression_03_four_bar_linkage_never_falls_back_to_otto_cycle():
    out = run_simulation({
        "topic": "Four-bar linkage mechanism with crank 1m coupler 2.5m rocker 2m ground 3m",
        "design": "",
    })
    assert out["experiment_id"] == "four_bar_linkage"
    assert out["simulation_status"] == "success"
    assert "four_bar_linkage" in out["numerical_results"]
    assert "otto_cycle" not in out["numerical_results"]
    assert out["visualization"]["template"] == "four_bar_linkage"
    assert out["visualization"]["scene_valid"] is True


def test_regression_04_series_rlc_never_gets_pendulum_scene():
    out = run_simulation({"topic": "Series RLC circuit R=10 ohm L=0.1 H C=0.001 F", "design": ""})
    assert out["experiment_id"] == "series_rlc"
    assert out["simulation_status"] == "success"
    assert out["visualization"]["template"] == "rlc_circuit"
    assert out["visualization_spec"]["scene_template"] == "rlc_circuit"


def test_regression_05_bfs_executes_real_bfs_not_complexity_or_dijkstra():
    out = run_simulation({"topic": "Breadth-first search graph traversal", "design": ""})
    assert out["experiment_id"] == "breadth_first_search"
    assert out["simulation_status"] == "success"
    ae = out["numerical_results"]["algorithm_execution"]
    assert ae["algorithm"] == "breadth_first_search"
    assert len(ae["traversal_order"]) >= 4
    assert out["visualization"]["template"] == "graph_traversal"


def test_regression_06_quicksort_executes_real_sort():
    out = run_simulation({
        "topic": "QuickSort sorting algorithm on integer array",
        "design": "",
        "parameters": {"array": [42, 7, 19, 3, 25, 11]},
    })
    assert out["experiment_id"] == "quick_sort"
    assert out["numerical_results"]["algorithm_execution"]["sorted_array"] == [3, 7, 11, 19, 25, 42]
    assert out["visualization"]["template"] == "sorting_array"


def test_regression_07_chemistry_titration_not_silently_kinetics():
    out = run_simulation({"topic": "Weak acid titration of acetic acid pKa=4.76 with NaOH", "design": ""})
    assert out["experiment_id"] == "acid_base_titration"
    assert "titration" in out["numerical_results"]
    assert out["visualization"]["template"] == "titration_apparatus"


def test_regression_08_biology_routed_and_validated():
    out = run_simulation({"topic": "Michaelis-Menten enzyme kinetics Vmax=100 Km=5", "design": ""})
    assert out["domain"] == "biology"
    assert out["experiment_id"] == "michaelis_menten"
    assert out["simulation_status"] == "success"
    assert out["visualization"]["template"] == "enzyme_kinetics"


def test_regression_09_truss_uses_truss_scene_not_beam():
    out = run_simulation({"topic": "Pratt bridge truss analysis with 10m span and 20 kN load", "design": ""})
    assert out["experiment_id"] == "truss_analysis"
    assert out["visualization"]["template"] == "truss_structure"
    assert out["visualization_spec"]["scene_template"] == "truss_structure"


def test_regression_10_shaft_uses_shaft_scene_not_beam():
    out = run_simulation({"topic": "Circular shaft torsion and shear stress analysis", "design": ""})
    assert out["experiment_id"] == "shaft_design"
    assert out["visualization"]["template"] == "shaft_torsion"


def test_regression_11_no_student_t_ci_or_fabricated_confidence():
    out = run_simulation({"topic": "Simple pendulum 1.5m oscillation", "design": ""})
    assert out["confidence_score"] is None
    assert "ci_95_lower" not in out["numerical_results"].get("statistical_summary", {})
    assert not any("95% ci" in o.lower() for o in out["observations"])


def test_regression_12_unsupported_experiment_honest_no_fabrication():
    out = run_simulation({"topic": "Quantum chromodynamics lattice gauge simulation", "design": ""})
    assert out["simulation_status"] == "unsupported"
    assert out["plot_data"] == []
    assert out["visualization_spec"] is None
    assert out["confidence_score"] is None


def test_regression_13_llm_generated_equations_never_bypass_scientific_validation():
    """Part 12 Regression 12: LLM-generated equation/dynamic outputs MUST pass through ScientificValidator."""
    from simulation_agent.output_formatter import format_output

    # Simulated LLM-generated dynamic output containing a NaN value
    corrupted_dynamic_raw = {
        "status": "success",
        "engine_used": "dynamic_equation_engine",
        "generation_method": "equation_model",
        "numerical_results": {"primary_metrics": {"peak_value": float("nan")}},
        "plot_data": [
            {
                "plot_type": "line",
                "title": "LLM Synthesized Curve",
                "x_label": "x",
                "y_label": "y",
                "x": [0.0, 1.0, 2.0, 3.0],
                "y": [0.0, float("nan"), 2.0, 3.0],
            }
        ],
        "observations": ["Synthesized curve"],
    }
    formatted = format_output(
        corrupted_dynamic_raw,
        {"domain": "physics", "experiment_type": "dynamic_custom", "hypothesis": "Test LLM validation"},
    ).model_dump()
    assert formatted["simulation_status"] == "validation_failed"
    assert formatted["validation"]["passed"] is False
    assert formatted["confidence_score"] is None


def test_lm_studio_three_model_exact_keys_and_policies():
    assert PROMPT_REFINER_MODEL_KEY == "qwen/qwen3-4b-thinking-2507"
    assert VISION_MODEL_KEY == "qwen3-vl-4b-thinking"
    assert MAIN_MODEL_KEY == "deepseek/deepseek-r1-0528-qwen3-8b"
    assert MAX_ACTIVE_MODELS == 1
    assert ROLE_CONFIG["vision_analyzer"]["requires_vision"] is True
    assert ROLE_CONFIG["main_reasoner"]["reasoning_only"] is True
    assert ROLE_CONFIG["main_reasoner"]["supports_tools"] is False

