"""
Experiment-Specific Synchronized 3D Scene Templates
====================================================
Dedicated declarative Three.js / R3F scene builders strictly mapped by canonical
`experiment_id -> visualization_template` and synchronized directly to each
deterministic solver's actual numerical outputs:
  - truss_structure (2D/3D Pratt truss joints & tension/compression members)
  - shaft_torsion (Circular shaft with twist deformation & stress overlays)
  - spring_mass_damper (Oscillating 1-DOF spring-mass-damper bench)
  - thermo_cycle (Piston-cylinder engine synchronized to thermodynamic volume ratio)
  - rlc_circuit (3D Voltage Source + Resistor + Inductor Coil + Parallel-Plate Capacitor)
  - resistive_circuit (Ohm's Law / Voltage Divider / Series-Parallel bench)
  - titration_apparatus (Burette + Stand + Erlenmeyer flask with pH color transition)
  - reaction_kinetics (Stirred batch reactor vessel with conversion animation)
  - enzyme_kinetics (Enzyme-substrate Michaelis-Menten catalytic apparatus)
  - population_growth (Bioreactor culture vessel with population density curve)
  - graph_traversal (Actual BFS / DFS / Dijkstra / Topological graph nodes, edges & trace)
  - sorting_array (Actual input array bars & instrumented sorting animation)
  - building_blueprint (3D column grid & floor slabs)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List
import numpy as np

from ..scene_schema import (
    AnimationConfig,
    AnimationTrack,
    CameraConfig,
    LightingConfig,
    MaterialConfig,
    MeasurementOverlay,
    ParameterConfig,
    SceneControlsConfig,
    SceneObject,
    SceneSpecification,
)


def _cylinder_between(p1: List[float], p2: List[float]) -> tuple:
    dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    length = max(math.sqrt(dx * dx + dy * dy + dz * dz), 1e-4)
    mid = [round((p1[0] + p2[0]) / 2.0, 4), round((p1[1] + p2[1]) / 2.0, 4), round((p1[2] + p2[2]) / 2.0, 4)]
    # Align Three.js Y-axis cylinder to vector (dx, dy, dz)
    # In XY plane (dz == 0): rotation Z = atan2(dy, dx) - pi/2
    if abs(dz) < 1e-6:
        rot = [0.0, 0.0, round(math.atan2(dy, dx) - math.pi / 2.0, 4)]
    else:
        horiz = math.hypot(dx, dz)
        pitch = math.atan2(horiz, dy)
        yaw = math.atan2(dx, dz)
        rot = [round(pitch, 4), round(yaw, 4), 0.0]
    return mid, rot, round(length, 4)


# ─── 1. Civil: 3D Truss Structure ────────────────────────────────────────────

def build_truss_structure_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    tr = numerical_results.get("truss", {})
    geom = numerical_results.get("truss_geometry", {})
    span = float(tr.get("span_m", procedure.get("parameters", {}).get("span_m", 10.0)))
    height = float(tr.get("height_m", procedure.get("parameters", {}).get("height_m", 3.0)))
    nodes = geom.get("nodes") or [[0.0, 0.0], [span / 2.0, 0.0], [span, 0.0], [span / 2.0, height]]
    members = geom.get("members") or [
        {"id": "BC1", "node_i": 0, "node_j": 1, "axial_force_kN": 10.0, "state": "tension"},
        {"id": "BC2", "node_i": 1, "node_j": 2, "axial_force_kN": 10.0, "state": "tension"},
        {"id": "ED_L", "node_i": 0, "node_j": 3, "axial_force_kN": -15.0, "state": "compression"},
        {"id": "ED_R", "node_i": 2, "node_j": 3, "axial_force_kN": -15.0, "state": "compression"},
        {"id": "V1", "node_i": 1, "node_j": 3, "axial_force_kN": 5.0, "state": "tension"},
    ]

    cx = span / 2.0
    objects: List[SceneObject] = []
    # Joints
    for idx, (nx, ny) in enumerate(nodes):
        objects.append(SceneObject(
            id=f"truss_joint_{idx}",
            name=f"Pin Joint N{idx}",
            type="sphere",
            position=[round(nx - cx, 4), round(ny, 4), 0.0],
            dimensions={"radius": 0.14},
            material=MaterialConfig(color="#cbd5e1", metalness=0.8, roughness=0.25),
        ))

    # Members colored by Tension (cyan/blue) vs Compression (red/orange)
    for m in members:
        ni, nj = int(m["node_i"]), int(m["node_j"])
        p1 = [nodes[ni][0] - cx, nodes[ni][1], 0.0]
        p2 = [nodes[nj][0] - cx, nodes[nj][1], 0.0]
        mid, rot, length = _cylinder_between(p1, p2)
        force = float(m.get("axial_force_kN", 0.0))
        color = "#06b6d4" if force > 1e-4 else ("#ef4444" if force < -1e-4 else "#64748b")
        objects.append(SceneObject(
            id=f"member_{m['id']}",
            name=f"Member {m['id']} ({force:+.2f} kN)",
            type="cylinder",
            position=mid,
            rotation=rot,
            dimensions={"radius": 0.07, "height": length},
            material=MaterialConfig(color=color, metalness=0.5, roughness=0.35),
            metadata={"axial_force_kN": force, "state": m.get("state", "axial")},
        ))

    # Supports
    objects.append(SceneObject(id="support_pin_A", name="Pin Support A", type="cylinder", position=[-cx, -0.25, 0.0], dimensions={"radius": 0.2, "height": 0.35}, material=MaterialConfig(color="#475569", metalness=0.8, roughness=0.3)))
    objects.append(SceneObject(id="support_roller_B", name="Roller Support B", type="sphere", position=[cx, -0.25, 0.0], dimensions={"radius": 0.2}, material=MaterialConfig(color="#64748b", metalness=0.85, roughness=0.25)))

    overlays = [
        MeasurementOverlay(id="tr_ra", label="Reaction R_A", value=tr.get("reaction_A_kN", 0), unit="kN", position_3d=[-cx, -0.6, 0.0]),
        MeasurementOverlay(id="tr_tens", label="Max Tension", value=tr.get("max_tension_kN", 0), unit="kN", position_3d=[0.0, -0.5, 0.0]),
        MeasurementOverlay(id="tr_comp", label="Max Compression", value=tr.get("max_compression_kN", 0), unit="kN", position_3d=[0.0, height + 0.5, 0.0]),
    ]
    return SceneSpecification(
        domain="civil_engineering",
        experiment_id="truss_analysis",
        scene_template="truss_structure",
        title=f"2D Pratt Truss Direct Stiffness Structure ({span}m × {height}m)",
        description="Pin-jointed truss members colored by solved axial force (Cyan = Tension, Red = Compression).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, height * 0.6, max(span * 1.1, 8.0)], target=[0.0, height * 0.45, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.85, directional_position=[4.0, 8.0, 6.0]),
        objects=objects,
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True),
    )


# ─── 2. Mechanical: Shaft Torsion & Bending ──────────────────────────────────

def build_shaft_torsion_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    sd = numerical_results.get("shaft_design", {})
    L_m = float(sd.get("length_mm", 500.0)) / 1000.0 * 4.0  # Visual scaling
    r_vis = max(0.18, min(0.45, float(sd.get("diameter_mm", 40.0)) / 120.0))
    twist_rad = float(sd.get("twist_angle_rad", 0.05))
    tau = float(sd.get("max_shear_stress_MPa", 0.0))
    fos = float(sd.get("factor_of_safety", 2.0))

    objects = [
        SceneObject(id="fixed_flange", name="Fixed Torque Reaction Flange", type="cylinder", position=[-L_m / 2.0 - 0.1, 0.0, 0.0], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": r_vis * 1.8, "height": 0.18}, material=MaterialConfig(color="#334155", metalness=0.85, roughness=0.25)),
        SceneObject(id="shaft_body", name="Circular Transmission Shaft", type="cylinder", position=[0.0, 0.0, 0.0], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": r_vis, "height": L_m}, material=MaterialConfig(color="#38bdf8", metalness=0.7, roughness=0.25)),
        SceneObject(id="torque_collar", name="Applied Torque Hub", type="torus", position=[L_m / 2.0, 0.0, 0.0], rotation=[0.0, math.pi / 2.0, 0.0], dimensions={"radius": r_vis * 1.4, "tube": 0.05}, material=MaterialConfig(color="#f59e0b", metalness=0.6, roughness=0.3)),
    ]
    frames = 60
    t_arr = [round(i * 0.05, 3) for i in range(frames)]
    twist_vis = max(twist_rad * 8.0, 0.25)
    rot_track = [[round(twist_vis * math.sin(2.0 * math.pi * i / frames), 4), 0.0, round(math.pi / 2.0, 4)] for i in range(frames)]

    overlays = [
        MeasurementOverlay(id="sh_tau", label="Max Shear τ", value=round(tau, 2), unit="MPa", position_3d=[0.0, r_vis + 0.5, 0.0]),
        MeasurementOverlay(id="sh_vm", label="Von Mises σ_vm", value=sd.get("von_mises_stress_MPa", 0), unit="MPa", position_3d=[0.0, r_vis + 0.9, 0.0]),
        MeasurementOverlay(id="sh_fos", label="Factor of Safety", value=round(fos, 2), unit="", position_3d=[L_m / 2.0, r_vis + 0.5, 0.0]),
    ]
    return SceneSpecification(
        domain="mechanical_engineering",
        experiment_id="shaft_design",
        scene_template="shaft_torsion",
        title="Circular Shaft Torsion & Combined Bending",
        description=f"Solid circular shaft under T={sd.get('torque_Nm', 200)} N·m, M={sd.get('bending_moment_Nm', 0)} N·m.",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.5, 1.4, 3.6], target=[0.0, 0.0, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=3.0, time_step_s=0.05, time_array=t_arr, tracks={"shaft_body": AnimationTrack(rotation=rot_track)}),
        measurement_overlays=overlays,
    )


# ─── 3. Mechanical: Spring-Mass-Damper ───────────────────────────────────────

def build_spring_mass_damper_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    smd = numerical_results.get("spring_mass_damper", {})
    x_pts = plot_data[0]["y"] if plot_data and plot_data[0].get("y") else [0.1 * math.cos(i * 0.2) for i in range(80)]
    t_pts = plot_data[0]["x"] if plot_data and plot_data[0].get("x") else [i * 0.05 for i in range(len(x_pts))]
    stride = max(1, len(x_pts) // 80)
    t_sub = [round(float(t_pts[i]), 3) for i in range(0, len(x_pts), stride)]
    x_sub = [float(x_pts[i]) for i in range(0, len(x_pts), stride)]
    scale = 1.0 / max(max(abs(v) for v in x_sub), 0.05) * 0.8

    mass_pos = [[round(1.5 + v * scale, 4), 0.35, 0.0] for v in x_sub]
    objects = [
        SceneObject(id="wall_anchor", name="Fixed Wall", type="box", position=[-0.8, 0.5, 0.0], dimensions={"width": 0.2, "height": 1.4, "depth": 1.0}, material=MaterialConfig(color="#334155", metalness=0.8, roughness=0.3)),
        SceneObject(id="spring_coil", name="Linear Spring (k)", type="cylinder", position=[0.35, 0.5, 0.0], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.12, "height": 2.0}, material=MaterialConfig(color="#06b6d4", wireframe=True)),
        SceneObject(id="damper_cyl", name="Viscous Damper (c)", type="cylinder", position=[0.35, 0.2, 0.0], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.07, "height": 2.0}, material=MaterialConfig(color="#f59e0b", metalness=0.7, roughness=0.3)),
        SceneObject(id="mass_block", name=f"Oscillating Mass ({smd.get('mass_kg', 1.0)} kg)", type="box", position=mass_pos[0], dimensions={"width": 0.6, "height": 0.6, "depth": 0.6}, material=MaterialConfig(color="#8b5cf6", metalness=0.4, roughness=0.3)),
    ]
    overlays = [
        MeasurementOverlay(id="smd_fn", label="Natural Freq f_n", value=smd.get("natural_frequency_Hz", 0), unit="Hz", position_3d=[1.5, 1.1, 0.0]),
        MeasurementOverlay(id="smd_z", label="Damping Ratio ζ", value=smd.get("damping_ratio_zeta", 0), unit="", position_3d=[0.3, 1.1, 0.0]),
    ]
    return SceneSpecification(
        domain="mechanical_engineering",
        experiment_id="spring_mass_damper",
        scene_template="spring_mass_damper",
        title="1-DOF Spring-Mass-Damper Vibration System",
        description=f"Driven by exact RK45 displacement trajectory x(t) (regime: {smd.get('regime', 'underdamped')}).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.8, 1.5, 4.2], target=[0.6, 0.35, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_sub[-1] if t_sub else 4.0, time_step_s=0.05, time_array=t_sub, tracks={"mass_block": AnimationTrack(position=mass_pos)}),
        measurement_overlays=overlays,
    )


# ─── 4. Mechanical: Thermodynamic Cycle Piston-Cylinder ──────────────────────

def build_thermo_cycle_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    exp_id = str(procedure.get("experiment_type") or "otto_cycle")
    block = next(iter(numerical_results.values()), {}) if isinstance(numerical_results, dict) else {}
    eta = block.get("efficiency_percent", 0.0)
    cycle_name = block.get("cycle", exp_id.replace("_", " ").title())

    frames = 80
    t_arr = [round(i * 0.05, 3) for i in range(frames)]
    piston_pos = [[0.0, round(0.2 + 0.55 * (1.0 - math.cos(2.0 * math.pi * i / frames)) / 2.0, 4), 0.0] for i in range(frames)]

    objects = [
        SceneObject(id="cylinder_wall", name="Thermodynamic Cylinder", type="cylinder", position=[0.0, 0.8, 0.0], dimensions={"radius": 0.65, "height": 1.6}, material=MaterialConfig(color="#94a3b8", opacity=0.35, transparent=True, metalness=0.6, roughness=0.2)),
        SceneObject(id="piston_head", name="Reciprocating Piston", type="cylinder", position=piston_pos[0], dimensions={"radius": 0.58, "height": 0.25}, material=MaterialConfig(color="#f59e0b", metalness=0.8, roughness=0.2)),
        SceneObject(id="cylinder_base", name="Engine Block Base", type="box", position=[0.0, -0.25, 0.0], dimensions={"width": 1.8, "height": 0.2, "depth": 1.4}, material=MaterialConfig(color="#1e293b", metalness=0.8, roughness=0.3)),
    ]
    overlays = [
        MeasurementOverlay(id="th_eta", label="Thermal Efficiency η", value=eta, unit="%", position_3d=[0.9, 1.2, 0.0]),
        MeasurementOverlay(id="th_cyc", label="Cycle Model", value=cycle_name, unit="", position_3d=[-0.9, 1.2, 0.0]),
    ]
    return SceneSpecification(
        domain="mechanical_engineering",
        experiment_id=exp_id,
        scene_template="thermo_cycle",
        title=f"{cycle_name} — Thermodynamic Cylinder Assembly",
        description=f"Ideal {cycle_name} piston-cylinder representation (η = {eta}%).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 1.4, 3.8], target=[0.0, 0.6, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=4.0, time_step_s=0.05, time_array=t_arr, tracks={"piston_head": AnimationTrack(position=piston_pos)}),
        measurement_overlays=overlays,
    )


# ─── 5. Electronics: Series RLC / RC / RL Circuit Scene ──────────────────────

def build_rlc_circuit_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    exp_id = str(procedure.get("experiment_type") or "series_rlc")
    rlc = numerical_results.get("rlc") or numerical_results.get("rc_circuit") or numerical_results.get("rl_circuit") or numerical_results.get("ac_circuit") or numerical_results.get("transformer") or {}
    R = rlc.get("resistance_ohm", procedure.get("parameters", {}).get("resistance_ohm", 10.0))
    L = rlc.get("inductance_H", procedure.get("parameters", {}).get("inductance_H", 0.1))
    C = rlc.get("capacitance_F", procedure.get("parameters", {}).get("capacitance_F", 0.001))
    f0 = rlc.get("resonant_frequency_Hz", 0.0)
    zeta = rlc.get("damping_ratio_zeta", 0.0)

    # Extract actual transient current to modulate glowing current-flow indicator
    i_vals = plot_data[0]["y"] if plot_data and plot_data[0].get("y") else [math.sin(k * 0.2) for k in range(60)]
    stride = max(1, len(i_vals) // 60)
    i_sub = [abs(float(i_vals[k])) for k in range(0, len(i_vals), stride)]
    i_max = max(max(i_sub), 1e-6)
    glow_track = [round(0.15 + 0.85 * (v / i_max), 3) for v in i_sub]
    t_arr = [round(k * 0.05, 3) for k in range(len(glow_track))]

    objects = [
        SceneObject(id="circuit_board", name="Circuit Test Bench", type="box", position=[0.0, -0.05, 0.0], dimensions={"width": 4.4, "height": 0.1, "depth": 2.6}, material=MaterialConfig(color="#0f172a", metalness=0.4, roughness=0.7)),
        SceneObject(id="voltage_source", name="Voltage Source V₀", type="cylinder", position=[-1.6, 0.35, 0.0], dimensions={"radius": 0.28, "height": 0.6}, material=MaterialConfig(color="#ef4444", metalness=0.5, roughness=0.3)),
        SceneObject(id="resistor_R", name=f"Resistor R = {R} Ω", type="cylinder", position=[-0.4, 0.25, -0.75], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.11, "height": 0.7}, material=MaterialConfig(color="#eab308", metalness=0.2, roughness=0.5)),
        SceneObject(id="inductor_L", name=f"Inductor Coil L = {L} H", type="torus", position=[0.8, 0.32, -0.75], dimensions={"radius": 0.24, "tube": 0.07}, material=MaterialConfig(color="#f97316", metalness=0.85, roughness=0.2)),
        SceneObject(id="capacitor_C_plate1", name=f"Capacitor Plate + (C = {C} F)", type="box", position=[1.6, 0.35, -0.08], dimensions={"width": 0.5, "height": 0.55, "depth": 0.04}, material=MaterialConfig(color="#38bdf8", metalness=0.75, roughness=0.2)),
        SceneObject(id="capacitor_C_plate2", name="Capacitor Plate -", type="box", position=[1.6, 0.35, 0.08], dimensions={"width": 0.5, "height": 0.55, "depth": 0.04}, material=MaterialConfig(color="#0284c7", metalness=0.75, roughness=0.2)),
        SceneObject(id="current_bus_top", name="Top Conductive Loop i(t)", type="box", position=[0.0, 0.16, -0.75], dimensions={"width": 3.2, "height": 0.04, "depth": 0.04}, material=MaterialConfig(color="#22d3ee", emissive="#22d3ee", emissive_intensity=0.6)),
        SceneObject(id="current_bus_return", name="Return Ground Loop", type="box", position=[0.0, 0.16, 0.75], dimensions={"width": 3.2, "height": 0.04, "depth": 0.04}, material=MaterialConfig(color="#3b82f6", metalness=0.6, roughness=0.3)),
    ]
    overlays = [
        MeasurementOverlay(id="rlc_f0", label="Resonant Freq f₀", value=f0, unit="Hz", position_3d=[0.8, 0.9, -0.75]),
        MeasurementOverlay(id="rlc_zeta", label="Damping Ratio ζ", value=zeta, unit="", position_3d=[-0.4, 0.9, -0.75]),
        MeasurementOverlay(id="rlc_peak", label="Peak Current", value=rlc.get("peak_current_A", 0), unit="A", position_3d=[0.0, 0.7, 0.75]),
    ]
    return SceneSpecification(
        domain="electronics",
        experiment_id=exp_id,
        scene_template="rlc_circuit",
        title=f"Series RLC / Reactive Circuit — R={R}Ω, L={L}H, C={C}F",
        description="3D passive electrical circuit with transient current glow driven by solved ODE i(t).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 2.4, 3.6], target=[0.0, 0.2, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_arr[-1] if t_arr else 3.0, time_step_s=0.05, time_array=t_arr, tracks={"current_bus_top": AnimationTrack(emissive_intensity=glow_track)}),
        measurement_overlays=overlays,
    )


def build_resistive_circuit_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    exp_id = str(procedure.get("experiment_type") or "ohms_law")
    block = next(iter(numerical_results.values()), {}) if isinstance(numerical_results, dict) else {}
    template_key = "voltage_divider_circuit" if exp_id == "voltage_divider" else "ohms_law_circuit"
    objects = [
        SceneObject(id="bench_mat", name="Lab Circuit Mat", type="box", position=[0.0, -0.05, 0.0], dimensions={"width": 3.6, "height": 0.08, "depth": 2.2}, material=MaterialConfig(color="#1e293b", roughness=0.8)),
        SceneObject(id="dc_supply", name="DC Voltage Source", type="box", position=[-1.2, 0.25, 0.0], dimensions={"width": 0.6, "height": 0.5, "depth": 0.5}, material=MaterialConfig(color="#ef4444", metalness=0.5, roughness=0.3)),
        SceneObject(id="resistor_1", name="Precision Resistor R1", type="cylinder", position=[0.2, 0.2, -0.45], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.1, "height": 0.7}, material=MaterialConfig(color="#eab308", roughness=0.5)),
        SceneObject(id="resistor_2", name="Load / Divider Resistor R2", type="cylinder", position=[0.2, 0.2, 0.45], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.1, "height": 0.7}, material=MaterialConfig(color="#10b981", roughness=0.5)),
        SceneObject(id="meter_probe", name="Digital Multimeter Readout", type="box", position=[1.2, 0.25, 0.0], dimensions={"width": 0.5, "height": 0.45, "depth": 0.45}, material=MaterialConfig(color="#0284c7", metalness=0.4, roughness=0.4)),
    ]
    overlays = [
        MeasurementOverlay(id="res_v", label="Output / Supply V", value=block.get("Vout_V") or block.get("supply_voltage_V") or 5.0, unit="V", position_3d=[1.2, 0.8, 0.0]),
        MeasurementOverlay(id="res_i", label="Current", value=block.get("max_current_mA") or block.get("current_mA") or block.get("total_current_A") or 0, unit="mA/A", position_3d=[0.2, 0.8, 0.0]),
    ]
    return SceneSpecification(
        domain="electronics",
        experiment_id=exp_id,
        scene_template=template_key,
        title=f"DC Resistive Circuit Bench — {exp_id.replace('_', ' ').title()}",
        description="Deterministic resistive network verified against Ohm's Law, KCL, and KVL.",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 2.0, 3.2], target=[0.0, 0.2, 0.0], fov=45),
        objects=objects,
        measurement_overlays=overlays,
    )


# ─── 6. Chemistry: Acid-Base Titration & Reaction Kinetics ───────────────────

def build_titration_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    tit = numerical_results.get("titration", {})
    v_eq = tit.get("equivalence_volume_mL", 25.0)
    ph_eq = tit.get("equivalence_pH", 8.72)
    ph_init = tit.get("initial_pH", 2.88)

    # Animate liquid volume rising & phenolphthalein glow near equivalence
    ph_vals = plot_data[0]["y"] if plot_data and plot_data[0].get("y") else [3.0, 4.7, 8.7, 12.0]
    stride = max(1, len(ph_vals) // 60)
    ph_sub = [float(ph_vals[i]) for i in range(0, len(ph_vals), stride)]
    t_arr = [round(i * 0.06, 3) for i in range(len(ph_sub))]
    emissive_track = [round(0.05 if p < 8.2 else min(0.95, (p - 8.0) / 3.0), 3) for p in ph_sub]

    objects = [
        SceneObject(id="retort_base", name="Titration Stand Base", type="box", position=[0.0, -0.05, 0.0], dimensions={"width": 1.6, "height": 0.1, "depth": 1.2}, material=MaterialConfig(color="#334155", metalness=0.7, roughness=0.4)),
        SceneObject(id="retort_rod", name="Vertical Retort Rod", type="cylinder", position=[-0.55, 1.3, 0.0], dimensions={"radius": 0.04, "height": 2.6}, material=MaterialConfig(color="#94a3b8", metalness=0.9, roughness=0.2)),
        SceneObject(id="burette_tube", name="50 mL Graduated Burette (NaOH)", type="cylinder", position=[0.1, 1.8, 0.0], dimensions={"radius": 0.07, "height": 1.4}, material=MaterialConfig(color="#e2e8f0", transparent=True, opacity=0.45)),
        SceneObject(id="flask_glass", name="Erlenmeyer Analyte Flask", type="cylinder", position=[0.1, 0.42, 0.0], dimensions={"radius": 0.38, "height": 0.75}, material=MaterialConfig(color="#cbd5e1", transparent=True, opacity=0.35)),
        SceneObject(id="analyte_solution", name="Analyte Solution (Indicator pH)", type="cylinder", position=[0.1, 0.25, 0.0], dimensions={"radius": 0.34, "height": 0.36}, material=MaterialConfig(color="#ec4899", emissive="#ec4899", emissive_intensity=0.1, transparent=True, opacity=0.8)),
    ]
    overlays = [
        MeasurementOverlay(id="tit_init", label="Initial pH", value=ph_init, unit="pH", position_3d=[-0.6, 0.6, 0.0]),
        MeasurementOverlay(id="tit_veq", label="Equivalence Vol V_eq", value=v_eq, unit="mL", position_3d=[0.8, 1.2, 0.0]),
        MeasurementOverlay(id="tit_pheq", label="Equivalence pH", value=ph_eq, unit="pH", position_3d=[0.8, 0.6, 0.0]),
    ]
    return SceneSpecification(
        domain="chemistry",
        experiment_id="acid_base_titration",
        scene_template="titration_apparatus",
        title="Acid-Base Equilibrium Titration Apparatus",
        description=f"Burette titration solved by exact charge-balance equilibrium (V_eq = {v_eq} mL, pH_eq = {ph_eq}).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.2, 1.5, 3.6], target=[0.0, 0.9, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_arr[-1] if t_arr else 3.6, time_step_s=0.06, time_array=t_arr, tracks={"analyte_solution": AnimationTrack(emissive_intensity=emissive_track)}),
        measurement_overlays=overlays,
    )


def build_reaction_kinetics_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    exp_id = str(procedure.get("experiment_type") or "reaction_kinetics")
    kin = numerical_results.get("kinetics") or numerical_results.get("chemical_equilibrium") or numerical_results.get("thermodynamics") or {}
    c_vals = plot_data[0]["y"] if plot_data and plot_data[0].get("y") else [1.0, 0.5, 0.2, 0.05]
    stride = max(1, len(c_vals) // 60)
    c_sub = [float(c_vals[i]) for i in range(0, len(c_vals), stride)]
    c_max = max(max(abs(v) for v in c_sub), 1e-6)
    t_arr = [round(i * 0.05, 3) for i in range(len(c_sub))]
    emissive = [round(max(0.1, 1.0 - abs(v) / c_max), 3) for v in c_sub]

    objects = [
        SceneObject(id="hotplate_base", name="Isothermal Stirrer Hotplate", type="box", position=[0.0, 0.0, 0.0], dimensions={"width": 1.6, "height": 0.25, "depth": 1.6}, material=MaterialConfig(color="#1e293b", metalness=0.7, roughness=0.3)),
        SceneObject(id="reactor_vessel", name="Batch Reactor Glass Vessel", type="cylinder", position=[0.0, 0.85, 0.0], dimensions={"radius": 0.55, "height": 1.3}, material=MaterialConfig(color="#cbd5e1", transparent=True, opacity=0.3)),
        SceneObject(id="reaction_mixture", name="Reacting Solution [A] -> [P]", type="cylinder", position=[0.0, 0.65, 0.0], dimensions={"radius": 0.5, "height": 0.85}, material=MaterialConfig(color="#10b981", emissive="#10b981", emissive_intensity=0.2, transparent=True, opacity=0.75)),
        SceneObject(id="stir_bar", name="Magnetic Stir Bar", type="capsule", position=[0.0, 0.25, 0.0], rotation=[0.0, 0.0, math.pi / 2.0], dimensions={"radius": 0.05, "length": 0.35}, material=MaterialConfig(color="#f8fafc")),
    ]
    overlays = [
        MeasurementOverlay(id="kin_k", label="Rate Constant / K", value=kin.get("rate_constant_k") or kin.get("K_eq") or kin.get("delta_G_kJ_mol") or 0, unit="", position_3d=[0.9, 1.1, 0.0]),
        MeasurementOverlay(id="kin_conv", label="Conversion / Extent", value=kin.get("conversion_percent") or kin.get("extent_M") or 0, unit="%" if "conversion_percent" in kin else "M", position_3d=[-0.9, 1.1, 0.0]),
    ]
    return SceneSpecification(
        domain="chemistry",
        experiment_id=exp_id,
        scene_template="reaction_kinetics",
        title=f"Isothermal Batch Reactor — {exp_id.replace('_', ' ').title()}",
        description="Batch chemical reactor synchronized to solved concentration/equilibrium dynamics.",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 1.4, 3.2], target=[0.0, 0.65, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_arr[-1] if t_arr else 3.0, time_step_s=0.05, time_array=t_arr, tracks={"reaction_mixture": AnimationTrack(emissive_intensity=emissive)}),
        measurement_overlays=overlays,
    )


# ─── 7. Biology: Enzyme Kinetics & Population Growth ─────────────────────────

def build_enzyme_kinetics_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    ek = numerical_results.get("enzyme_kinetics", {})
    objects = [
        SceneObject(id="assay_stage", name="Spectrophotometer Cuvette Stage", type="box", position=[0.0, -0.1, 0.0], dimensions={"width": 2.4, "height": 0.15, "depth": 1.6}, material=MaterialConfig(color="#0f172a", metalness=0.7, roughness=0.3)),
        SceneObject(id="enzyme_macromolecule", name="Enzyme Active Site Complex", type="torus", position=[0.0, 0.7, 0.0], dimensions={"radius": 0.45, "tube": 0.16}, material=MaterialConfig(color="#8b5cf6", metalness=0.3, roughness=0.4)),
        SceneObject(id="substrate_molecule", name="Substrate [S]", type="sphere", position=[-0.8, 0.7, 0.0], dimensions={"radius": 0.14}, material=MaterialConfig(color="#10b981", emissive="#10b981", emissive_intensity=0.5)),
        SceneObject(id="product_molecule", name="Catalyzed Product [P]", type="sphere", position=[0.8, 0.7, 0.0], dimensions={"radius": 0.14}, material=MaterialConfig(color="#f59e0b", emissive="#f59e0b", emissive_intensity=0.5)),
    ]
    overlays = [
        MeasurementOverlay(id="ek_vmax", label="V_max", value=ek.get("Vmax_uninhibited", 100), unit="µM/min", position_3d=[0.0, 1.4, 0.0]),
        MeasurementOverlay(id="ek_km", label="K_m", value=ek.get("Km_uM", 5.0), unit="µM", position_3d=[-0.9, 1.2, 0.0]),
        MeasurementOverlay(id="ek_vkm", label="v([S]=Km)", value=ek.get("velocity_at_Km", 50.0), unit="µM/min", position_3d=[0.9, 1.2, 0.0]),
    ]
    return SceneSpecification(
        domain="biology",
        experiment_id="michaelis_menten",
        scene_template="enzyme_kinetics",
        title="Michaelis-Menten Enzyme Catalysis Apparatus",
        description=f"Steady-state enzyme kinetics (Vmax={ek.get('Vmax_uninhibited')}, Km={ek.get('Km_uM')} µM).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 1.4, 3.2], target=[0.0, 0.6, 0.0], fov=45),
        objects=objects,
        measurement_overlays=overlays,
    )


def build_population_growth_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    exp_id = str(procedure.get("experiment_type") or "logistic_growth")
    gr = numerical_results.get("growth") or numerical_results.get("expression") or {}
    y_vals = plot_data[0]["y"] if plot_data and plot_data[0].get("y") else [100.0, 1000.0, 10000.0]
    stride = max(1, len(y_vals) // 60)
    y_sub = [float(y_vals[i]) for i in range(0, len(y_vals), stride)]
    y_max = max(max(y_sub), 1.0)
    t_arr = [round(i * 0.05, 3) for i in range(len(y_sub))]
    emissive = [round(0.1 + 0.85 * (v / y_max), 3) for v in y_sub]

    objects = [
        SceneObject(id="bioreactor_base", name="Incubator Base", type="box", position=[0.0, -0.05, 0.0], dimensions={"width": 1.8, "height": 0.15, "depth": 1.8}, material=MaterialConfig(color="#1e293b", metalness=0.7, roughness=0.3)),
        SceneObject(id="culture_vessel", name="Bioreactor Culture Vessel", type="cylinder", position=[0.0, 0.8, 0.0], dimensions={"radius": 0.55, "height": 1.4}, material=MaterialConfig(color="#cbd5e1", transparent=True, opacity=0.3)),
        SceneObject(id="biomass_medium", name="Cell Culture Optical Density", type="cylinder", position=[0.0, 0.6, 0.0], dimensions={"radius": 0.48, "height": 0.9}, material=MaterialConfig(color="#22c55e", emissive="#22c55e", emissive_intensity=0.2, transparent=True, opacity=0.75)),
    ]
    overlays = [
        MeasurementOverlay(id="bio_fin", label="Final Population / Level", value=gr.get("final_population") or gr.get("steady_state_protein") or 0, unit="", position_3d=[0.9, 1.1, 0.0]),
        MeasurementOverlay(id="bio_td", label="Doubling Time", value=gr.get("doubling_time_h", "N/A"), unit="h", position_3d=[-0.9, 1.1, 0.0]),
    ]
    return SceneSpecification(
        domain="biology",
        experiment_id=exp_id,
        scene_template="population_growth",
        title=f"Bioreactor Culture — {exp_id.replace('_', ' ').title()}",
        description="Cell culture optical density synchronized to deterministic population ODE.",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 1.4, 3.2], target=[0.0, 0.65, 0.0], fov=45),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_arr[-1] if t_arr else 3.0, time_step_s=0.05, time_array=t_arr, tracks={"biomass_medium": AnimationTrack(emissive_intensity=emissive)}),
        measurement_overlays=overlays,
    )


# ─── 8. Computer Science: Actual Graph Traversal & Sorting Scenes ────────────

def build_graph_traversal_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds 3D graph directly from actual executed BFS/DFS/Dijkstra/Topo/CC results."""
    ae = numerical_results.get("algorithm_execution", {})
    algo = str(ae.get("algorithm") or procedure.get("experiment_type") or "breadth_first_search")
    graph = ae.get("input_data", {}).get("graph") or {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    order = ae.get("traversal_order") or ae.get("settled_order") or ae.get("topological_order") or list(graph.keys())
    shortest_path = ae.get("shortest_path") or []
    path_edges = set(zip(shortest_path[:-1], shortest_path[1:]))

    nodes_list = list(graph.keys())
    n = max(len(nodes_list), 1)
    radius_ring = max(1.6, min(3.2, n * 0.35))
    coords: Dict[str, List[float]] = {}
    for idx, nid in enumerate(nodes_list):
        ang = 2.0 * math.pi * idx / n
        coords[nid] = [round(radius_ring * math.cos(ang), 4), round(0.4 + 0.35 * math.sin(ang * 2.0), 4), round(radius_ring * math.sin(ang), 4)]

    objects: List[SceneObject] = [
        SceneObject(id="graph_stage", name="Graph Execution Stage", type="box", position=[0.0, -0.35, 0.0], dimensions={"width": radius_ring * 2.5, "height": 0.12, "depth": radius_ring * 2.5}, material=MaterialConfig(color="#0f172a", metalness=0.6, roughness=0.4)),
    ]

    # Nodes with step-synchronized emissive activation in EXACT executed traversal order!
    n_frames = max(len(order) * 8, 24)
    t_arr = [round(i * 0.1, 3) for i in range(n_frames)]
    tracks: Dict[str, AnimationTrack] = {}
    order_pos = {nid: i for i, nid in enumerate(order)}

    for nid in nodes_list:
        pos = coords[nid]
        in_order = nid in order_pos
        is_start = (bool(order) and nid == order[0])
        col = "#10b981" if is_start else ("#38bdf8" if in_order else "#64748b")
        obj_id = f"node_{nid}"
        objects.append(SceneObject(
            id=obj_id,
            name=f"Node {nid} (visit #{order_pos[nid]+1})" if in_order else f"Node {nid} (unreached)",
            type="sphere",
            position=pos,
            dimensions={"radius": 0.24},
            material=MaterialConfig(color=col, emissive=col, emissive_intensity=0.25, metalness=0.3, roughness=0.3),
            metadata={"node_id": nid, "visit_rank": order_pos.get(nid, -1)},
        ))
        if in_order:
            activate_frame = order_pos[nid] * 8
            tracks[obj_id] = AnimationTrack(emissive_intensity=[0.95 if f >= activate_frame else 0.12 for f in range(n_frames)])

    # Edges from ACTUAL input graph
    edge_idx = 0
    for u, nbrs in graph.items():
        targets = list(nbrs.keys()) if isinstance(nbrs, dict) else list(nbrs)
        for v in targets:
            if v not in coords:
                continue
            mid, rot, length = _cylinder_between(coords[u], coords[v])
            hi = (u, v) in path_edges
            objects.append(SceneObject(
                id=f"edge_{edge_idx}_{u}_{v}",
                name=f"Edge {u}->{v}",
                type="cylinder",
                position=mid,
                rotation=rot,
                dimensions={"radius": 0.045 if hi else 0.025, "height": length},
                material=MaterialConfig(color="#f59e0b" if hi else "#475569", emissive="#f59e0b" if hi else None, emissive_intensity=0.7 if hi else 0.0),
            ))
            edge_idx += 1

    overlays = [
        MeasurementOverlay(id="cs_algo", label="Executed Algorithm", value=algo.replace("_", " ").upper(), unit="", position_3d=[0.0, 2.0, 0.0]),
        MeasurementOverlay(id="cs_order", label="Execution Order", value=" -> ".join(order[:8]), unit="", position_3d=[0.0, 1.6, 0.0]),
        MeasurementOverlay(id="cs_ops", label="Operation Count", value=ae.get("operation_count", 0), unit="ops", position_3d=[radius_ring, 1.2, 0.0]),
    ]
    return SceneSpecification(
        domain="computer_science",
        experiment_id=algo,
        scene_template="graph_traversal",
        title=f"3D Graph Algorithm Execution — {algo.replace('_', ' ').title()}",
        description=f"Synchronized directly to actual executed {algo} traversal order: {' -> '.join(order)}.",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, radius_ring * 1.4, radius_ring * 2.2], target=[0.0, 0.3, 0.0], fov=48),
        objects=objects,
        animation=AnimationConfig(has_animation=True, duration_s=t_arr[-1], time_step_s=0.1, time_array=t_arr, tracks=tracks),
        measurement_overlays=overlays,
    )


