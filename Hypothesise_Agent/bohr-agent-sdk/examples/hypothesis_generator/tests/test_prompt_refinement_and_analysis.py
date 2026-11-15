"""
Automated Verification Suite: Token Filtering, Qwen Prompt Refinement & L4 Analysis Accuracy
=========================================================================================
Validates:
1. Token filtering & scientific stop-word removal (preserves numeric units & scientific operators)
2. Context compression & keyword ranking across topic + literature abstracts
3. Prompt construction for OREAL DeepSeek-R1-Distill-Qwen-7B
4. Cross-domain L4 statistical post-processing (95% CI, regression, derivative sensitivity, >= 3-4 plots)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_agent.prompt_refiner import (
    filter_tokens,
    filter_and_compress_context,
    build_deepseek_messages,
)
from simulation_agent.agent import run_simulation, extract_procedure_from_text
from simulation_agent.dynamic_sim import (
    SandboxExecutionRunner,
    _normalize_and_validate_plots,
    _build_prefill_header,
    evaluate_equation_model,
    _safe_eval_expr,
)
from simulation_agent.visualization.templates.chemistry_templates import build_molecule_scene


def test_token_filtering_and_stopword_removal():
    sample = (
        "In this paper, we investigate the effect of varying the length of a simple pendulum "
        "to 1.5m under g = 9.81 m/s^2 when air damping is not negligible [1, 2] https://example.com"
    )
    res = filter_tokens(sample)
    tokens_low = [t.lower() for t in res["filtered_tokens"]]

    assert res["raw_token_count"] > res["filtered_token_count"]
    assert res["removed_stopwords_count"] >= 6
    assert res["reduction_pct"] > 20.0
    # Preserves numeric units & scientific relational operators
    assert "1.5m" in tokens_low
    assert "9.81" in tokens_low
    assert "pendulum" in tokens_low
    assert "not" in tokens_low
    assert "under" in tokens_low
    # Removes URLs & citation brackets & stop words
    assert "https" not in tokens_low
    assert "the" not in tokens_low


def test_context_compression_with_papers():
    papers = [
        {
            "title": "Harmonic Period Scaling in Rigid Pendulums",
            "abstract": "We show that for small angles T = 2*pi*sqrt(L/g). Length L=1.5m yields 2.46s.",
        },
        {
            "title": "Damping Effects in Oscillators",
            "abstract": "Viscous drag causes exponential amplitude decay without shifting frequency significantly.",
        },
    ]
    ctx = filter_and_compress_context("Simple pendulum length 1.5m oscillation", papers)
    assert ctx["stats"]["removed_stopwords_count"] > 0
    assert len(ctx["compressed_papers"]) == 2
    assert len(ctx["top_keywords"]) >= 5
    assert "pendulum" in [k.lower() for k in ctx["top_keywords"]]


def test_deepseek_prompt_structure():
    refinement = {
        "domain": "physics",
        "experiment_type": "pendulum",
        "refined_objective": "Verify T = 2*pi*sqrt(L/g) for L=1.5m",
        "parameters": {"length_m": 1.5, "gravity": 9.81},
        "independent_vars": ["length_m"],
        "dependent_vars": ["natural_period_s"],
        "control_vars": ["gravity", "angle_rad"],
        "equations": ["T = 2*pi*sqrt(L/g)"],
        "compressed_papers": ["[P1] Pendulum Scaling | Core finding: L=1.5m -> 2.46s"],
        "top_keywords": ["pendulum", "1.5m", "period"],
        "refined_prompt": "Design pendulum length experiment.",
    }
    msgs = build_deepseek_messages("Simple Pendulum 1.5m", refinement)
    assert len(msgs) == 2
    assert "## 5. DATA ANALYSIS PLAN" in msgs[0]["content"]
    assert "Verify T = 2*pi*sqrt(L/g)" in msgs[1]["content"]


def test_cross_domain_analysis_depth():
    cases = [
        ("physics", "Simple pendulum 1.5m oscillation", "## 1. HYPOTHESIS\nIf L increases then period increases.\n## 2. VARIABLES\nL=1.5m"),
        ("chemistry", "Reaction kinetics Arrhenius temperature effect", "## 1. HYPOTHESIS\nIf temperature increases then rate constant k increases.\n## 2. VARIABLES\nT=298K"),
        ("biology", "Bacterial population logistic growth curve", "## 1. HYPOTHESIS\nIf nutrients saturate then growth plateaus.\n## 2. VARIABLES\nr=0.5"),
        ("computer_science", "Compare CNN vs Transformer on CIFAR-10", "## 1. HYPOTHESIS\nTransformer achieves higher accuracy than CNN.\n## 2. VARIABLES\nepochs=50"),
        ("civil_engineering", "Simply supported steel beam under load", "## 1. HYPOTHESIS\nIf load increases then beam deflection increases.\n## 2. VARIABLES\nspan=6m"),
    ]
    for expected_domain, topic, design in cases:
        sim = run_simulation({"topic": topic, "design": design})
        assert sim["domain"] == expected_domain, f"Domain mismatch for {topic}: {sim['domain']}"
        assert "statistical_summary" in sim["numerical_results"], f"Missing statistical_summary in {expected_domain}"
        assert "model_validation" in sim["numerical_results"], f"Missing model_validation in {expected_domain}"
        assert len(sim["numerical_results"]) >= 3, f"Too few numerical metrics in {expected_domain}: {list(sim['numerical_results'].keys())}"
        assert len(sim["plot_data"]) >= 3, f"Too few plots in {expected_domain}: {len(sim['plot_data'])}"
        assert len(sim["observations"]) >= 4, f"Too few observations in {expected_domain}"
        assert len(sim["simulation_log"]) >= 6, f"Too few log entries in {expected_domain}"


def test_word_boundary_novel_experiment_routing():
    """Verify 'controlled' never hits 'led' and novel experiments route cleanly to dynamic_custom."""
    sg = extract_procedure_from_text(
        "Controlled mechanical test measuring Wheatstone bridge strain gauge voltage under axial stress.",
        "strain gauge principle",
    )
    assert sg["domain"] == "mechanical_engineering", f"Unexpected domain: {sg['domain']}"
    assert sg["experiment_type"] == "dynamic_custom", f"Unexpected type: {sg['experiment_type']}"

    ni = extract_procedure_from_text(
        "Controlled synthesis reacting Nickel with chlorine gas to produce NiCl2.",
        "Nickel when reacted with chlorium",
    )
    assert ni["domain"] == "chemistry", f"Unexpected domain: {ni['domain']}"
    assert ni["experiment_type"] == "dynamic_custom", f"Unexpected type: {ni['experiment_type']}"

    # Explicit electronics LED circuits must still route cleanly to electronics
    led = extract_procedure_from_text(
        "Drive an Arduino blinking LED with a 220 ohm resistor.",
        "Arduino LED Blink Circuit",
    )
    assert led["domain"] == "electronics", f"Expected electronics, got {led['domain']}"


def test_dynamic_sandbox_and_plot_validation():
    """Verify SandboxExecutionRunner blocks unsafe builtins and _normalize_and_validate_plots validates dense 3-plot outputs."""
    runner = SandboxExecutionRunner()

    # Unsafe builtin 'open' must be blocked
    try:
        runner.run("f = open('test.txt', 'w')\nsimulation_results = {}")
        assert False, "Sandbox should block open()"
    except RuntimeError:
        pass

    # Infinite loops / stiff ODE hangs must be terminated by OS subprocess timeout
    try:
        runner.run("while True:\n    pass\nsimulation_results = {}", timeout=2)
        assert False, "Sandbox should terminate hanging loops on timeout"
    except RuntimeError as exc:
        assert "timed out" in str(exc).lower()

    prefill = _build_prefill_header({"gauge_factor": 2.1, "nominal_resistance_ohm": 120.0, "excitation_voltage_V": 5.0})
    code = prefill + """
