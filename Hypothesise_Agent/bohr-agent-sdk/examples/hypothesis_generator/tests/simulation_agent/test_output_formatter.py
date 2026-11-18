"""
Tests for simulation_agent.output_formatter
Verifies:
  - No fabricated confidence_score (None by default)
  - No Student-t 95% CI computed on deterministic ODE/analytical trajectories
  - ScientificValidator runs before finalizing status
  - Honest unsupported/failed output without synthetic plots or 3D scene
"""

from simulation_agent.output_formatter import format_output
from simulation_agent.engines import physics_sim, llm_fallback


def test_output_formatter_no_fabricated_confidence_and_no_student_t_ci():
    raw = physics_sim.run({
        "domain": "physics",
        "experiment_type": "pendulum",
        "parameters": {"length_m": 1.0, "gravity": 9.81, "angle_rad": 0.2, "damping": 0.0},
    })
    out = format_output(raw, {"domain": "physics", "experiment_type": "pendulum", "hypothesis": "Test pendulum"})
    data = out.model_dump()
    assert data["confidence_score"] is None
    assert data["simulation_status"] == "success"
    assert data["validation"]["passed"] is True
    stat = data["numerical_results"]["statistical_summary"]
    assert "ci_95_lower" not in stat
    assert "ci_95_upper" not in stat
    assert not any("95% ci" in obs.lower() for obs in data["observations"])


def test_output_formatter_unsupported_preserves_empty_plots_and_no_scene():
    proc = {"domain": "general", "hypothesis": "Quantum lattice gauge"}
    raw = llm_fallback.run(proc)
    out = format_output(raw, proc)
    data = out.model_dump()
    assert data["simulation_status"] == "unsupported"
    assert data["plot_data"] == []
    assert data["visualization_spec"] is None
    assert data["confidence_score"] is None
