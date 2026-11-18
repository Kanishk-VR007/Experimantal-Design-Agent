"""
Tests for simulation_agent.visualization.scene_generator & scene_validator
Verifies strict (domain, experiment_id) -> template synchronization and ensures
RLC never gets pendulum, truss/shaft never get beam, titration/kinetics never get molecule,
BFS never gets Dijkstra, and unsupported/failed get None.
"""

from simulation_agent.visualization.scene_generator import generate_scene_specification
from simulation_agent.visualization.scene_schema import SceneSpecification
from backend.visualization.scene_validator import validate_scene_specification
from simulation_agent.engines import electronics_sim, civil_sim, mech_sim, chem_sim, cs_sim


def test_rlc_gets_rlc_circuit_never_pendulum():
    raw = electronics_sim.run({"experiment_type": "series_rlc", "parameters": {"resistance_ohm": 10.0, "inductance_H": 0.1, "capacitance_F": 0.001}})
    spec = generate_scene_specification(
        {"domain": "physics", "experiment_type": "series_rlc"},
        raw["numerical_results"],
        raw["plot_data"],
    )
    assert spec is not None
    assert spec["scene_template"] == "rlc_circuit"
    assert spec["scene_template"] != "simple_pendulum"
    ok, _ = validate_scene_specification(SceneSpecification(**spec), expected_experiment_id="series_rlc", expected_template="rlc_circuit")
    assert ok is True


def test_truss_and_shaft_never_get_beam_template():
    r_truss = civil_sim.run({"experiment_type": "truss_analysis", "parameters": {"span_m": 10.0, "height_m": 3.0, "panels": 4, "point_load_kN": 20.0}})
    s_truss = generate_scene_specification({"domain": "civil_engineering", "experiment_type": "truss_analysis"}, r_truss["numerical_results"], r_truss["plot_data"])
    assert s_truss["scene_template"] == "truss_structure"

    r_shaft = mech_sim.run({"experiment_type": "shaft_design", "parameters": {"torque_Nm": 200.0, "diameter_mm": 40.0}})
    s_shaft = generate_scene_specification({"domain": "mechanical_engineering", "experiment_type": "shaft_design"}, r_shaft["numerical_results"], r_shaft["plot_data"])
    assert s_shaft["scene_template"] == "shaft_torsion"


def test_titration_and_kinetics_never_get_molecule_template():
    r_tit = chem_sim.run({"experiment_type": "acid_base_titration", "parameters": {"pKa": 4.76}})
    s_tit = generate_scene_specification({"domain": "chemistry", "experiment_type": "acid_base_titration"}, r_tit["numerical_results"], r_tit["plot_data"])
    assert s_tit["scene_template"] == "titration_apparatus"

    r_kin = chem_sim.run({"experiment_type": "reaction_kinetics", "parameters": {"reaction_order": 1}})
    s_kin = generate_scene_specification({"domain": "chemistry", "experiment_type": "reaction_kinetics"}, r_kin["numerical_results"], r_kin["plot_data"])
    assert s_kin["scene_template"] == "reaction_kinetics"


def test_bfs_scene_uses_actual_executed_graph_not_dijkstra():
    graph = {"S": ["X", "Y"], "X": ["W"], "Y": [], "W": []}
    r_bfs = cs_sim.run({"experiment_type": "breadth_first_search", "parameters": {"graph": graph, "start_node": "S"}})
    s_bfs = generate_scene_specification({"domain": "computer_science", "experiment_type": "breadth_first_search"}, r_bfs["numerical_results"], r_bfs["plot_data"])
    assert s_bfs["scene_template"] == "graph_traversal"
    assert s_bfs["experiment_id"] == "breadth_first_search"
    obj_ids = {o["id"] for o in s_bfs["objects"]}
    assert {"node_S", "node_X", "node_Y", "node_W"}.issubset(obj_ids)
    assert "dijkstra" not in s_bfs["title"].lower()


def test_unsupported_or_failed_simulation_produces_no_scene():
    assert generate_scene_specification({"domain": "general"}, {}, [], simulation_status="unsupported") is None
    assert generate_scene_specification({"domain": "civil"}, {}, [], simulation_status="failed") is None


def test_scene_validator_rejects_mismatched_template():
    r_rlc = electronics_sim.run({"experiment_type": "series_rlc", "parameters": {"resistance_ohm": 10.0, "inductance_H": 0.1, "capacitance_F": 0.001}})
    s_rlc = generate_scene_specification({"domain": "electronics", "experiment_type": "series_rlc"}, r_rlc["numerical_results"], r_rlc["plot_data"])
    ok, issues = validate_scene_specification(SceneSpecification(**s_rlc), expected_experiment_id="pendulum", expected_template="simple_pendulum")
    assert ok is False
    assert any("mismatch" in i.lower() for i in issues)