strain = np.linspace(-0.002, 0.002, N)
v_quarter = excitation_voltage_V * (gauge_factor * strain) / (4.0 + 2.0 * gauge_factor * strain)
v_full = excitation_voltage_V * gauge_factor * strain
dR = nominal_resistance_ohm * gauge_factor * strain
gfs = np.linspace(1.5, 3.0, N)
sens = excitation_voltage_V * gfs * 0.001 / 4.0
simulation_results = {
    "numerical_results": {"primary_metrics": {"peak_mV": float(np.max(v_full) * 1000.0)}},
    "plots": [
        make_plot("Bridge Output vs Strain", "Strain", "Voltage (V)", strain, v_quarter, "Quarter Bridge", extra=[("Full Bridge", v_full, "#10b981")]),
        make_plot("Resistance Change vs Strain", "Strain", "Delta R (Ohm)", strain, dR, "Delta R"),
        make_plot("Gauge Factor Sensitivity", "Gauge Factor", "Output at 1000 ustrain (V)", gfs, sens, "Sensitivity"),
    ],
    "observations": ["Quarter-bridge voltage responds linearly across microstrain range."]
}
"""
    res = runner.run(code)
    num, plots, obs = _normalize_and_validate_plots(res, "strain gauge principle", min_plots=3, min_curve_points=15)
    assert len(plots) == 3
    assert all(len(p["x"]) == 100 and len(p["y"]) == 100 for p in plots)
    assert plots[0]["extra_series"] and len(plots[0]["extra_series"][0]["y"]) == 100

    # Sparse 1-plot / 5-pt script must be rejected under Attempt 1 strict thresholds
    try:
        _normalize_and_validate_plots(
            {"plots": [{"plot_type": "line", "title": "Sparse", "x": [0, 1, 2, 3, 4], "y": [0, 2, 4, 6, 8]}]},
            "sparse test",
            min_plots=3,
            min_curve_points=15,
        )
        assert False, "Sparse 5-pt single plot should fail strict Attempt 1 check"
    except ValueError:
        pass


def test_nickel_chloride_3d_molecule_selection():
    """Verify NiCl2 molecular geometry and Nickel CPK node rendering."""
    spec = build_molecule_scene(
        {"domain": "chemistry", "hypothesis": "Nickel reacts with chlorine gas forming NiCl2"},
        {},
        [],
    )
    atoms = [o for o in spec.objects if o.type == "sphere"]
    bonds = [o for o in spec.objects if o.type == "cylinder"]
    assert len(atoms) == 3
    assert len(bonds) == 2
    elements = {a.metadata.get("element") for a in atoms}
    assert elements == {"Ni", "Cl"}


def test_equation_model_evaluator():
    """Verify AST-guarded expression evaluation and dense 120-point plot synthesis."""
    # Must block arbitrary Python calls / attribute tricks
    try:
        _safe_eval_expr("__import__('os').system('echo hi')", {"x": 1.0})
        assert False, "AST expression validator should reject __import__"
    except ValueError:
        pass

    spec = {
        "constants": {"k": "A * exp(-Ea / (R * T))"},
        "plots": [
            {
                "plot_type": "line",
                "title": "Reactant & Product Concentration vs Time",
                "x_name": "t",
                "x_label": "Time (s)",
                "x_min": 0.0,
                "x_max": 120.0,
                "y_label": "Concentration (M)",
                "series_name": "[Cl2] Reactant",
                "y_expr": "C0 * exp(-k * t)",
                "extra_curves": [{"name": "[NiCl2] Product", "expr": "C0 * (1 - exp(-k * t))", "color": "#10b981"}],
            },
            {
                "plot_type": "line",
                "title": "Arrhenius Rate Constant vs Temperature",
                "x_name": "temp_k",
                "x_label": "Temperature (K)",
                "x_min": 290.0,
                "x_max": 420.0,
                "y_label": "Rate Constant k (1/s)",
                "series_name": "k(T)",
                "y_expr": "A * exp(-Ea / (R * temp_k))",
            },
        ],
    }
    res = evaluate_equation_model(
        model_spec=spec,
        topic="Nickel when reacted with chlorine",
        parameters={"temperature_K": 323.15, "initial_concentration_M": 1.0, "activation_energy_kJ": 65.0, "pre_exponential_factor": 1e9},
        domain="chemistry",
        n_points=120,
    )
    assert len(res["plots"]) == 2
    assert len(res["plots"][0]["x"]) == 120
    assert res["plots"][0]["extra_series"] and len(res["plots"][0]["extra_series"][0]["y"]) == 120
    assert res["plots"][0]["y"][0] > res["plots"][0]["y"][-1]
    assert res["plots"][1]["y"][-1] > res["plots"][1]["y"][0]

    # Verify nested-quote + Greek symbol + unresolved-optional-constant + LHS=RHS normalization
    sg_res = evaluate_equation_model(
        model_spec={
            "constants": {"unused_G": "unknown_A + unknown_B"},
            "plots": [
                {"plot_type": "line", "title": "Resistance Shift", "x_name": "x", "x_min": 0.0, "x_max": 0.002, "y_expr": '"(R0 * k) * ε"'},
                {"plot_type": "line", "title": "Total Resistance", "x_name": "Time (s)", "x_min": 0.0, "x_max": 10.0, "y_expr": "R(t) = R0 * (1 + 0.01 * t)"},
            ],
        },
        topic="strain gauge principle",
        parameters={"nominal_resistance_ohm": 120.0, "gauge_factor": 2.1},
        domain="mechanical_engineering",
        n_points=120,
    )
    assert len(sg_res["plots"]) == 2
    assert sg_res["plots"][0]["y"][-1] > sg_res["plots"][0]["y"][0]
    assert sg_res["plots"][1]["y"][-1] > sg_res["plots"][1]["y"][0]


if __name__ == "__main__":
    test_token_filtering_and_stopword_removal()
    print("PASS: test_token_filtering_and_stopword_removal")
    test_context_compression_with_papers()
    print("PASS: test_context_compression_with_papers")
    test_deepseek_prompt_structure()
    print("PASS: test_deepseek_prompt_structure")
    test_cross_domain_analysis_depth()
    print("PASS: test_cross_domain_analysis_depth")
    test_word_boundary_novel_experiment_routing()
    print("PASS: test_word_boundary_novel_experiment_routing")
    test_dynamic_sandbox_and_plot_validation()
    print("PASS: test_dynamic_sandbox_and_plot_validation")
    test_nickel_chloride_3d_molecule_selection()
    print("PASS: test_nickel_chloride_3d_molecule_selection")
    test_equation_model_evaluator()
    print("PASS: test_equation_model_evaluator")
    print("ALL REFINEMENT & ANALYSIS TESTS PASSED!")

