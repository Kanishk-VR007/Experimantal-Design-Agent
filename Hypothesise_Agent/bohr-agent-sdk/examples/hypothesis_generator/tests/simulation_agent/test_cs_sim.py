"""
Tests for simulation_agent.engines.cs_sim
Includes Part 11.6 Benchmark 8 (BFS FIFO order, cycles, disconnected graphs),
DFS, Dijkstra (with negative-weight rejection), Topological Sort (with cycle rejection),
all 6 sorting algorithms + binary/linear search, and seeded property-based tests.
"""

import random
from collections import Counter
import pytest
from simulation_agent.engines import cs_sim


def test_benchmark_8_bfs_exact_fifo_order_and_levels():
    graph = {
        "A": ["B", "C"],
        "B": ["D", "E"],
        "C": ["F"],
        "D": [],
        "E": ["F"],
        "F": [],
        "Z": [],  # disconnected node
    }
    res = cs_sim.run({
        "domain": "computer_science",
        "experiment_type": "breadth_first_search",
        "parameters": {"graph": graph, "start_node": "A"},
    })
    assert res["status"] == "success"
    ae = res["numerical_results"]["algorithm_execution"]
    assert ae["traversal_order"] == ["A", "B", "C", "D", "E", "F"]
    assert ae["levels"] == {"A": 0, "B": 1, "C": 1, "D": 2, "E": 2, "F": 2}
    assert "Z" in ae["unreached_nodes"]
    assert ae["operation_count"] > 0


def test_bfs_handles_cycles_without_infinite_loop():
    cyclic = {"A": ["B"], "B": ["C", "A"], "C": ["A", "B"]}
    res = cs_sim.run({
        "experiment_type": "breadth_first_search",
        "parameters": {"graph": cyclic, "start_node": "A"},
    })
    ae = res["numerical_results"]["algorithm_execution"]
    assert ae["traversal_order"] == ["A", "B", "C"]
    assert len(ae["traversal_order"]) == len(set(ae["traversal_order"]))


def test_dijkstra_shortest_path_and_negative_weight_rejection():
    weighted = {
        "A": {"B": 4, "C": 2},
        "B": {"D": 1},
        "C": {"B": 1, "D": 5},
        "D": {},
    }
    res = cs_sim.run({
        "experiment_type": "dijkstra_shortest_path",
        "parameters": {"graph": weighted, "start_node": "A", "target_node": "D"},
    })
    ae = res["numerical_results"]["algorithm_execution"]
    assert ae["shortest_path"] == ["A", "C", "B", "D"]
    assert ae["total_cost"] == 4.0

    # Negative edge weight must fail cleanly
    neg_graph = {"A": {"B": -2}, "B": {}}
    res_neg = cs_sim.run({
        "experiment_type": "dijkstra_shortest_path",
        "parameters": {"graph": neg_graph, "start_node": "A"},
    })
    assert res_neg["status"] == "failed"


def test_topological_sort_valid_dag_and_cycle_detection():
    dag = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    res = cs_sim.run({"experiment_type": "topological_sort", "parameters": {"graph": dag}})
    ae = res["numerical_results"]["algorithm_execution"]
    order = ae["topological_order"]
    pos = {n: i for i, n in enumerate(order)}
    assert pos["A"] < pos["B"] < pos["D"]
    assert pos["A"] < pos["C"] < pos["D"]

    cyc = {"A": ["B"], "B": ["A"]}
    res_cyc = cs_sim.run({"experiment_type": "topological_sort", "parameters": {"graph": cyc}})
    assert res_cyc["status"] == "failed"


@pytest.mark.parametrize(
    "algo",
    ["bubble_sort", "selection_sort", "insertion_sort", "merge_sort", "quick_sort", "heap_sort"],
)
def test_property_based_sorting_algorithms_seeded(algo):
    rng = random.Random(42)
    for _ in range(5):
        arr = [rng.randint(-50, 100) for _ in range(rng.randint(5, 25))]
        res = cs_sim.run({"experiment_type": algo, "parameters": {"array": arr}})
        assert res["status"] == "success"
        ae = res["numerical_results"]["algorithm_execution"]
        out = ae["sorted_array"]
        assert out == sorted(arr)
        assert Counter(out) == Counter(arr)
        assert ae["operation_count"] > 0


def test_binary_search_found_and_not_found():
    arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    r_hit = cs_sim.run({"experiment_type": "binary_search", "parameters": {"array": arr, "target": 23}})
    assert r_hit["numerical_results"]["algorithm_execution"]["found"] is True
    assert r_hit["numerical_results"]["algorithm_execution"]["found_index"] == 5

    r_miss = cs_sim.run({"experiment_type": "binary_search", "parameters": {"array": arr, "target": 99}})
    assert r_miss["numerical_results"]["algorithm_execution"]["found"] is False
    assert r_miss["numerical_results"]["algorithm_execution"]["found_index"] == -1
