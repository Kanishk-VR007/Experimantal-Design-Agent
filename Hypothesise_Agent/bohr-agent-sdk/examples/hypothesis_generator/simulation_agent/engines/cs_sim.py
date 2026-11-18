"""
Computer Science Simulation & Algorithm Execution Engine
=========================================================
Executes real deterministic algorithms with complete step-by-step instrumentation:

Graph Algorithms:
  - breadth_first_search (FIFO deque traversal, level map, handles cycles & disconnected nodes)
  - depth_first_search (LIFO stack traversal)
  - dijkstra_shortest_path (Min-heap priority queue, negative-weight rejection)
  - connected_components (Undirected component partitioning)
  - topological_sort (Kahn's algorithm with explicit cycle detection)

Sorting Algorithms:
  - bubble_sort, selection_sort, insertion_sort, merge_sort, quick_sort, heap_sort

Searching Algorithms:
  - linear_search, binary_search

Separate Theoretical Analysis & Parametric ML Models:
  - algorithm_complexity (Big-O theoretical scaling curves — separate from execution)
  - model_comparison, dropout_effect, neural_network_training (clearly labeled parametric models)
"""

from __future__ import annotations

import time
import heapq
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .llm_fallback import build_unsupported_response, build_failed_response


DEFAULT_UNWEIGHTED_GRAPH: Dict[str, List[str]] = {
    "A": ["B", "C"],
    "B": ["D", "E"],
    "C": ["F"],
    "D": [],
    "E": ["F"],
    "F": [],
}

DEFAULT_WEIGHTED_GRAPH: Dict[str, Dict[str, float]] = {
    "A": {"B": 4, "C": 2},
    "B": {"D": 5, "E": 2},
    "C": {"B": 1, "E": 3},
    "D": {"F": 2},
    "E": {"F": 4},
    "F": {},
}

DEFAULT_SORT_ARRAY: List[float] = [45, 12, 89, 34, 67, 23, 91, 5]


def _normalize_graph_unweighted(raw_graph: Any) -> Dict[str, List[str]]:
    if not isinstance(raw_graph, dict) or not raw_graph:
        return {k: list(v) for k, v in DEFAULT_UNWEIGHTED_GRAPH.items()}
    adj: Dict[str, List[str]] = {}
    all_nodes = set(str(k) for k in raw_graph.keys())
    for k, nbrs in raw_graph.items():
        ks = str(k)
        if isinstance(nbrs, dict):
            adj[ks] = [str(n) for n in nbrs.keys()]
        elif isinstance(nbrs, (list, tuple, set)):
            adj[ks] = [str(n) for n in nbrs]
        else:
            adj[ks] = []
        all_nodes.update(adj[ks])
    for n in all_nodes:
        adj.setdefault(n, [])
    return adj


def _normalize_graph_weighted(raw_graph: Any) -> Dict[str, Dict[str, float]]:
    if not isinstance(raw_graph, dict) or not raw_graph:
        return {k: dict(v) for k, v in DEFAULT_WEIGHTED_GRAPH.items()}
    adj: Dict[str, Dict[str, float]] = {}
    all_nodes = set(str(k) for k in raw_graph.keys())
    for k, nbrs in raw_graph.items():
        ks = str(k)
        adj[ks] = {}
        if isinstance(nbrs, dict):
            for n, w in nbrs.items():
                adj[ks][str(n)] = float(w)
                all_nodes.add(str(n))
        elif isinstance(nbrs, (list, tuple)):
            for item in nbrs:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    adj[ks][str(item[0])] = float(item[1])
                    all_nodes.add(str(item[0]))
                else:
                    adj[ks][str(item)] = 1.0
                    all_nodes.add(str(item))
    for n in all_nodes:
        adj.setdefault(n, {})
    return adj