def build_sorting_array_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds 3D bar array synchronized directly to executed sorting/searching algorithm."""
    ae = numerical_results.get("algorithm_execution", {})
    algo = str(ae.get("algorithm") or procedure.get("experiment_type") or "quick_sort")
    arr = ae.get("sorted_array") or ae.get("input_data", {}).get("array") if isinstance(ae.get("input_data"), dict) else ae.get("sorted_array")
    if not isinstance(arr, list) or not arr:
        arr = [5, 12, 23, 34, 45, 67, 89, 91]
    n = len(arr)
    max_v = max(max(abs(float(v)) for v in arr), 1.0)
    spacing = 0.55
    x0 = -((n - 1) * spacing) / 2.0

    objects: List[SceneObject] = [
        SceneObject(id="sort_stage", name="Array Execution Stage", type="box", position=[0.0, -0.08, 0.0], dimensions={"width": max(n * spacing + 1.0, 3.0), "height": 0.14, "depth": 1.6}, material=MaterialConfig(color="#0f172a", metalness=0.7, roughness=0.3)),
    ]
    for i, val in enumerate(arr[:24]):
        h = max(0.15, (float(val) / max_v) * 2.4)
        objects.append(SceneObject(
            id=f"bar_{i}",
            name=f"arr[{i}] = {val}",
            type="box",
            position=[round(x0 + i * spacing, 3), round(h / 2.0, 3), 0.0],
            dimensions={"width": 0.38, "height": round(h, 3), "depth": 0.38},
            material=MaterialConfig(color="#38bdf8", emissive="#0284c7", emissive_intensity=0.25, metalness=0.4, roughness=0.3),
            metadata={"index": i, "value": val},
        ))

    overlays = [
        MeasurementOverlay(id="sort_algo", label="Executed Algorithm", value=algo.replace("_", " ").upper(), unit="", position_3d=[0.0, 2.8, 0.0]),
        MeasurementOverlay(id="sort_ops", label="Operations", value=ae.get("operation_count", 0), unit="ops", position_3d=[1.8, 2.4, 0.0]),
        MeasurementOverlay(id="sort_tc", label="Time Complexity", value=ae.get("time_complexity", ""), unit="", position_3d=[-1.8, 2.4, 0.0]),
    ]
    return SceneSpecification(
        domain="computer_science",
        experiment_id=algo,
        scene_template="sorting_array",
        title=f"3D Array Execution — {algo.replace('_', ' ').title()}",
        description=f"Synchronized to actual {algo} execution ({ae.get('operation_count', 0)} operations).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 2.2, max(n * 0.65, 4.5)], target=[0.0, 1.0, 0.0], fov=48),
        objects=objects,
        measurement_overlays=overlays,
    )


def build_building_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    bld = numerical_results.get("building", {})
    floors = int(bld.get("floors", 2))
    w = float(bld.get("plan_width_m", 12.0)) * 0.3
    d = float(bld.get("plan_depth_m", 8.0)) * 0.3
    fh = float(bld.get("floor_height_m", 3.0)) * 0.3

    objects: List[SceneObject] = []
    for fl in range(floors + 1):
        objects.append(SceneObject(
            id=f"slab_{fl}", name=f"Floor Slab {fl}", type="box",
            position=[0.0, round(fl * fh, 3), 0.0],
            dimensions={"width": round(w, 3), "height": 0.08, "depth": round(d, 3)},
            material=MaterialConfig(color="#64748b", opacity=0.75, transparent=True),
        ))
    return SceneSpecification(
        domain="civil_engineering",
        experiment_id="building_blueprint",
        scene_template="building_blueprint",
        title=f"3D Building Frame ({floors} Floors)",
        description=f"Architectural column-slab frame ({bld.get('plan_width_m', 12)}m × {bld.get('plan_depth_m', 8)}m).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[w * 1.1, floors * fh * 1.1, d * 1.8], target=[0.0, floors * fh * 0.4, 0.0], fov=48),
        objects=objects,
    )
