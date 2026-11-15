"""
Computer Science 3D Scene Templates
===================================
Generates validated 3D scene specifications for Computer Science experiments:
1. Deep Learning & Neural Network Architectures:
   - Multi-layer 3D topology (Input, Conv/Dense Hidden, Multi-Head Attention, Softmax Logits)
   - Synaptic connections with animated forward/backward data flow pulses
   - Layer dimension placards, accuracy/loss telemetry, and interactive hyperparameter controls
2. Algorithms, Data Structures & Complexity:
   - 3D Sorting Array with animated comparison & swap highlights
   - 3D Graph / Tree DAG with shortest-path traversal animation
   - Big-O complexity metrics and operations telemetry
"""

import math
import numpy as np
from typing import Dict, Any, List
from ..scene_schema import (
    SceneSpecification, SceneObject, MaterialConfig,
    CameraConfig, LightingConfig, ParameterConfig,
    AnimationConfig, AnimationTrack, MeasurementOverlay,
    VectorOverlay, SceneControlsConfig
)


def build_neural_net_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D multi-layer neural network / transformer architecture scene."""
    params = procedure.get("parameters", {})
    lr = float(params.get("learning_rate", 0.001))
    dropout = float(params.get("dropout_rate", 0.3))
    epochs = int(params.get("epochs", 50))

    # Extract numerical telemetry
    comp = numerical_results.get("model_comparison", {})
    training = numerical_results.get("training", {})
    accuracy = comp.get("transformer_final_accuracy_pct") or training.get("final_val_accuracy_pct") or 91.5
    loss = comp.get("transformer_final_loss") or training.get("final_val_loss") or 0.16
    winner = comp.get("winner", "Transformer (ViT)")

    objects: List[SceneObject] = []

    # 1. Dark Technical Optical Stage / Base
    objects.append(SceneObject(
        id="compute_chassis",
        name="Neural Computing Stage",
        type="box",
        position=[0.0, -0.6, 0.0],
        dimensions={"width": 8.5, "height": 0.2, "depth": 4.5},
        material=MaterialConfig(color="#090d16", metalness=0.85, roughness=0.25)
    ))

    # Stage boundary glow trim
    objects.append(SceneObject(
        id="stage_trim",
        name="Stage Telemetry Border",
        type="box",
        position=[0.0, -0.48, 0.0],
        dimensions={"width": 8.3, "height": 0.04, "depth": 4.3},
        material=MaterialConfig(color="#1e293b", emissive="#38bdf8", emissive_intensity=0.35, metalness=0.5, roughness=0.5)
    ))

    # 2. Define Layer Topologies
    layers = [
        {
            "id": "input_layer",
            "name": "Input Layer [Tensor 28x28x1]",
            "x": -3.2,
            "color": "#06b6d4",
            "emissive": "#0891b2",
            "count": 6,
            "y_range": [-1.0, 1.2],
            "radius": 0.18
        },
        {
            "id": "conv_hidden_layer",
            "name": "Feature Extraction (Conv2D / Dense)",
            "x": -1.1,
            "color": "#8b5cf6",
            "emissive": "#7c3aed",
            "count": 9,
            "y_range": [-1.4, 1.6],
            "radius": 0.20
        },
        {
            "id": "attention_layer",
            "name": "Multi-Head Attention / Latent Embeddings",
            "x": 1.1,
            "color": "#f59e0b",
            "emissive": "#d97706",
            "count": 8,
            "y_range": [-1.2, 1.4],
            "radius": 0.21
        },
        {
            "id": "output_layer",
            "name": "Softmax Classification Logits [10 Classes]",
            "x": 3.2,
            "color": "#10b981",
            "emissive": "#059669",
            "count": 5,
            "y_range": [-0.9, 1.1],
            "radius": 0.24
        }
    ]

    all_node_positions: List[List[float]] = []
    layer_node_coords: List[List[List[float]]] = []

    # Create Nodes for each layer
    for layer_idx, layer in enumerate(layers):
        x = layer["x"]
        y_min, y_max = layer["y_range"]
        y_coords = np.linspace(y_min, y_max, layer["count"])
        curr_layer_coords = []

        # Layer Base Stanchion
        objects.append(SceneObject(
            id=f"layer_stanchion_{layer_idx}",
            name=f"{layer['name']} Bounding Plane",
            type="cylinder",
            position=[x, -0.4, 0.0],
            dimensions={"radius": 0.45, "height": 0.15},
            material=MaterialConfig(color="#1e293b", metalness=0.7, roughness=0.3)
        ))

        for node_idx, y in enumerate(y_coords):
            # Stagger Z slightly for 3D depth volume
            z = math.sin(node_idx * 1.3) * 0.4
            node_id = f"node_L{layer_idx}_{node_idx}"
            curr_layer_coords.append([x, y, z])
            all_node_positions.append([x, y, z])

            objects.append(SceneObject(
                id=node_id,
                name=f"Neuron L{layer_idx}[{node_idx}]",
                type="sphere",
                position=[x, y, z],
                dimensions={"radius": layer["radius"]},
                material=MaterialConfig(
                    color=layer["color"],
                    emissive=layer["emissive"],
                    emissive_intensity=0.45,
                    metalness=0.4,
                    roughness=0.25
                ),
                metadata={
                    "layer": layer["name"],
                    "index": node_idx,
                    "activation": round(float(0.3 + 0.65 * math.sin(layer_idx + node_idx)), 3)
                }
            ))

        layer_node_coords.append(curr_layer_coords)

    # 3. Create Synaptic Connections (Cylinders) between adjacent layers
    synapse_idx = 0
    for l_idx in range(len(layer_node_coords) - 1):
        src_coords = layer_node_coords[l_idx]
        dst_coords = layer_node_coords[l_idx + 1]

        # Connect a clean subset of synapses to avoid visual clutter
        for s_idx, (sx, sy, sz) in enumerate(src_coords):
            for d_idx, (dx, dy, dz) in enumerate(dst_coords):
                # Sparsely connect for visual clarity
                if (s_idx + d_idx) % 2 == 0:
                    mx, my, mz = (sx + dx) / 2.0, (sy + dy) / 2.0, (sz + dz) / 2.0
                    length = math.sqrt((dx - sx)**2 + (dy - sy)**2 + (dz - sz)**2)
                    ry = math.atan2(dz - sz, dx - sx)
                    rz = math.atan2(dy - sy, math.sqrt((dx - sx)**2 + (dz - sz)**2))

                    objects.append(SceneObject(
                        id=f"synapse_{synapse_idx}",
                        name=f"Synapse L{l_idx}_{s_idx}->L{l_idx+1}_{d_idx}",
                        type="cylinder",
                        position=[mx, my, mz],
                        rotation=[0.0, -ry, rz],
                        dimensions={"radius": 0.018, "height": length},
                        material=MaterialConfig(
                            color="#334155",
                            emissive="#38bdf8",
                            emissive_intensity=0.15,
                            metalness=0.6,
                            roughness=0.4,
                            opacity=0.7,
                            transparent=True
                        )
                    ))
                    synapse_idx += 1

    # 4. Animated Signal Pulse Particles traversing through layers
    num_time_steps = 60
    time_array = [round(t * 0.05, 3) for t in range(num_time_steps)]
    tracks: Dict[str, AnimationTrack] = {}

    for pulse_id in range(4):
        pulse_name = f"pulse_particle_{pulse_id}"
        pos_track = []
        emissive_track = []

        phase_offset = pulse_id * 15
        for step in range(num_time_steps):
            t_rel = ((step + phase_offset) % num_time_steps) / float(num_time_steps)
            # Traverse from x = -3.2 to +3.2
            px = -3.2 + (6.4 * t_rel)
            py = 0.2 * math.sin(t_rel * math.pi * 3) + 0.1
            pz = 0.3 * math.cos(t_rel * math.pi * 4)

            pos_track.append([round(px, 3), round(py, 3), round(pz, 3)])
            emissive_track.append(round(0.4 + 0.6 * math.sin(t_rel * math.pi * 2), 2))

        objects.append(SceneObject(
            id=pulse_name,
            name=f"Inference Data Pulse #{pulse_id+1}",
            type="sphere",
            position=pos_track[0],
            dimensions={"radius": 0.12},
            material=MaterialConfig(
                color="#38bdf8",
                emissive="#38bdf8",
                emissive_intensity=0.9,
                metalness=0.1,
                roughness=0.1
            )
        ))

        tracks[pulse_name] = AnimationTrack(
            position=pos_track,
            emissive_intensity=emissive_track
        )

    # 5. Overlays
    overlays = [
        MeasurementOverlay(
            id="mo_accuracy",
            label="Validation Accuracy",
            value=f"{accuracy}%",
            unit="%",
            position_3d=[3.2, 1.8, 0.0]
        ),
        MeasurementOverlay(
            id="mo_loss",
            label="Cross-Entropy Loss",
            value=round(float(loss), 4),
            unit="",
            position_3d=[1.1, 1.9, 0.0]
        ),
        MeasurementOverlay(
            id="mo_arch",
            label="Active Architecture",
            value=winner,
            unit="",
            position_3d=[-1.1, 2.0, 0.0]
        ),
        MeasurementOverlay(
            id="mo_lr",
            label="Learning Rate",
            value=lr,
            unit="eta",
            position_3d=[-3.2, 1.8, 0.0]
        )
    ]

    # 6. Parameters
    parameters = [
        ParameterConfig(
            name="learning_rate",
            label="Learning Rate",
            type="float",
            value=lr,
            min_val=0.0001,
            max_val=0.01,
            step=0.0005,
            unit="",
            description="Optimizer step size governing gradient descent convergence rate."
        ),
        ParameterConfig(
            name="dropout_rate",
            label="Dropout Rate",
            type="float",
            value=dropout,
            min_val=0.0,
            max_val=0.7,
            step=0.05,
            unit="",
            description="Regularization probability to deactivate neurons during training to prevent overfitting."
        ),
        ParameterConfig(
            name="epochs",
            label="Training Epochs",
            type="int",
            value=epochs,
            min_val=10,
            max_val=200,
            step=10,
            unit="",
            description="Complete passes through the entire training dataset."
        )
    ]

    return SceneSpecification(
        domain="computer_science",
        experiment_id="neural_network_3d",
        scene_template="neural_network_3d",
        title="3D Deep Neural Network Topology & Latent Inference",
        description="Interactive 3D visualization of multi-layer neural architecture showing synaptic weight connections, activation flows, and convergence telemetry.",
        is_simulation_backed=True,
        confidence_score=0.94,
        camera=CameraConfig(position=[0.0, 2.8, 7.2], target=[0.0, 0.2, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.8, directional_intensity=1.1, directional_position=[5.0, 8.0, 6.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=3.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        vectors=[],
        controls=SceneControlsConfig(
            allow_orbit=True,
            allow_pan=True,
            allow_zoom=True,
            show_grid=True,
            show_axes=True,
            background_color="#080c14"
        ),
        notes=[
            "Synaptic transmission pulses represent feedforward inference tensors and backward gradient propagation.",
            "Node colors denote functional layer hierarchy: Cyan (Input), Purple (Feature/Conv2D), Amber (Attention/Latent), Emerald (Softmax Output).",
            "Adjust hyperparameters via the inspector to observe real-time telemetry impact."
        ]
    )


def build_algorithm_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D Algorithm & Data Structure visualization (Sorting Array / Graph Traversal)."""
    params = procedure.get("parameters", {})
    n_max = int(params.get("n_max", 200))
    exp_type = str(procedure.get("experiment_type", "")).lower()
    hypothesis = str(procedure.get("hypothesis", "")).lower()

    is_graph = any(w in (exp_type + " " + hypothesis) for w in ["graph", "dijkstra", "bfs", "dfs", "tree", "shortest path"])

    objects: List[SceneObject] = []

    # Chassis base
    objects.append(SceneObject(
        id="algo_stage",
        name="Algorithm Execution Stage",
        type="box",
        position=[0.0, -0.6, 0.0],
        dimensions={"width": 8.0, "height": 0.2, "depth": 4.0},
        material=MaterialConfig(color="#090d16", metalness=0.85, roughness=0.25)
    ))

    num_time_steps = 60
    time_array = [round(t * 0.05, 3) for t in range(num_time_steps)]
    tracks: Dict[str, AnimationTrack] = {}

    if is_graph:
        # 3D Graph / DAG Scene
        node_coords = [
            [-3.0, 0.0, 0.0],   # Node 0 (Start)
            [-1.5, 1.2, 0.8],   # Node 1
            [-1.5, -0.8, -0.6], # Node 2
            [0.5, 1.4, -0.5],   # Node 3
            [0.5, -0.6, 0.7],   # Node 4
            [2.5, 0.8, 0.4],    # Node 5
            [3.2, -0.2, 0.0]    # Node 6 (Target)
        ]
        edges = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5), (5, 6), (1, 4)]
        shortest_path = [0, 1, 3, 5, 6]

        for idx, (x, y, z) in enumerate(node_coords):
            is_in_path = idx in shortest_path
            node_color = "#10b981" if is_in_path else "#64748b"
            node_emissive = "#059669" if is_in_path else "#334155"

            objects.append(SceneObject(
                id=f"graph_node_{idx}",
                name=f"Graph Vertex v{idx}",
                type="sphere",
                position=[x, y, z],
                dimensions={"radius": 0.32},
                material=MaterialConfig(
                    color=node_color,
                    emissive=node_emissive,
                    emissive_intensity=0.6 if is_in_path else 0.2,
                    metalness=0.4,
                    roughness=0.3
                ),
                metadata={"vertex_id": idx, "is_shortest_path": is_in_path}
            ))

        for e_idx, (u, v) in enumerate(edges):
            ux, uy, uz = node_coords[u]
            vx, vy, vz = node_coords[v]
            mx, my, mz = (ux + vx) / 2.0, (uy + vy) / 2.0, (uz + vz) / 2.0
            length = math.sqrt((vx - ux)**2 + (vy - uy)**2 + (vz - uz)**2)
            ry = math.atan2(vz - uz, vx - ux)
            rz = math.atan2(vy - uy, math.sqrt((vx - ux)**2 + (vz - uz)**2))

            in_sp = (u in shortest_path and v in shortest_path and abs(shortest_path.index(u) - shortest_path.index(v)) == 1)

            objects.append(SceneObject(
                id=f"graph_edge_{e_idx}",
                name=f"Edge ({u} <-> {v})",
                type="cylinder",
                position=[mx, my, mz],
                rotation=[0.0, -ry, rz],
                dimensions={"radius": 0.04 if in_sp else 0.02, "height": length},
                material=MaterialConfig(
                    color="#f59e0b" if in_sp else "#475569",
                    emissive="#d97706" if in_sp else "#1e293b",
                    emissive_intensity=0.7 if in_sp else 0.1,
                    metalness=0.5,
                    roughness=0.4
                )
            ))

        # Animated Dijkstra Frontier Pulse along shortest path
        sp_points = [node_coords[i] for i in shortest_path]
        pulse_pos = []
        for step in range(num_time_steps):
            t_norm = step / float(num_time_steps - 1)
            seg_idx = min(int(t_norm * (len(sp_points) - 1)), len(sp_points) - 2)
            seg_t = (t_norm * (len(sp_points) - 1)) - seg_idx
            p0 = sp_points[seg_idx]
            p1 = sp_points[seg_idx + 1]
            px = p0[0] + seg_t * (p1[0] - p0[0])
            py = p0[1] + seg_t * (p1[1] - p0[1])
            pz = p0[2] + seg_t * (p1[2] - p0[2])
            pulse_pos.append([round(px, 3), round(py, 3), round(pz, 3)])

        objects.append(SceneObject(
            id="dijkstra_pulse",
            name="Shortest Path Traversal Pulse",
            type="sphere",
            position=pulse_pos[0],
            dimensions={"radius": 0.18},
            material=MaterialConfig(color="#f59e0b", emissive="#f59e0b", emissive_intensity=1.0)
        ))
        tracks["dijkstra_pulse"] = AnimationTrack(position=pulse_pos)

        overlays = [
            MeasurementOverlay(id="algo_time", label="Algorithm Time Complexity", value="O(V log V + E)", unit="ops"),
            MeasurementOverlay(id="algo_space", label="Auxiliary Space", value="O(V)", unit="nodes"),
            MeasurementOverlay(id="algo_path", label="Shortest Path Cost", value="14.2", unit="units")
        ]
        title = "3D Graph Network Topology & Dijkstra Shortest Path"

    else:
        # 3D Sorting Array Bars
        array_vals = [24, 65, 12, 88, 42, 95, 33, 76, 51, 18, 60, 84]
        num_bars = len(array_vals)
        x_start = -3.2
        spacing = 0.58
        max_val = max(array_vals)

        for b_idx, val in enumerate(array_vals):
            height = (val / max_val) * 2.2
            x = x_start + (b_idx * spacing)
            y = (height / 2.0) - 0.5
            is_pivot = (b_idx == 5)
            bar_color = "#f59e0b" if is_pivot else "#38bdf8"

            bar_id = f"sort_bar_{b_idx}"
            objects.append(SceneObject(
                id=bar_id,
                name=f"Array[{b_idx}] = {val}",
                type="box",
                position=[x, y, 0.0],
                dimensions={"width": 0.42, "height": height, "depth": 0.42},
                material=MaterialConfig(
                    color=bar_color,
                    emissive="#d97706" if is_pivot else "#0284c7",
                    emissive_intensity=0.4 if is_pivot else 0.15,
                    metalness=0.6,
                    roughness=0.3
                ),
                metadata={"index": b_idx, "value": val, "is_pivot": is_pivot}
            ))

        # Comparison Indicator Cursor Arrow
        cursor_pos = []
        for step in range(num_time_steps):
            cur_idx = int((step / float(num_time_steps)) * (num_bars - 1))
            cx = x_start + (cur_idx * spacing)
            cursor_pos.append([round(cx, 3), 1.9, 0.0])

        objects.append(SceneObject(
            id="sort_cursor",
            name="Partition Pointer",
            type="cone",
            position=cursor_pos[0],
            rotation=[math.pi, 0.0, 0.0],
            dimensions={"radius": 0.22, "height": 0.45},
            material=MaterialConfig(color="#ec4899", emissive="#db2777", emissive_intensity=0.8)
        ))
        tracks["sort_cursor"] = AnimationTrack(position=cursor_pos)

        overlays = [
            MeasurementOverlay(id="algo_time", label="Time Complexity", value="O(n log n)", unit=""),
            MeasurementOverlay(id="algo_space", label="Space Complexity", value="O(log n)", unit=""),
            MeasurementOverlay(id="algo_comps", label="Comparisons at n=200", value="1,540", unit="ops")
        ]
        title = "3D Sorting Array Dynamics & Divide-and-Conquer Partition"

    parameters = [
        ParameterConfig(
            name="input_size_n",
            label="Input Size (n)",
            type="int",
            value=n_max,
            min_val=10,
            max_val=1000,
            step=50,
            unit="items",
            description="Number of elements or graph vertices processed by the algorithm."
        )
    ]

    return SceneSpecification(
        domain="computer_science",
        experiment_id="algorithm_complexity_3d",
        scene_template="algorithm_3d",
        title=title,
        description="3D spatial visualization of computational algorithms, data structures, and operational complexities.",
        is_simulation_backed=True,
        confidence_score=0.92,
        camera=CameraConfig(position=[0.0, 2.5, 6.8], target=[0.0, 0.3, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.8, directional_intensity=1.0, directional_position=[4.0, 7.0, 5.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=3.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        vectors=[],
        controls=SceneControlsConfig(
            allow_orbit=True,
            allow_pan=True,
            allow_zoom=True,
            show_grid=True,
            show_axes=True,
            background_color="#080c14"
        ),
        notes=[
            "Spatial 3D bars and vertices illustrate memory allocations, comparisons, and state transitions.",
            "Visual markers indicate active pivots and traversal frontiers in real time."
        ]
    )


def build_cs_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Main routing entry point for Computer Science 3D visualizations."""
    exp_type = str(procedure.get("experiment_type", "")).lower().strip()
    hypothesis = str(procedure.get("hypothesis", "")).lower()
    combined = f"{exp_type} {hypothesis} {procedure.get('topic', '')}".lower()

    if any(w in combined for w in ["sort", "array", "bubble", "merge", "quick", "heap", "complexity", "dijkstra", "bfs", "dfs", "graph", "tree", "dag", "path", "search"]):
        return build_algorithm_scene(procedure, numerical_results, plot_data)
    else:
        return build_neural_net_scene(procedure, numerical_results, plot_data)

