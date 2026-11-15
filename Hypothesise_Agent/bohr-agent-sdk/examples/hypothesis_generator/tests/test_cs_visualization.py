"""
Computer Science & Cross-Domain Visualization Tests
===================================================
Verifies:
1. CS Neural Network 3D scene specification and telemetry
2. CS Algorithm (Sorting & Graph Traversal) 3D scene specification
3. CS 2D visual_data structure (layers, array steps, Dijkstra graph)
4. Domain parameter extraction and prompt-based domain enforcement
5. Exclusion of biology from supported domain mappings
"""

# import pytest
from simulation_agent.visualization.scene_generator import generate_scene_specification
from simulation_agent.visualization.templates.cs_templates import (
    build_neural_net_scene, build_algorithm_scene, build_cs_scene
)
from simulation_agent.agent import extract_procedure_from_text, run_simulation
from simulation_agent.router import DOMAIN_MAP


def test_cs_neural_network_scene():
    procedure = {
        "domain": "computer_science",
        "experiment_type": "model_comparison",
        "hypothesis": "Vision Transformer outperforms ResNet CNN",
        "parameters": {"learning_rate": 0.001, "dropout_rate": 0.3, "epochs": 50}
    }
    numerical = {
        "model_comparison": {
            "cnn_final_accuracy_pct": 89.0,
            "transformer_final_accuracy_pct": 91.5,
            "winner": "Transformer (ViT)"
        }
    }
    spec = build_neural_net_scene(procedure, numerical, [])
    assert spec.domain == "computer_science"
    assert spec.scene_template == "neural_network_3d"
    assert spec.is_simulation_backed is True
    assert len(spec.objects) > 10
    # Check that neurons and synapses exist
    assert any("node_" in obj.id for obj in spec.objects)
    assert any("synapse_" in obj.id for obj in spec.objects)
    assert any("pulse_particle" in obj.id for obj in spec.objects)
    # Check animation
    assert spec.animation.has_animation is True
    assert len(spec.animation.tracks) > 0
    # Check overlays
    assert any(m.id == "mo_accuracy" for m in spec.measurement_overlays)
    print("PASS: test_cs_neural_network_scene")


def test_cs_algorithm_sorting_scene():
    procedure = {
        "domain": "computer_science",
        "experiment_type": "algorithm_complexity",
        "hypothesis": "QuickSort and MergeSort have O(n log n) comparison bounds",
        "parameters": {"n_max": 250}
    }
    spec = build_algorithm_scene(procedure, {}, [])
    assert spec.domain == "computer_science"
    assert spec.scene_template == "algorithm_3d"
    assert any("sort_bar_" in obj.id for obj in spec.objects)
    assert any("sort_cursor" in obj.id for obj in spec.objects)
    assert any(m.id == "algo_time" for m in spec.measurement_overlays)
    print("PASS: test_cs_algorithm_sorting_scene")


def test_cs_algorithm_graph_scene():
    procedure = {
        "domain": "cs",
        "experiment_type": "graph_traversal",
        "hypothesis": "Dijkstra shortest path finds optimal route in weighted graph",
        "parameters": {}
    }
    spec = build_algorithm_scene(procedure, {}, [])
    assert spec.domain == "computer_science"
    assert any("graph_node_" in obj.id for obj in spec.objects)
    assert any("graph_edge_" in obj.id for obj in spec.objects)
    assert any("dijkstra_pulse" in obj.id for obj in spec.objects)
    print("PASS: test_cs_algorithm_graph_scene")


def test_cs_simulation_pipeline_with_visual_data():
    sim_input = {
        "topic": "Compare convergence speed and accuracy between CNN and Transformer models",
        "design": "## 1. HYPOTHESIS\nTransformers will achieve higher accuracy.\n## 3. EXPERIMENTAL DESIGN\nCIFAR-10 training.\n## 4. METHODOLOGY\nMeasure epochs and loss.",
        "domain": "cs"
    }
    result = run_simulation(sim_input)
    assert result["domain"] in ("cs", "computer_science")
    assert result["visualization_type"] == "algorithm"
    assert result["visual_data"] is not None
    assert "layers" in result["visual_data"]
    assert result["visualization_spec"]["scene_template"] == "neural_network_3d"
    print("PASS: test_cs_simulation_pipeline_with_visual_data")


def test_biology_excluded_from_router():
    assert "biology" not in DOMAIN_MAP
    assert "biological" not in DOMAIN_MAP
    assert "genomics" not in DOMAIN_MAP
    assert "protein" not in DOMAIN_MAP
    print("PASS: test_biology_excluded_from_router")


def test_explicit_domain_override_prevents_hallucination():
    proc = extract_procedure_from_text(
        "Some text that talks about strain and deformation",
        "A study on graph traversal and algorithms",
        user_domain="cs"
    )
    assert proc["domain"] == "computer_science"
    print("PASS: test_explicit_domain_override_prevents_hallucination")


if __name__ == "__main__":
    test_cs_neural_network_scene()
    test_cs_algorithm_sorting_scene()
    test_cs_algorithm_graph_scene()
    test_cs_simulation_pipeline_with_visual_data()
    test_biology_excluded_from_router()
    test_explicit_domain_override_prevents_hallucination()
    print("ALL COMPUTER SCIENCE VISUALIZATION TESTS PASSED!")
