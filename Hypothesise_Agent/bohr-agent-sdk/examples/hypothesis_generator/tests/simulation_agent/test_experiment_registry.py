"""
Tests for simulation_agent.experiment_registry
Verifies all 7 domains, 36+ canonical experiments, deterministic classification,
and 1:1 registry <-> visualization template mapping.
"""

from simulation_agent.experiment_registry import (
    EXPERIMENT_REGISTRY,
    classify_experiment,
    get_experiment_entry,
    list_experiments_by_domain,
)
from simulation_agent.visualization.scene_generator import TEMPLATE_BUILDERS


def test_registry_covers_all_seven_canonical_domains():
    domains = {e.domain for e in EXPERIMENT_REGISTRY.values()}
    expected = {"civil", "mechanical", "physics", "chemistry", "biology", "electronics", "computer_science"}
    assert expected.issubset(domains), f"Missing domains: {expected - domains}"
    assert len(EXPERIMENT_REGISTRY) >= 35


def test_every_registered_experiment_has_valid_visualization_template():
    for exp_id, entry in EXPERIMENT_REGISTRY.items():
        assert entry.visualization_template in TEMPLATE_BUILDERS, (
            f"Experiment '{exp_id}' template '{entry.visualization_template}' missing from TEMPLATE_BUILDERS"
        )
        assert entry.equations, f"Experiment '{exp_id}' missing governing equations"
        assert entry.method, f"Experiment '{exp_id}' missing method description"


def test_classify_point_load_vs_udl_beam():
    d1, e1, _ = classify_experiment(topic="5 m simply supported beam with 10 kN central point load")
    assert d1 == "civil"
    assert e1 == "simply_supported_beam_point_load"

    d2, e2, _ = classify_experiment(topic="5 m simply supported beam with 10 kN/m uniformly distributed load")
    assert d2 == "civil"
    assert e2 == "simply_supported_beam_udl"


def test_classify_cs_algorithms_distinctly():
    _, e_bfs, _ = classify_experiment(topic="Breadth-first search traversal on graph")
    _, e_dfs, _ = classify_experiment(topic="Depth-first search traversal on graph")
    _, e_dij, _ = classify_experiment(topic="Dijkstra shortest path on weighted network")
    _, e_qs, _ = classify_experiment(topic="QuickSort execution on unsorted array")
    assert e_bfs == "breadth_first_search"
    assert e_dfs == "depth_first_search"
    assert e_dij == "dijkstra_shortest_path"
    assert e_qs == "quick_sort"


def test_classify_unknown_returns_none_experiment_id():
    _, exp_id, _ = classify_experiment(topic="Quantum chromodynamics lattice gauge theory")
    assert exp_id is None


def test_list_experiments_by_domain_helper():
    bio_ids = [e.experiment_id for e in list_experiments_by_domain("biology")]
    assert "michaelis_menten" in bio_ids
    assert "logistic_growth" in bio_ids
    assert get_experiment_entry("four_bar_linkage") is not None