def _build_graph_visual_data(
    algorithm_name: str,
    nodes_order: List[str],
    edges_list: List[Dict[str, Any]],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build deterministic 2D/3D layout metadata for actual executed graph."""
    n = max(len(nodes_order), 1)
    nodes_meta = []
    for idx, nid in enumerate(nodes_order):
        angle = 2.0 * np.pi * idx / n
        nodes_meta.append({
            "id": nid,
            "label": str(nid),
            "x": round(220.0 + 140.0 * float(np.cos(angle)), 1),
            "y": round(160.0 + 100.0 * float(np.sin(angle)), 1),
        })
    out = {
        "type": "algorithm",
        "algorithm": algorithm_name,
        "graph": {
            "nodes": nodes_meta,
            "edges": edges_list,
        },
    }
    if extra:
        out.update(extra)
    return out


# ─── GRAPH ALGORITHMS ────────────────────────────────────────────────────────

def _run_bfs(params: dict) -> Dict[str, Any]:
    """True FIFO queue-based Breadth-First Search with complete step trace."""
    adj = _normalize_graph_unweighted(params.get("graph"))
    start = str(params.get("start_node") or next(iter(adj.keys())))
    if start not in adj:
        return build_failed_response(
            {"domain": "computer_science", "experiment_type": "breadth_first_search"},
            f"start_node '{start}' does not exist in graph nodes {sorted(adj.keys())}.",
        )

    t0 = time.perf_counter()
    visited = {start}
    levels: Dict[str, int] = {start: 0}
    parent: Dict[str, Optional[str]] = {start: None}
    q = deque([start])
    traversal_order: List[str] = []
    steps: List[Dict[str, Any]] = [{
        "step": 0, "operation": "initialize", "current_node": start,
        "visited": [start], "queue": list(q),
        "detail": f"Enqueue start node '{start}' at level 0",
    }]
    ops = 1

    while q:
        u = q.popleft()
        ops += 1
        traversal_order.append(u)
        steps.append({
            "step": len(steps), "operation": "dequeue_visit", "current_node": u,
            "visited": list(traversal_order), "queue": list(q),
            "detail": f"Dequeue & visit '{u}' (level {levels[u]})",
        })
        for v in adj.get(u, []):
            ops += 1
            if v not in visited:
                visited.add(v)
                levels[v] = levels[u] + 1
                parent[v] = u
                q.append(v)
                ops += 1
                steps.append({
                    "step": len(steps), "operation": "enqueue_neighbor", "current_node": v,
                    "from_node": u, "visited": list(traversal_order), "queue": list(q),
                    "detail": f"Discover '{v}' from '{u}' -> enqueue (level {levels[v]})",
                })
            else:
                steps.append({
                    "step": len(steps), "operation": "skip_visited", "current_node": v,
                    "from_node": u, "visited": list(traversal_order), "queue": list(q),
                    "detail": f"Skip already-visited neighbor '{v}' of '{u}'",
                })

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    unreached = sorted(set(adj.keys()) - set(traversal_order))
    edges_list = [
        {"source": u, "target": v, "in_tree": (parent.get(v) == u)}
        for u, nbrs in adj.items() for v in nbrs
    ]

    numerical = {
        "algorithm_execution": {
            "algorithm": "breadth_first_search",
            "input_data": {"graph": adj, "start_node": start},
            "initial_state": {"queue": [start], "visited": [start]},
            "traversal_order": traversal_order,
            "levels": levels,
            "parent_tree": parent,
            "unreached_nodes": unreached,
            "visited_count": len(traversal_order),
            "total_nodes": len(adj),
            "total_edges": len(edges_list),
            "operation_count": ops,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
        },
        "execution_steps": steps,
    }

    plots = [{
        "plot_type": "bar",
        "title": f"BFS Discovery Depth (Level) From '{start}'",
        "x_label": "Visited Node (in BFS Order)",
        "y_label": "Hop Distance (Level)",
        "x": traversal_order,
        "y": [levels[n] for n in traversal_order],
        "series_name": "BFS Level",
    }]

    visual_data = _build_graph_visual_data(
        "breadth_first_search", list(adj.keys()), edges_list,
        extra={"traversal_order": traversal_order, "levels": levels, "trace_steps": steps[:50]},
    )

    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "breadth_first_search",
        "solver": {"name": "bfs", "version": "2.0", "method": "FIFO Queue Breadth-First Search", "equations": ["Time: O(V + E)", "Space: O(V)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [
            f"BFS traversal from '{start}': {' → '.join(traversal_order)} ({len(traversal_order)}/{len(adj)} nodes reached).",
            f"Recorded {len(steps)} instrumented steps and {ops} elementary operations in {elapsed_ms} ms.",
            f"Unreached (disconnected) nodes: {unreached if unreached else 'None'}.",
        ],
        "assumptions": ["Unweighted edges; deterministic adjacency iteration order"],
        "limitations": ["Unweighted hop count only"], "warnings": [],
        "simulation_log": [f"[cs_sim] Executed real FIFO BFS from '{start}' -> {traversal_order}"],
    }


def _run_dfs(params: dict) -> Dict[str, Any]:
    """True LIFO stack-based Depth-First Search with step trace."""
    adj = _normalize_graph_unweighted(params.get("graph"))
    start = str(params.get("start_node") or next(iter(adj.keys())))
    if start not in adj:
        return build_failed_response(
            {"domain": "computer_science", "experiment_type": "depth_first_search"},
            f"start_node '{start}' not found in graph.",
        )

    t0 = time.perf_counter()
    stack = [start]
    visited = set()
    traversal_order: List[str] = []
    parent: Dict[str, Optional[str]] = {start: None}
    steps: List[Dict[str, Any]] = [{
        "step": 0, "operation": "initialize", "current_node": start,
        "visited": [], "stack": list(stack), "detail": f"Push start node '{start}'",
    }]
    ops = 1

    while stack:
        u = stack.pop()
        ops += 1
        if u in visited:
            steps.append({
                "step": len(steps), "operation": "skip_visited", "current_node": u,
                "visited": list(traversal_order), "stack": list(stack),
                "detail": f"Popped already-visited '{u}'; skip",
            })
            continue
        visited.add(u)
        traversal_order.append(u)
        steps.append({
            "step": len(steps), "operation": "pop_visit", "current_node": u,
            "visited": list(traversal_order), "stack": list(stack),
            "detail": f"Visit '{u}'",
        })
        # Push neighbors in reverse so left-most neighbor is visited first (matches recursive DFS)
        for v in reversed(adj.get(u, [])):
            ops += 1
            if v not in visited:
                if v not in parent:
                    parent[v] = u
                stack.append(v)
                steps.append({
                    "step": len(steps), "operation": "push_neighbor", "current_node": v,
                    "from_node": u, "visited": list(traversal_order), "stack": list(stack),
                    "detail": f"Push neighbor '{v}' of '{u}' onto stack",
                })

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    edges_list = [{"source": u, "target": v, "in_tree": (parent.get(v) == u)} for u, nbrs in adj.items() for v in nbrs]

    numerical = {
        "algorithm_execution": {
            "algorithm": "depth_first_search",
            "input_data": {"graph": adj, "start_node": start},
            "initial_state": {"stack": [start], "visited": []},
            "traversal_order": traversal_order,
            "parent_tree": parent,
            "visited_count": len(traversal_order),
            "total_nodes": len(adj),
            "operation_count": ops,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar",
        "title": f"DFS Discovery Sequence From '{start}'",
        "x_label": "Node", "y_label": "Discovery Index",
        "x": traversal_order, "y": list(range(1, len(traversal_order) + 1)), "series_name": "Discovery Order",
    }]
    visual_data = _build_graph_visual_data("depth_first_search", list(adj.keys()), edges_list, extra={"traversal_order": traversal_order, "trace_steps": steps[:50]})
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "depth_first_search",
        "solver": {"name": "dfs", "version": "2.0", "method": "LIFO Stack Depth-First Search", "equations": ["Time: O(V + E)", "Space: O(V)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [f"DFS traversal from '{start}': {' → '.join(traversal_order)} ({ops} ops, {elapsed_ms} ms)."],
        "assumptions": ["Deterministic neighbor order"], "limitations": ["Does not find shortest paths"], "warnings": [],
        "simulation_log": [f"[cs_sim] Executed real LIFO DFS from '{start}' -> {traversal_order}"],
    }


def _run_dijkstra(params: dict) -> Dict[str, Any]:
    """True min-heap Dijkstra shortest path with negative-weight validation."""
    adj = _normalize_graph_weighted(params.get("graph"))
    start = str(params.get("start_node") or next(iter(adj.keys())))
    target = str(params.get("target_node")) if params.get("target_node") else None
    if start not in adj:
        return build_failed_response({"domain": "computer_science", "experiment_type": "dijkstra_shortest_path"}, f"start_node '{start}' not in graph.")

    # Reject negative edge weights explicitly
    for u, nbrs in adj.items():
        for v, w in nbrs.items():
            if w < 0:
                return build_failed_response(
                    {"domain": "computer_science", "experiment_type": "dijkstra_shortest_path"},
                    f"Dijkstra's algorithm requires non-negative edge weights; found w({u},{v}) = {w}.",
                )

    t0 = time.perf_counter()
    dist: Dict[str, float] = {n: float("inf") for n in adj}
    prev: Dict[str, Optional[str]] = {n: None for n in adj}
    dist[start] = 0.0
    pq: List[Tuple[float, str]] = [(0.0, start)]
    settled: List[str] = []
    settled_set = set()
    steps: List[Dict[str, Any]] = [{
        "step": 0, "operation": "initialize", "current_node": start,
        "visited": [], "distances": {k: (v if v != float("inf") else None) for k, v in dist.items()},
        "detail": f"Set dist[{start}] = 0 and push to min-heap",
    }]
    ops = 1

    while pq:
        d_u, u = heapq.heappop(pq)
        ops += 1
        if u in settled_set:
            continue
        settled_set.add(u)
        settled.append(u)
        steps.append({
            "step": len(steps), "operation": "settle_min", "current_node": u,
            "visited": list(settled), "cost": d_u,
            "detail": f"Settle '{u}' with optimal distance {d_u}",
        })
        for v, w in adj[u].items():
            ops += 1
            nd = d_u + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
                ops += 1
                steps.append({
                    "step": len(steps), "operation": "relax_edge", "current_node": v,
                    "from_node": u, "visited": list(settled), "new_dist": nd,
                    "detail": f"Relax ({u}->{v}, w={w}): dist[{v}] updated to {nd}",
                })

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)

    # Reconstruct shortest path to target (or farthest reachable node)
    if target is None or target not in adj:
        reachable = [n for n in adj if dist[n] < float("inf")]
        target = reachable[-1] if reachable else start

    shortest_path: List[str] = []
    if dist.get(target, float("inf")) < float("inf"):
        curr: Optional[str] = target
        while curr is not None:
            shortest_path.append(curr)
            curr = prev[curr]
        shortest_path.reverse()

    path_edges = set(zip(shortest_path[:-1], shortest_path[1:]))
    edges_list = [
        {"source": u, "target": v, "weight": w, "in_path": (u, v) in path_edges}
        for u, nbrs in adj.items() for v, w in nbrs.items()
    ]
    dist_clean = {k: (round(v, 6) if v < float("inf") else None) for k, v in dist.items()}
    total_cost = dist_clean.get(target)

    numerical = {
        "algorithm_execution": {
            "algorithm": "dijkstra_shortest_path",
            "input_data": {"graph": adj, "start_node": start, "target_node": target},
            "initial_state": {"start": start, "distances": {k: (0.0 if k == start else None) for k in adj}},
            "settled_order": settled,
            "distances": dist_clean,
            "shortest_path": shortest_path,
            "total_cost": total_cost,
            "operation_count": ops,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V)",
        },
        "execution_steps": steps,
    }
    reachable_nodes = [n for n in settled if dist_clean[n] is not None]
    plots = [{
        "plot_type": "bar",
        "title": f"Dijkstra Shortest-Path Distances From '{start}'",
        "x_label": "Node", "y_label": "Shortest Path Cost",
        "x": reachable_nodes, "y": [dist_clean[n] for n in reachable_nodes], "series_name": "Distance",
    }]
    visual_data = _build_graph_visual_data(
        "dijkstra_shortest_path", list(adj.keys()), edges_list,
        extra={"shortest_path": shortest_path, "total_cost": total_cost, "distances": dist_clean, "trace_steps": steps[:50]},
    )
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "dijkstra_shortest_path",
        "solver": {"name": "dijkstra", "version": "2.0", "method": "Binary-Heap Priority Queue Dijkstra", "equations": ["Time: O((V + E) log V)", "Space: O(V)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [
            f"Shortest path {start} → {target}: {' → '.join(shortest_path)} with total cost = {total_cost}.",
            f"Settled {len(settled)} nodes in {ops} operations ({elapsed_ms} ms).",
        ],
        "assumptions": ["Non-negative edge weights"], "limitations": ["Cannot solve graphs with negative edge weights"], "warnings": [],
        "simulation_log": [f"[cs_sim] Executed real Dijkstra {start}->{target}: path={shortest_path}, cost={total_cost}"],
    }


def _run_connected_components(params: dict) -> Dict[str, Any]:
    """Exact connected components on undirected graph."""
    adj = _normalize_graph_unweighted(params.get("graph"))
    # Symmetrize for undirected connectivity
    undir: Dict[str, List[str]] = {u: list(nbrs) for u, nbrs in adj.items()}
    for u, nbrs in adj.items():
        for v in nbrs:
            if u not in undir.setdefault(v, []):
                undir[v].append(u)

    t0 = time.perf_counter()
    visited = set()
    components: List[List[str]] = []
    steps: List[Dict[str, Any]] = []
    ops = 0

    for node in sorted(undir.keys()):
        ops += 1
        if node in visited:
            continue
        comp: List[str] = []
        q = deque([node])
        visited.add(node)
        while q:
            u = q.popleft()
            comp.append(u)
            ops += 1
            for v in undir[u]:
                ops += 1
                if v not in visited:
                    visited.add(v)
                    q.append(v)
        components.append(comp)
        steps.append({"step": len(steps), "operation": "component_found", "component": comp, "visited": sorted(visited), "detail": f"Found component {len(components)}: {comp}"})

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    edges_list = [{"source": u, "target": v} for u, nbrs in adj.items() for v in nbrs]
    numerical = {
        "algorithm_execution": {
            "algorithm": "connected_components",
            "input_data": {"graph": adj},
            "components": components,
            "component_count": len(components),
            "operation_count": ops,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar", "title": "Connected Component Sizes",
        "x_label": "Component", "y_label": "Node Count",
        "x": [f"C{i+1}" for i in range(len(components))], "y": [len(c) for c in components], "series_name": "Size",
    }]
    visual_data = _build_graph_visual_data("connected_components", sorted(undir.keys()), edges_list, extra={"components": components})
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "connected_components",
        "solver": {"name": "connected_components", "version": "2.0", "method": "BFS Connected Components", "equations": ["Time: O(V + E)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [f"Found {len(components)} connected component(s): {components}."],
        "assumptions": ["Undirected graph connectivity"], "limitations": ["Not strongly connected directed components"], "warnings": [],
        "simulation_log": [f"[cs_sim] Connected components executed: {len(components)} components"],
    }


def _run_topological_sort(params: dict) -> Dict[str, Any]:
    """Exact Kahn's algorithm for DAG topological sort with cycle detection."""
    adj = _normalize_graph_unweighted(params.get("graph"))
    t0 = time.perf_counter()
    in_deg = {u: 0 for u in adj}
    for u, nbrs in adj.items():
        for v in nbrs:
            in_deg[v] = in_deg.get(v, 0) + 1

    # Min-heap for deterministic lexicographical order
    heap = [u for u, d in in_deg.items() if d == 0]
    heapq.heapify(heap)
    order: List[str] = []
    steps: List[Dict[str, Any]] = [{"step": 0, "operation": "initialize", "in_degree": dict(in_deg), "ready_queue": sorted(heap), "detail": "Initialized in-degrees"}]
    ops = len(adj)

    while heap:
        u = heapq.heappop(heap)
        order.append(u)
        ops += 1
        steps.append({"step": len(steps), "operation": "emit_node", "current_node": u, "visited": list(order), "ready_queue": sorted(heap), "detail": f"Emit zero-in-degree node '{u}'"})
        for v in adj.get(u, []):
            in_deg[v] -= 1
            ops += 1
            if in_deg[v] == 0:
                heapq.heappush(heap, v)

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    is_dag = len(order) == len(adj)
    if not is_dag:
        return build_failed_response(
            {"domain": "computer_science", "experiment_type": "topological_sort"},
            f"Cycle detected: topological sort requires a DAG (resolved {len(order)}/{len(adj)} nodes).",
        )

    edges_list = [{"source": u, "target": v} for u, nbrs in adj.items() for v in nbrs]
    numerical = {
        "algorithm_execution": {
            "algorithm": "topological_sort",
            "input_data": {"graph": adj},
            "topological_order": order,
            "is_dag": True,
            "operation_count": ops,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar", "title": "Topological Ordering Rank",
        "x_label": "Node", "y_label": "Rank", "x": order, "y": list(range(1, len(order) + 1)), "series_name": "Order",
    }]
    visual_data = _build_graph_visual_data("topological_sort", order, edges_list, extra={"traversal_order": order})
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "topological_sort",
        "solver": {"name": "topological_sort", "version": "2.0", "method": "Kahn's Algorithm", "equations": ["Time: O(V + E)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [f"Valid DAG topological ordering: {' → '.join(order)}."],
        "assumptions": ["Directed Acyclic Graph"], "limitations": ["Fails on cyclic graphs"], "warnings": [],
        "simulation_log": [f"[cs_sim] Kahn's topological sort executed: {order}"],
    }


# ─── SORTING ALGORITHMS ──────────────────────────────────────────────────────

def _run_sorting(algo_id: str, params: dict) -> Dict[str, Any]:
    raw_arr = params.get("array") or params.get("data") or DEFAULT_SORT_ARRAY
    if not isinstance(raw_arr, list) or not raw_arr:
        raw_arr = list(DEFAULT_SORT_ARRAY)
    arr_initial = [float(x) if not isinstance(x, int) else x for x in raw_arr]
    arr = list(arr_initial)
    n = len(arr)
    steps: List[Dict[str, Any]] = [{"step": 0, "operation": "initial", "indices": [], "array": list(arr), "detail": f"Initial array of length {n}"}]
    comparisons = 0
    swaps = 0
    max_trace = 120

    def record(op: str, indices: List[int], detail: str):
        if len(steps) < max_trace:
            steps.append({"step": len(steps), "operation": op, "indices": indices, "array": list(arr), "detail": detail})

    t0 = time.perf_counter()

    if algo_id == "bubble_sort":
        t_comp, s_comp = "O(n²)", "O(1)"
        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                comparisons += 1
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swaps += 1
                    swapped = True
                    record("swap", [j, j + 1], f"Swap {arr[j+1]} and {arr[j]}")
            if not swapped:
                break

    elif algo_id == "selection_sort":
        t_comp, s_comp = "O(n²)", "O(1)"
        for i in range(n):
            min_idx = i
            for j in range(i + 1, n):
                comparisons += 1
                if arr[j] < arr[min_idx]:
                    min_idx = j
            if min_idx != i:
                arr[i], arr[min_idx] = arr[min_idx], arr[i]
                swaps += 1
                record("swap", [i, min_idx], f"Place min {arr[i]} at index {i}")

    elif algo_id == "insertion_sort":
        t_comp, s_comp = "O(n²)", "O(1)"
        for i in range(1, n):
            key = arr[i]
            j = i - 1
            while j >= 0:
                comparisons += 1
                if arr[j] > key:
                    arr[j + 1] = arr[j]
                    swaps += 1
                    j -= 1
                else:
                    break
            arr[j + 1] = key
            record("insert", [j + 1], f"Insert {key} at index {j + 1}")

    elif algo_id == "merge_sort":
        t_comp, s_comp = "O(n log n)", "O(n)"

        def _ms(lo: int, hi: int):
            nonlocal comparisons, swaps
            if hi - lo <= 1:
                return
            mid = (lo + hi) // 2
            _ms(lo, mid)
            _ms(mid, hi)
            left = arr[lo:mid]
            right = arr[mid:hi]
            i = j = 0
            k = lo
            while i < len(left) and j < len(right):
                comparisons += 1
                if left[i] <= right[j]:
                    arr[k] = left[i]; i += 1
                else:
                    arr[k] = right[j]; j += 1
                swaps += 1; k += 1
            while i < len(left):
                arr[k] = left[i]; i += 1; k += 1; swaps += 1
            while j < len(right):
                arr[k] = right[j]; j += 1; k += 1; swaps += 1
            record("merge", [lo, hi - 1], f"Merged slice [{lo}:{hi}]")

        _ms(0, n)

    elif algo_id == "quick_sort":
        t_comp, s_comp = "O(n log n) avg / O(n²) worst", "O(log n)"

        def _qs(lo: int, hi: int):
            nonlocal comparisons, swaps
            if lo >= hi:
                return
            pivot = arr[hi]
            i = lo - 1
            for j in range(lo, hi):
                comparisons += 1
                if arr[j] <= pivot:
                    i += 1
                    if i != j:
                        arr[i], arr[j] = arr[j], arr[i]
                        swaps += 1
                        record("swap", [i, j], f"Partition swap around pivot {pivot}")
            if i + 1 != hi:
                arr[i + 1], arr[hi] = arr[hi], arr[i + 1]
                swaps += 1
            p_idx = i + 1
            record("partition", [p_idx], f"Pivot {pivot} fixed at index {p_idx}")
            _qs(lo, p_idx - 1)
            _qs(p_idx + 1, hi)

        _qs(0, n - 1)

    elif algo_id == "heap_sort":
        t_comp, s_comp = "O(n log n)", "O(1)"

        def _heapify(size: int, root: int):
            nonlocal comparisons, swaps
            largest = root
            l_c, r_c = 2 * root + 1, 2 * root + 2
            if l_c < size:
                comparisons += 1
                if arr[l_c] > arr[largest]:
                    largest = l_c
            if r_c < size:
                comparisons += 1
                if arr[r_c] > arr[largest]:
                    largest = r_c
            if largest != root:
                arr[root], arr[largest] = arr[largest], arr[root]
                swaps += 1
                record("heap_swap", [root, largest], f"Sift down swap indices {root}, {largest}")
                _heapify(size, largest)

        for i in range(n // 2 - 1, -1, -1):
            _heapify(n, i)
        for i in range(n - 1, 0, -1):
            arr[0], arr[i] = arr[i], arr[0]
            swaps += 1
            record("extract_max", [0, i], f"Extract max {arr[i]} to index {i}")
            _heapify(i, 0)
    else:
        return build_unsupported_response({"domain": "computer_science", "experiment_type": algo_id})

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    record("complete", [0, max(0, n - 1)], "Sorting complete")

    numerical = {
        "algorithm_execution": {
            "algorithm": algo_id,
            "input_data": arr_initial,
            "initial_state": arr_initial,
            "sorted_array": arr,
            "array_length": n,
            "comparisons": comparisons,
            "swaps_or_writes": swaps,
            "operation_count": comparisons + swaps,
            "execution_time_ms": elapsed_ms,
            "time_complexity": t_comp,
            "space_complexity": s_comp,
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar",
        "title": f"{algo_id.replace('_', ' ').title()} — Final Sorted Array",
        "x_label": "Index", "y_label": "Value",
        "x": [f"[{i}]" for i in range(n)], "y": arr, "series_name": "Sorted Value",
    }]
    visual_data = {
        "type": "algorithm",
        "algorithm": algo_id,
        "array_initial": arr_initial,
        "array_sorted": arr,
        "trace_steps": steps,
    }
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": algo_id,
        "solver": {"name": algo_id, "version": "2.0", "method": f"Instrumented {algo_id.replace('_', ' ').title()}", "equations": [f"Time: {t_comp}", f"Space: {s_comp}"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [
            f"Executed {algo_id} on {n} elements: {comparisons} comparisons, {swaps} swaps/writes ({elapsed_ms} ms).",
            f"Sorted output: {arr[:12]}{'...' if n > 12 else ''}.",
        ],
        "assumptions": ["Comparison-based numeric ordering"], "limitations": [f"Trace capped at {max_trace} snapshots for UI rendering"], "warnings": [],
        "simulation_log": [f"[cs_sim] Executed {algo_id}: n={n}, comparisons={comparisons}, swaps={swaps}"],
    }


# ─── SEARCHING ALGORITHMS ────────────────────────────────────────────────────

def _run_linear_search(params: dict) -> Dict[str, Any]:
    raw_arr = params.get("array") or params.get("data") or [12, 45, 7, 23, 56, 89, 34, 19]
    target = params.get("target", 56)
    t0 = time.perf_counter()
    steps = []
    found_idx = -1
    comparisons = 0
    for i, val in enumerate(raw_arr):
        comparisons += 1
        match = (val == target)
        steps.append({"step": i + 1, "operation": "compare", "index": i, "value": val, "match": match, "detail": f"Compare arr[{i}]={val} with target={target}"})
        if match:
            found_idx = i
            break
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)

    numerical = {
        "algorithm_execution": {
            "algorithm": "linear_search",
            "input_data": {"array": raw_arr, "target": target},
            "found": found_idx != -1,
            "found_index": found_idx,
            "comparisons": comparisons,
            "operation_count": comparisons,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar", "title": f"Linear Search (Target={target}, Found Index={found_idx})",
        "x_label": "Index", "y_label": "Value", "x": [f"[{i}]" for i in range(len(raw_arr))], "y": raw_arr, "series_name": "Array",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "linear_search",
        "solver": {"name": "linear_search", "version": "2.0", "method": "Instrumented Linear Search", "equations": ["Time: O(n)", "Space: O(1)"]},
        "numerical_results": numerical, "plot_data": plots,
        "visual_data": {"type": "algorithm", "algorithm": "linear_search", "array_initial": raw_arr, "array_sorted": raw_arr, "trace_steps": steps},
        "visualization_type": "algorithm",
        "observations": [f"Linear search for {target}: {'found at index ' + str(found_idx) if found_idx != -1 else 'not found'} after {comparisons} comparisons."],
        "assumptions": ["Sequential scan"], "limitations": ["Linear scan cost"], "warnings": [],
        "simulation_log": [f"[cs_sim] Linear search target={target} -> idx={found_idx}"],
    }


def _run_binary_search(params: dict) -> Dict[str, Any]:
    raw_arr = list(params.get("array") or params.get("data") or [5, 12, 23, 34, 45, 56, 67, 78, 89, 91])
    target = params.get("target", 67)
    warnings: List[str] = []
    if raw_arr != sorted(raw_arr):
        raw_arr = sorted(raw_arr)
        warnings.append("Input array was unsorted; sorted ascending prior to binary search.")

    t0 = time.perf_counter()
    lo, hi = 0, len(raw_arr) - 1
    found_idx = -1
    comparisons = 0
    steps = []
    while lo <= hi:
        mid = (lo + hi) // 2
        comparisons += 1
        val = raw_arr[mid]
        steps.append({"step": len(steps) + 1, "operation": "probe_mid", "lo": lo, "mid": mid, "hi": hi, "value": val, "detail": f"Probe mid={mid} (val={val}) vs target={target}"})
        if val == target:
            found_idx = mid
            break
        elif val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)

    numerical = {
        "algorithm_execution": {
            "algorithm": "binary_search",
            "input_data": {"array": raw_arr, "target": target},
            "found": found_idx != -1,
            "found_index": found_idx,
            "comparisons": comparisons,
            "operation_count": comparisons,
            "execution_time_ms": elapsed_ms,
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
        },
        "execution_steps": steps,
    }
    plots = [{
        "plot_type": "bar", "title": f"Binary Search (Target={target}, Found Index={found_idx})",
        "x_label": "Index", "y_label": "Value", "x": [f"[{i}]" for i in range(len(raw_arr))], "y": raw_arr, "series_name": "Sorted Array",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "algorithm_execution",
        "engine_used": "cs_sim", "experiment_id": "binary_search",
        "solver": {"name": "binary_search", "version": "2.0", "method": "Instrumented Binary Search", "equations": ["Time: O(log n)", "Space: O(1)"]},
        "numerical_results": numerical, "plot_data": plots,
        "visual_data": {"type": "algorithm", "algorithm": "binary_search", "array_initial": raw_arr, "array_sorted": raw_arr, "trace_steps": steps},
        "visualization_type": "algorithm",
        "observations": [f"Binary search for {target}: {'found at index ' + str(found_idx) if found_idx != -1 else 'not found'} in {comparisons} comparisons (O(log n))."],
        "assumptions": ["Sorted ascending random-access array"], "limitations": ["Requires pre-sorted input"], "warnings": warnings,
        "simulation_log": [f"[cs_sim] Binary search target={target} -> idx={found_idx} in {comparisons} probes"],
    }


# ─── SEPARATE THEORETICAL COMPLEXITY & PARAMETRIC ML MODELS ──────────────────

def _algorithm_complexity(params: dict) -> Dict[str, Any]:
    """Theoretical asymptotic Big-O comparison (distinct from algorithm execution)."""
    n_max = int(params.get("n_max", 500))
    n = np.linspace(1, n_max, 200)
    o_log = np.log2(np.maximum(n, 1))
    o_n = n
    o_nlogn = n * np.log2(np.maximum(n, 1))
    o_n2 = n ** 2

    numerical = {
        "theoretical_complexity": {
            "n_max": n_max,
            "O_log_n": round(float(o_log[-1]), 3),
            "O_n": round(float(o_n[-1]), 1),
            "O_n_log_n": round(float(o_nlogn[-1]), 1),
            "O_n2": round(float(o_n2[-1]), 1),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": "Theoretical Asymptotic Complexity Comparison (Big-O)",
        "x_label": "Input Size n", "y_label": "Theoretical Operations",
        "x": n.tolist(), "y": o_n.tolist(), "series_name": "O(n)",
        "extra_series": [
            {"y": o_nlogn.tolist(), "name": "O(n log n)", "color": "#f59e0b"},
            {"y": o_n2.tolist(), "name": "O(n²)", "color": "#ef4444"},
            {"y": o_log.tolist(), "name": "O(log n)", "color": "#10b981"},
        ],
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "cs_sim", "experiment_id": "algorithm_complexity",
        "solver": {"name": "algorithm_complexity", "version": "2.0", "method": "Theoretical Asymptotic Complexity Curves", "equations": ["O(log n), O(n), O(n log n), O(n^2)"]},
        "numerical_results": numerical, "plot_data": plots,
        "visual_data": {"type": "algorithm", "algorithm": "algorithm_complexity", "array_initial": DEFAULT_SORT_ARRAY, "array_sorted": sorted(DEFAULT_SORT_ARRAY)},
        "visualization_type": "algorithm",
        "observations": [f"Theoretical asymptotic counts at n={n_max}: O(log n)={o_log[-1]:.2f}, O(n)={n_max}, O(n log n)={o_nlogn[-1]:.0f}, O(n²)={o_n2[-1]:.0f}."],
        "assumptions": ["Unit-cost RAM theoretical model; not empirical wall-clock benchmarking"],
        "limitations": ["Constant factors and cache hierarchy effects omitted"], "warnings": [],
        "simulation_log": ["[cs_sim] Theoretical Big-O complexity curves generated"],
    }


def _model_comparison(params: dict) -> Dict[str, Any]:
    """Parametric analytical learning-curve comparison (CNN vs ViT)."""
    epochs = int(params.get("epochs", 50))
    t = np.arange(1, epochs + 1)
    cnn_loss = 2.3 * np.exp(-0.09 * t) + 0.13
    cnn_acc = np.minimum(89.0 * (1.0 - np.exp(-0.13 * t)), 89.0)
    trans_loss = 2.5 * np.exp(-0.055 * t) + 0.16
    trans_acc = np.minimum(91.5 * (1.0 - np.exp(-0.075 * t)), 91.5)

    def epoch_at_pct(arr, pct):
        idx = int(np.argmax(arr >= pct))
        return idx + 1 if arr[idx] >= pct else -1

    numerical = {
        "model_comparison": {
            "cnn_final_accuracy_pct": round(float(cnn_acc[-1]), 2),
            "transformer_final_accuracy_pct": round(float(trans_acc[-1]), 2),
            "winner": "Transformer" if float(trans_acc[-1]) > float(cnn_acc[-1]) else "CNN",
            "cnn_epochs_to_80pct": epoch_at_pct(cnn_acc, 80),
            "transformer_epochs_to_80pct": epoch_at_pct(trans_acc, 80),
            "cnn_final_loss": round(float(cnn_loss[-1]), 4),
            "transformer_final_loss": round(float(trans_loss[-1]), 4),
        }
    }
    plots = [
        {"plot_type": "line", "title": "Parametric Learning Curve: CNN vs Transformer Accuracy", "x_label": "Epoch", "y_label": "Accuracy (%)", "x": t.tolist(), "y": cnn_acc.tolist(), "series_name": "CNN (Parametric)", "extra_series": [{"y": trans_acc.tolist(), "name": "Transformer (Parametric)", "color": "#a855f7"}]},
        {"plot_type": "line", "title": "Parametric Learning Curve: Cross-Entropy Loss", "x_label": "Epoch", "y_label": "Loss", "x": t.tolist(), "y": cnn_loss.tolist(), "series_name": "CNN Loss", "extra_series": [{"y": trans_loss.tolist(), "name": "Transformer Loss", "color": "#a855f7"}]},
    ]
    visual_data = {
        "type": "neural_network", "architecture": "Deep CNN vs Vision Transformer",
        "layers": [
            {"id": "in", "name": "Input Layer", "type": "input", "nodes": 8, "shape": "32x32x3", "color": "#06b6d4"},
            {"id": "conv", "name": "Conv2D + ReLU", "type": "conv", "nodes": 12, "shape": "64 ch", "color": "#8b5cf6"},
            {"id": "attn", "name": "Multi-Head Attention", "type": "attention", "nodes": 8, "shape": "8 Heads", "color": "#f59e0b"},
            {"id": "out", "name": "Softmax Logits", "type": "output", "nodes": 4, "shape": "10 Classes", "color": "#10b981"},
        ],
        "metrics": numerical["model_comparison"],
    }
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "parametric_model",
        "engine_used": "cs_sim", "experiment_id": "model_comparison",
        "solver": {"name": "model_comparison", "version": "2.0", "method": "Parametric Exponential Learning-Curve Model", "equations": ["acc(t) = A_max * (1 - exp(-k*t))"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": visual_data, "visualization_type": "algorithm",
        "observations": [
            f"Parametric model: CNN reaches 80% at epoch {epoch_at_pct(cnn_acc, 80)}; Transformer peaks at {trans_acc[-1]:.2f}% vs CNN {cnn_acc[-1]:.2f}%.",
            "Note: Values come from a deterministic parametric learning-curve model, not empirical GPU training.",
        ],
        "assumptions": ["Analytical exponential convergence surrogate"], "limitations": ["Does not execute SGD training on CIFAR-10"],
        "warnings": ["Parametric analytical surrogate model — not empirical dataset training."],
        "simulation_log": ["[cs_sim] Parametric CNN vs Transformer learning-curve model evaluated"],
    }


def _dropout_effect(params: dict) -> Dict[str, Any]:
    dropout_rates = np.linspace(0.0, 0.7, 20)
    base_acc = float(params.get("base_accuracy", 89.0))
    optimal = float(params.get("optimal_dropout", 0.3))
    accuracy = base_acc * np.exp(-6.0 * (dropout_rates - optimal) ** 2)
    accuracy[0] = base_acc - 4.0
    accuracy = np.clip(accuracy, 40.0, base_acc)
    best_idx = int(np.argmax(accuracy))
    numerical = {
        "dropout_analysis": {
            "optimal_dropout_rate": round(float(dropout_rates[best_idx]), 2),
            "peak_accuracy_pct": round(float(accuracy[best_idx]), 2),
            "accuracy_at_0_pct": round(float(accuracy[0]), 2),
        }
    }
    plots = [{"plot_type": "line", "title": "Parametric Dropout Regularization Curve", "x_label": "Dropout Rate", "y_label": "Accuracy (%)", "x": dropout_rates.tolist(), "y": accuracy.tolist(), "series_name": "Accuracy"}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "parametric_model",
        "engine_used": "cs_sim", "experiment_id": "dropout_effect",
        "solver": {"name": "dropout_effect", "version": "2.0", "method": "Parametric Dropout Regularization Curve", "equations": ["acc(p) = A_base * exp(-6*(p - p_opt)^2)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": {"type": "neural_network", "architecture": "Regularized CNN", "layers": []}, "visualization_type": "neural_network",
        "observations": [f"Parametric optimum at dropout p={dropout_rates[best_idx]:.2f} -> {accuracy[best_idx]:.2f}%."],
        "assumptions": ["Gaussian parametric surrogate"], "limitations": ["Not empirical SGD"], "warnings": ["Parametric surrogate model."],
        "simulation_log": ["[cs_sim] Dropout parametric model evaluated"],
    }


def _neural_network_training(params: dict) -> Dict[str, Any]:
    epochs = int(params.get("epochs", 100))
    hidden_units = int(params.get("hidden_units", 128))
    lr = float(params.get("learning_rate", 0.001))
    t = np.arange(1, epochs + 1)
    speed = lr * 1000.0
    plateau = 95.0 - max(0.0, 10.0 - speed) * 2.0
    train_loss = 2.3 * np.exp(-0.07 * speed / 10.0 * t) + 0.08
    val_loss = 2.4 * np.exp(-0.06 * speed / 10.0 * t) + 0.12
    val_acc = plateau * (1.0 - np.exp(-0.06 * speed / 10.0 * t))
    numerical = {
        "training": {
            "final_val_accuracy_pct": round(float(val_acc[-1]), 2),
            "final_train_loss": round(float(train_loss[-1]), 4),
            "final_val_loss": round(float(val_loss[-1]), 4),
            "hidden_units": hidden_units, "learning_rate": lr, "total_epochs": epochs,
        }
    }
    plots = [{"plot_type": "line", "title": f"Parametric NN Convergence (LR={lr})", "x_label": "Epoch", "y_label": "Loss", "x": t.tolist(), "y": train_loss.tolist(), "series_name": "Train Loss", "extra_series": [{"y": val_loss.tolist(), "name": "Val Loss", "color": "#f59e0b"}]}]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "parametric_model",
        "engine_used": "cs_sim", "experiment_id": "neural_network_training",
        "solver": {"name": "neural_network_training", "version": "2.0", "method": "Parametric NN Loss/Accuracy Model", "equations": ["loss(t) = L0 * exp(-k*t) + L_inf"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": {"type": "neural_network", "architecture": "MLP", "layers": []}, "visualization_type": "neural_network",
        "observations": [f"Parametric NN final validation accuracy: {val_acc[-1]:.2f}%."],
        "assumptions": ["Exponential convergence surrogate"], "limitations": ["Not actual weight training"], "warnings": ["Parametric surrogate model."],
        "simulation_log": ["[cs_sim] Neural network parametric model evaluated"],
    }


# ─── Main Explicit Dispatcher ────────────────────────────────────────────────

_CS_DISPATCH = {
    "breadth_first_search": _run_bfs,
    "bfs": _run_bfs,
    "depth_first_search": _run_dfs,
    "dfs": _run_dfs,
    "dijkstra_shortest_path": _run_dijkstra,
    "dijkstra": _run_dijkstra,
    "shortest_path": _run_dijkstra,
    "connected_components": _run_connected_components,
    "topological_sort": _run_topological_sort,
    "topo_sort": _run_topological_sort,
    "bubble_sort": lambda p: _run_sorting("bubble_sort", p),
    "selection_sort": lambda p: _run_sorting("selection_sort", p),
    "insertion_sort": lambda p: _run_sorting("insertion_sort", p),
    "merge_sort": lambda p: _run_sorting("merge_sort", p),
    "mergesort": lambda p: _run_sorting("merge_sort", p),
    "quick_sort": lambda p: _run_sorting("quick_sort", p),
    "quicksort": lambda p: _run_sorting("quick_sort", p),
    "heap_sort": lambda p: _run_sorting("heap_sort", p),
    "heapsort": lambda p: _run_sorting("heap_sort", p),
    "linear_search": _run_linear_search,
    "binary_search": _run_binary_search,
    "algorithm_complexity": _algorithm_complexity,
    "big_o": _algorithm_complexity,
    "model_comparison": _model_comparison,
    "dropout_effect": _dropout_effect,
    "neural_network_training": _neural_network_training,
    "neural_network": _neural_network_training,
    "nn_training": _neural_network_training,
}


def run(procedure: dict) -> dict:
    """Explicit CS dispatcher. Executes real algorithms instead of complexity curves."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    # If generic/blank experiment_type, detect exact algorithm explicitly
    if exp_type in ("", "computer_science", "cs", "machine_learning", "ml", "algorithm"):
        if any(w in text for w in ("breadth-first", "breadth first", " bfs ", "bfs")):
            exp_type = "breadth_first_search"
        elif any(w in text for w in ("depth-first", "depth first", " dfs ", "dfs")):
            exp_type = "depth_first_search"
        elif any(w in text for w in ("dijkstra", "shortest path")):
            exp_type = "dijkstra_shortest_path"
        elif "connected component" in text:
            exp_type = "connected_components"
        elif "topological" in text or "kahn" in text:
            exp_type = "topological_sort"
        elif "bubble sort" in text or "bubblesort" in text:
            exp_type = "bubble_sort"
        elif "selection sort" in text:
            exp_type = "selection_sort"
        elif "insertion sort" in text:
            exp_type = "insertion_sort"
        elif "merge sort" in text or "mergesort" in text:
            exp_type = "merge_sort"
        elif "quick sort" in text or "quicksort" in text:
            exp_type = "quick_sort"
        elif "heap sort" in text or "heapsort" in text:
            exp_type = "heap_sort"
        elif "binary search" in text:
            exp_type = "binary_search"
        elif "linear search" in text:
            exp_type = "linear_search"
        elif any(w in text for w in ("cnn", "transformer", "vit", "resnet")):
            exp_type = "model_comparison"
        elif any(w in text for w in ("dropout", "regulariz")):
            exp_type = "dropout_effect"
        elif any(w in text for w in ("big-o", "big o", "asymptotic", "complexity")):
            exp_type = "algorithm_complexity"
        elif any(w in text for w in ("neural network", "backprop", "epoch")):
            exp_type = "neural_network_training"

    solver_fn = _CS_DISPATCH.get(exp_type)
    if solver_fn is None:
        return build_unsupported_response(
            procedure,
            reason=f"Computer science experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
            supported_examples=[
                "breadth_first_search", "depth_first_search", "dijkstra_shortest_path",
                "connected_components", "topological_sort", "bubble_sort", "selection_sort",
                "insertion_sort", "merge_sort", "quick_sort", "heap_sort",
                "linear_search", "binary_search", "algorithm_complexity",
            ],
        )

    return solver_fn(params)
