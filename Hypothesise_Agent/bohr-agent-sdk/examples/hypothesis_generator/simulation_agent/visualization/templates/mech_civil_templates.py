"""
Civil & Mechanical Engineering 3D Scene Templates
=================================================
Generates 3D structural and mechanical visualization scenes:
- Simply Supported Beam under Uniform Distributed Load (Euler-Bernoulli bending, deflection curve, stress color gradient)
- Spur Gear Train (meshed pitch gears, counter-rotation, torque & power transfer)
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


def build_beam_deformation_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D beam deformation and bending moment scene synchronized to exact solver outputs."""
    params = procedure.get("parameters", {})
    exp_id = str(procedure.get("experiment_type") or "").lower().strip()
    beam_res = (
        numerical_results.get("beam_analysis")
        or numerical_results.get("cantilever_analysis")
        or {}
    )
    L = float(beam_res.get("span_m", params.get("span_m", 6.0)))
    beam_width = float(params.get("beam_width_mm", 200.0)) / 1000.0
    beam_depth = float(params.get("beam_depth_mm", 400.0)) / 1000.0

    is_cantilever = (
        "cantilever" in exp_id
        or "cantilever_analysis" in numerical_results
        or any(w in (exp_id + " " + str(procedure.get("hypothesis", ""))).lower() for w in ("cantilever", "fixed-free"))
    )
    is_point_load = (
        "point_load" in exp_id
        or "point_load_kN" in beam_res
        or ("point_load_kN" in params and "load_kN_per_m" not in beam_res)
    )
    is_udl = (
        "udl" in exp_id
        or "load_kN_per_m" in beam_res
        or (not is_point_load and "multiple_loads" not in exp_id and "moment" not in exp_id)
    )

    P = float(beam_res.get("point_load_kN", params.get("point_load_kN", 10.0)))
    w = float(beam_res.get("load_kN_per_m", params.get("load_kN_per_m", 10.0)))
    a_pos = float(beam_res.get("load_position_a_m", params.get("load_position_a_m", L if is_cantilever else L / 2.0)))

    deflection_computed = bool(beam_res.get("deflection_computed", False))
    if not beam_res and ("elastic_modulus_GPa" in params and "moment_of_inertia_m4" in params):
        deflection_computed = True

    E_GPa = float(params.get("elastic_modulus_GPa", 200.0))
    E_kNm2 = E_GPa * 1e6
    I_m4 = float(params.get("moment_of_inertia_m4", 8.33e-6))

    # Discretize beam into 21 node segments along X: [-L/2, +L/2]
    num_nodes = 21
    x_coords = np.linspace(0.0, L, num_nodes)
    x_centered = x_coords - (L / 2.0)

    # Pull solved bending moment & deflection curves from plot_data if available, else compute exact formula matching load type
    moments = None
    deflections_m = np.zeros(num_nodes)
    for p in plot_data or []:
        title_l = str(p.get("title", "")).lower()
        px = p.get("x")
        py = p.get("y")
        if px and py and len(px) >= 5:
            if "moment" in title_l and moments is None:
                moments = np.abs(np.interp(x_coords, np.asarray(px, dtype=float), np.asarray(py, dtype=float)))
            elif "deflection" in title_l and deflection_computed:
                # Deflection plot is in mm (negative downward or positive magnitude)
                deflections_m = np.abs(np.interp(x_coords, np.asarray(px, dtype=float), np.asarray(py, dtype=float))) / 1000.0

    if moments is None:
        if is_cantilever and is_point_load:
            moments = P * np.maximum(0.0, L - x_coords)
        elif is_cantilever:
            moments = 0.5 * w * (L - x_coords) ** 2
        elif is_point_load:
            R_L = P * (L - a_pos) / L
            moments = np.where(x_coords <= a_pos, R_L * x_coords, R_L * x_coords - P * (x_coords - a_pos))
        else:
            moments = 0.5 * w * L * x_coords - 0.5 * w * (x_coords ** 2)

    M_max = float(beam_res.get("max_bending_moment_kNm", beam_res.get("root_moment_kNm", float(np.max(moments)))))
    delta_max_mm = beam_res.get("max_deflection_mm", beam_res.get("tip_deflection_mm"))
    if delta_max_mm is None and deflection_computed:
        if is_cantilever and is_point_load:
            delta_max_mm = (P * L**3) / (3.0 * E_kNm2 * I_m4) * 1000.0
        elif is_cantilever:
            delta_max_mm = (w * L**4) / (8.0 * E_kNm2 * I_m4) * 1000.0
        elif is_point_load:
            delta_max_mm = (P * L**3) / (48.0 * E_kNm2 * I_m4) * 1000.0
        else:
            delta_max_mm = (5.0 * w * L**4) / (384.0 * E_kNm2 * I_m4) * 1000.0
        deflections_m = (moments / max(float(np.max(moments)), 1e-9)) * (float(delta_max_mm) / 1000.0)

    # Normalize 3D visual deflection cleanly when computed; zero deflection when EI was omitted
    if deflection_computed and float(np.max(deflections_m)) > 0:
        max_vis = min(0.45, L * 0.08)
        vis_exaggeration = min(25.0, max_vis / max(float(np.max(deflections_m)), 1e-6))
        deflections_3d = deflections_m * vis_exaggeration
    else:
        vis_exaggeration = 0.0
        deflections_3d = np.zeros(num_nodes)

    max_m = max(float(np.max(moments)), 1e-5)
    sigma_max_MPa = beam_res.get("max_bending_stress_MPa")

    objects: List[SceneObject] = []

    if is_cantilever:
        objects.append(SceneObject(
            id="fixed_root_clamp",
            name="Fixed Support Clamp (x = 0)",
            type="box",
            position=[-L / 2.0 - 0.1, 0.0, 0.0],
            dimensions={"width": 0.2, "height": beam_depth * 2.5, "depth": beam_width * 2.0},
            material=MaterialConfig(color="#334155", metalness=0.8, roughness=0.3)
        ))
    else:
        objects.append(SceneObject(
            id="pin_support_left",
            name=f"Pinned Support A (R_A = {beam_res.get('reaction_A_kN', beam_res.get('reaction_left_kN', 'N/A'))} kN)",
            type="cylinder",
            position=[-L / 2.0, -0.25, 0.0],
            dimensions={"radius": 0.15, "height": 0.3},
            material=MaterialConfig(color="#475569", metalness=0.8, roughness=0.3)
        ))
        objects.append(SceneObject(
            id="roller_support_right",
            name=f"Roller Support B (R_B = {beam_res.get('reaction_B_kN', beam_res.get('reaction_right_kN', 'N/A'))} kN)",
            type="sphere",
            position=[L / 2.0, -0.25, 0.0],
            dimensions={"radius": 0.15},
            material=MaterialConfig(color="#64748b", metalness=0.9, roughness=0.2)
        ))

    objects.append(SceneObject(
        id="reference_axis",
        name="Neutral Axis Reference",
        type="line",
        position=[0.0, 0.0, 0.0],
        dimensions={"length": L},
        material=MaterialConfig(color="#64748b", wireframe=True, opacity=0.3, transparent=True),
        metadata={"points": [[-L / 2.0, 0.0, 0.0], [L / 2.0, 0.0, 0.0]]}
    ))

    dx = L / (num_nodes - 1)
    for i in range(num_nodes - 1):
        xc = float((x_centered[i] + x_centered[i + 1]) / 2.0)
        yc = -float((deflections_3d[i] + deflections_3d[i + 1]) / 2.0)
        m_norm = float(moments[i] / max_m)
        r_col = int(50 + 205 * m_norm)
        g_col = int(80 + 50 * (1 - m_norm))
        b_col = int(220 * (1 - m_norm) + 30)
        hex_color = f"#{r_col:02x}{g_col:02x}{b_col:02x}"

        objects.append(SceneObject(
            id=f"beam_segment_{i}",
            name=f"Beam Segment {i + 1} (M={round(float(moments[i]), 2)} kN·m)",
            type="box",
            position=[round(xc, 3), round(yc, 3), 0.0],
            dimensions={"width": round(dx * 1.02, 3), "height": beam_depth, "depth": beam_width},
            material=MaterialConfig(color=hex_color, metalness=0.3, roughness=0.4),
            metadata={"segment_index": i, "moment_kNm": round(float(moments[i]), 3)}
        ))

    # Load arrows synchronized to ACTUAL load type!
    if is_point_load:
        x_arrow = (L / 2.0) if is_cantilever else (a_pos - L / 2.0)
        objects.append(SceneObject(
            id="point_load_arrow",
            name=f"Concentrated Point Load P = {P} kN",
            type="arrow",
            position=[round(x_arrow, 3), beam_depth / 2.0 + 0.75, 0.0],
            rotation=[math.pi, 0.0, 0.0],
            dimensions={"length": 0.65, "radius": 0.05},
            material=MaterialConfig(color="#ef4444", emissive="#ef4444", emissive_intensity=0.35, metalness=0.5, roughness=0.3)
        ))
    elif is_udl:
        for i in range(1, num_nodes - 1, 3):
            xc = float(x_centered[i])
            objects.append(SceneObject(
                id=f"load_arrow_{i}",
                name=f"UDL Vector w = {w} kN/m",
                type="arrow",
                position=[round(xc, 3), beam_depth / 2.0 + 0.6, 0.0],
                rotation=[math.pi, 0.0, 0.0],
                dimensions={"length": 0.5, "radius": 0.03},
                material=MaterialConfig(color="#f59e0b", metalness=0.5, roughness=0.3)
            ))
    else:
        # Multiple loads or applied moment
        objects.append(SceneObject(
            id="load_arrow_center",
            name="Applied Structural Loading",
            type="arrow",
            position=[0.0, beam_depth / 2.0 + 0.65, 0.0],
            rotation=[math.pi, 0.0, 0.0],
            dimensions={"length": 0.55, "radius": 0.04},
            material=MaterialConfig(color="#f59e0b", metalness=0.5, roughness=0.3)
        ))

    # Animation only when deflection is actually computed
    frames = 60
    time_array = [round(t * 0.05, 3) for t in range(frames)]
    tracks: Dict[str, AnimationTrack] = {}
    if deflection_computed:
        for i in range(num_nodes - 1):
            xc = float((x_centered[i] + x_centered[i + 1]) / 2.0)
            final_yc = -float((deflections_3d[i] + deflections_3d[i + 1]) / 2.0)
            seg_positions = [
                [round(xc, 3), round(final_yc * ((step / (frames - 1)) ** 1.5), 4), 0.0]
                for step in range(frames)
            ]
            tracks[f"beam_segment_{i}"] = AnimationTrack(position=seg_positions)

    load_param = (
        ParameterConfig(name="point_load_kN", label="Point Load P", type="float", value=P, min_val=1.0, max_val=200.0, step=1.0, unit="kN", description="Concentrated transverse point load")
        if is_point_load else
        ParameterConfig(name="load_kN_per_m", label="Uniform Load w", type="float", value=w, min_val=1.0, max_val=50.0, step=1.0, unit="kN/m", description="Uniformly distributed transverse load")
    )
    parameters = [
        ParameterConfig(name="span_m", label="Beam Span Length L", type="float", value=L, min_val=1.0, max_val=20.0, step=0.5, unit="m", description="Beam span length"),
        load_param,
    ]

    overlays = [
        MeasurementOverlay(
            id="moment_meas",
            label="Root Moment M_max" if is_cantilever else "Max Bending Moment M_max",
            value=round(M_max, 3),
            unit="kN·m",
            position_3d=[-L / 2.0, 0.9, 0.0] if is_cantilever else [0.0, 0.9, 0.0]
        ),
        MeasurementOverlay(
            id="deflect_meas",
            label="Tip Deflection δ_tip" if is_cantilever else "Max Deflection δ_max",
            value=round(float(delta_max_mm), 3) if delta_max_mm is not None else "Requires E & I",
            unit="mm" if delta_max_mm is not None else "",
            position_3d=[L / 2.0, -0.6, 0.0] if is_cantilever else [0.0, -0.6, 0.0]
        ),
    ]
    if "reaction_A_kN" in beam_res or "reaction_left_kN" in beam_res:
        ra = beam_res.get("reaction_A_kN", beam_res.get("reaction_left_kN", 0))
        rb = beam_res.get("reaction_B_kN", beam_res.get("reaction_right_kN", 0))
        overlays.append(MeasurementOverlay(
            id="rxn_left_meas",
            label="Support Reactions R_A / R_B",
            value=f"{ra} / {rb}",
            unit="kN",
            position_3d=[-L / 2.0, -0.7, 0.0]
        ))
    elif sigma_max_MPa is not None:
        overlays.append(MeasurementOverlay(
            id="stress_meas",
            label="Max Flexural Stress σ_max",
            value=round(float(sigma_max_MPa), 2),
            unit="MPa",
            position_3d=[0.0, 1.2, 0.0]
        ))

    canonical_exp = exp_id or ("cantilever_beam_point_load" if (is_cantilever and is_point_load) else "simply_supported_beam_point_load" if is_point_load else "simply_supported_beam_udl")
    load_desc = f"point load P={P} kN" if is_point_load else f"UDL w={w} kN/m"
    notes = [
        f"Deflection exaggerated {round(vis_exaggeration, 1)}x for 3D clarity (actual: {round(float(delta_max_mm), 3)} mm)."
        if deflection_computed and delta_max_mm is not None
        else "Deflection not animated because explicit E and I were not provided; colors show exact bending moment distribution."
    ]

    return SceneSpecification(
        domain="civil_engineering",
        experiment_id=canonical_exp,
        scene_template="beam_deformation",
        title=f"{'Cantilever' if is_cantilever else 'Simply Supported'} Beam — {load_desc}",
        description=f"Euler-Bernoulli beam analysis (L={L} m, {load_desc}, M_max={round(M_max, 3)} kN·m).",
        is_simulation_backed=True,
        camera=CameraConfig(position=[0.0, 1.2, max(L * 1.1, 4.0)], target=[0.0, 0.0, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.8, directional_position=[3.0, 8.0, 5.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=deflection_computed,
            duration_s=3.0 if deflection_computed else 0.0,
            time_step_s=0.05,
            time_array=time_array if deflection_computed else [],
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True),
        notes=notes
    )


def build_gear_train_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D mechanical spur gear train simulation scene."""
    params = procedure.get("parameters", {})
    N1 = int(params.get("teeth_driver", 20))
    N2 = int(params.get("teeth_driven", 40))
    module = float(params.get("module_mm", 2.5))
    rpm_in = float(params.get("rpm_input", 60.0))  # visual speed
    power_kW = float(params.get("power_kW", 5.0))

    ratio = N2 / N1
    rpm_out = rpm_in / ratio

    # Pitch diameters in 3D units (scaled for scene: 1 module mm -> 0.03 units)
    scale_m = 0.03
    d1 = N1 * module * scale_m
    d2 = N2 * module * scale_m
    centre_dist = (d1 + d2) / 2.0

    objects = [
        # Gearbox Base
        SceneObject(
            id="gear_chassis",
            name="Gearbox Base Plate",
            type="box",
            position=[centre_dist / 2.0, -0.1, 0.0],
            dimensions={"width": centre_dist + d2 + 0.5, "height": 0.1, "depth": 1.2},
            material=MaterialConfig(color="#1e293b", metalness=0.8, roughness=0.3)
        ),
        # Driver Shaft
        SceneObject(
            id="driver_shaft",
            name="Input Drive Shaft",
            type="cylinder",
            position=[0.0, 0.4, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.08, "height": 0.6},
            material=MaterialConfig(color="#64748b", metalness=0.9, roughness=0.1)
        ),
        # Driver Pinion Gear
        SceneObject(
            id="gear_driver",
            name=f"Driver Pinion ({N1} teeth)",
            type="cylinder",
            position=[0.0, 0.4, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": d1 / 2.0, "height": 0.18},
            material=MaterialConfig(color="#3b82f6", metalness=0.6, roughness=0.3)
        ),
        # Driven Shaft
        SceneObject(
            id="driven_shaft",
            name="Output Driven Shaft",
            type="cylinder",
            position=[centre_dist, 0.4, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.1, "height": 0.6},
            material=MaterialConfig(color="#64748b", metalness=0.9, roughness=0.1)
        ),
        # Driven Gear
        SceneObject(
            id="gear_driven",
            name=f"Driven Spur Gear ({N2} teeth)",
            type="cylinder",
            position=[centre_dist, 0.4, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": d2 / 2.0, "height": 0.18},
            material=MaterialConfig(color="#f59e0b", metalness=0.6, roughness=0.3)
        )
    ]

    # Generate synchronized counter-rotation tracks
    frames = 120
    time_array = [round(t * 0.05, 3) for t in range(frames)]
    w1 = (rpm_in * 2.0 * math.pi) / 60.0
    w2 = -w1 / ratio

    driver_rots = []
    driven_rots = []
    for t in time_array:
        rot1 = [math.pi / 2, round(w1 * t, 3), 0.0]
        rot2 = [math.pi / 2, round(w2 * t, 3), 0.0]
        driver_rots.append(rot1)
        driven_rots.append(rot2)

    tracks = {
        "gear_driver": AnimationTrack(rotation=driver_rots),
        "gear_driven": AnimationTrack(rotation=driven_rots)
    }

    parameters = [
        ParameterConfig(
            name="teeth_driver",
            label="Driver Teeth N₁",
            type="int",
            value=N1,
            min_val=10.0,
            max_val=60.0,
            step=1.0,
            description="Number of teeth on the input pinion"
        ),
        ParameterConfig(
            name="teeth_driven",
            label="Driven Teeth N₂",
            type="int",
            value=N2,
            min_val=15.0,
            max_val=120.0,
            step=1.0,
            description="Number of teeth on the output gear"
        ),
        ParameterConfig(
            name="rpm_input",
            label="Input Speed RPM",
            type="float",
            value=rpm_in,
            min_val=10.0,
            max_val=3000.0,
            step=50.0,
            unit="RPM",
            description="Rotational velocity of the driver shaft"
        )
    ]

    overlays = [
        MeasurementOverlay(
            id="ratio_meas",
            label="Gear Ratio i",
            value=f"{N2}:{N1} ({round(ratio, 2)}x)",
            position_3d=[centre_dist / 2.0, 1.2, 0.0]
        ),
        MeasurementOverlay(
            id="rpm_out_meas",
            label="Output Speed",
            value=round(rpm_out, 1),
            unit="RPM",
            position_3d=[centre_dist, 0.9, 0.0]
        )
    ]

    return SceneSpecification(
        domain="mechanical_engineering",
        experiment_id="gear_train",
        scene_template="gear_train",
        title="Spur Gear Train Kinematics & Reduction",
        description=f"Kinematic spur gear transmission with gear ratio i={round(ratio, 2)}:1, meshing at centre distance C={round(centre_dist, 2)}m.",
        is_simulation_backed=True,
        confidence_score=0.98,
        camera=CameraConfig(position=[centre_dist / 2.0, 1.5, 3.5], target=[centre_dist / 2.0, 0.4, 0.0], fov=45),
        lighting=LightingConfig(ambient_intensity=0.85, directional_position=[4.0, 7.0, 4.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=6.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True)
    )


def build_four_bar_linkage_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """
    Builds an analytical, kinematically consistent 3D Four-Bar Linkage simulation scene.
    Directly consumes `numerical_results["kinematic_trajectory"]` from `mech_sim` when available
    so every link pose, joint position, and assembly branch matches the solved vector-loop equations.
    """
    params = procedure.get("parameters", {})
    traj = numerical_results.get("kinematic_trajectory") or {}
    fb = numerical_results.get("four_bar_linkage") or {}

    lengths = traj.get("lengths") or {}
    a = float(lengths.get("crank_a_m", fb.get("crank_length_m", params.get("crank_length", params.get("length_a", 1.0)))))
    b = float(lengths.get("coupler_b_m", fb.get("coupler_length_m", params.get("coupler_length", params.get("length_b", 2.5)))))
    c = float(lengths.get("rocker_c_m", fb.get("rocker_length_m", params.get("rocker_length", params.get("length_c", 2.0)))))
    d = float(lengths.get("ground_d_m", fb.get("ground_length_m", params.get("ground_length", params.get("length_d", 3.0)))))
    rpm_in = float(fb.get("input_rpm", params.get("rpm", params.get("cadence_rpm", 30.0))))

    crank_positions: List[List[float]] = []
    crank_rotations: List[List[float]] = []
    coupler_positions: List[List[float]] = []
    coupler_rotations: List[List[float]] = []
    rocker_positions: List[List[float]] = []
    rocker_rotations: List[List[float]] = []

    joints = traj.get("joint_positions")
    t_src = traj.get("time_steps") or traj.get("time_s")
    if isinstance(joints, list) and joints and t_src and len(joints) == len(t_src):
        stride = max(1, len(t_src) // 120)
        time_array = [round(float(t_src[i]), 4) for i in range(0, len(t_src), stride)]
        for i in range(0, len(t_src), stride):
            frame = joints[i]
            xB, yB = float(frame["B"][0]), float(frame["B"][1])
            xC, yC = float(frame["C"][0]), float(frame["C"][1])
            theta2 = math.atan2(yB, xB)
            theta3 = math.atan2(yC - yB, xC - xB)
            theta4 = math.atan2(yC, xC - d)
            crank_positions.append([round(xB / 2.0, 4), round(yB / 2.0, 4), 0.0])
            crank_rotations.append([0.0, 0.0, round(theta2 - math.pi / 2.0, 4)])
            coupler_positions.append([round((xB + xC) / 2.0, 4), round((yB + yC) / 2.0, 4), 0.0])
            coupler_rotations.append([0.0, 0.0, round(theta3 - math.pi / 2.0, 4)])
            rocker_positions.append([round((d + xC) / 2.0, 4), round(yC / 2.0, 4), 0.0])
            rocker_rotations.append([0.0, 0.0, round(theta4 - math.pi / 2.0, 4)])
    elif isinstance(joints, dict) and joints.get("B") and joints.get("C") and t_src:
        b_pts = joints["B"]
        c_pts = joints["C"]
        stride = max(1, len(t_src) // 120)
        time_array = [round(float(t_src[i]), 4) for i in range(0, len(t_src), stride)]
        for i in range(0, len(t_src), stride):
            xB, yB = float(b_pts[i][0]), float(b_pts[i][1])
            xC, yC = float(c_pts[i][0]), float(c_pts[i][1])
            theta2 = math.atan2(yB, xB)
            theta3 = math.atan2(yC - yB, xC - xB)
            theta4 = math.atan2(yC, xC - d)
            crank_positions.append([round(xB / 2.0, 4), round(yB / 2.0, 4), 0.0])
            crank_rotations.append([0.0, 0.0, round(theta2 - math.pi / 2.0, 4)])
            coupler_positions.append([round((xB + xC) / 2.0, 4), round((yB + yC) / 2.0, 4), 0.0])
            coupler_rotations.append([0.0, 0.0, round(theta3 - math.pi / 2.0, 4)])
            rocker_positions.append([round((d + xC) / 2.0, 4), round(yC / 2.0, 4), 0.0])
            rocker_rotations.append([0.0, 0.0, round(theta4 - math.pi / 2.0, 4)])
    else:
        frames = 120
        time_array = [round(t * 0.05, 3) for t in range(frames)]
        omega = (rpm_in * 2.0 * math.pi) / 60.0
        for t in time_array:
            theta2 = omega * t
            xB = a * math.cos(theta2)
            yB = a * math.sin(theta2)
            dx = d - xB
            dy = -yB
            dist_bd = max(math.hypot(dx, dy), 1e-9)
            cos_alpha = max(-1.0, min(1.0, (b**2 + dist_bd**2 - c**2) / (2.0 * b * dist_bd)))
            alpha = math.acos(cos_alpha)
            phi = math.atan2(dy, dx)
            theta3 = phi + alpha
            xC = xB + b * math.cos(theta3)
            yC = yB + b * math.sin(theta3)
            theta4 = math.atan2(yC, xC - d)
            crank_positions.append([round(xB / 2.0, 4), round(yB / 2.0, 4), 0.0])
            crank_rotations.append([0.0, 0.0, round(theta2 - math.pi / 2.0, 4)])
            coupler_positions.append([round((xB + xC) / 2.0, 4), round((yB + yC) / 2.0, 4), 0.0])
            coupler_rotations.append([0.0, 0.0, round(theta3 - math.pi / 2.0, 4)])
            rocker_positions.append([round((d + xC) / 2.0, 4), round(yC / 2.0, 4), 0.0])
            rocker_rotations.append([0.0, 0.0, round(theta4 - math.pi / 2.0, 4)])

    objects = [
        # Ground Frame Base Plate
        SceneObject(
            id="ground_base",
            name="Ground Frame Link AD",
            type="box",
            position=[round(d / 2.0, 3), -0.2, 0.0],
            dimensions={"width": d + 1.0, "height": 0.15, "depth": 0.8},
            material=MaterialConfig(color="#1e293b", metalness=0.8, roughness=0.3)
        ),
        # Fixed Pivot A
        SceneObject(
            id="pivot_a",
            name="Fixed Pivot A (Crank Ground)",
            type="cylinder",
            position=[0.0, 0.0, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.12, "height": 0.3},
            material=MaterialConfig(color="#475569", metalness=0.9, roughness=0.2)
        ),
        # Fixed Pivot D
        SceneObject(
            id="pivot_d",
            name="Fixed Pivot D (Rocker Ground)",
            type="cylinder",
            position=[d, 0.0, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.12, "height": 0.3},
            material=MaterialConfig(color="#475569", metalness=0.9, roughness=0.2)
        ),
        # Crank Link AB
        SceneObject(
            id="crank_link",
            name="Input Crank Link AB",
            type="cylinder",
            position=crank_positions[0],
            rotation=crank_rotations[0],
            dimensions={"radius": 0.06, "height": a},
            material=MaterialConfig(color="#06b6d4", metalness=0.6, roughness=0.3)
        ),
        # Coupler Link BC
        SceneObject(
            id="coupler_link",
            name="Coupler Connecting Rod BC",
            type="cylinder",
            position=coupler_positions[0],
            rotation=coupler_rotations[0],
            dimensions={"radius": 0.05, "height": b},
            material=MaterialConfig(color="#f59e0b", metalness=0.6, roughness=0.3)
        ),
        # Rocker Link CD
        SceneObject(
            id="rocker_link",
            name="Output Rocker Link CD",
            type="cylinder",
            position=rocker_positions[0],
            rotation=rocker_rotations[0],
            dimensions={"radius": 0.06, "height": c},
            material=MaterialConfig(color="#10b981", metalness=0.6, roughness=0.3)
        ),
    ]

    tracks = {
        "crank_link": AnimationTrack(position=crank_positions, rotation=crank_rotations),
        "coupler_link": AnimationTrack(position=coupler_positions, rotation=coupler_rotations),
        "rocker_link": AnimationTrack(position=rocker_positions, rotation=rocker_rotations),
    }

    overlays = [
        MeasurementOverlay(
            id="m_crank_length",
            label="Crank Length a",
            value=round(a, 2),
            unit="m",
            target_object_id="crank_link",
            position_3d=[0.0, round(a / 2.0, 2), 0.15],
            is_dynamic=False
        ),
        MeasurementOverlay(
            id="m_rocker_length",
            label="Rocker Length c",
            value=round(c, 2),
            unit="m",
            target_object_id="rocker_link",
            position_3d=[d, round(c / 2.0, 2), 0.15],
            is_dynamic=False
        ),
    ]

    return SceneSpecification(
        version="2.0.0",
        domain="mechanical_engineering",
        experiment_id="four_bar_linkage",
        scene_template="four_bar_linkage",
        title="Four-Bar Planar Mechanism Kinematics",
        description=f"Kinematic simulation of four-bar mechanism: crank a={a}m, coupler b={b}m, rocker c={c}m, ground d={d}m with continuous Freudenstein loop trajectory.",
        is_simulation_backed=True,
        confidence_score=0.98,
        camera=CameraConfig(position=[d / 2.0, 1.5, 4.5], target=[d / 2.0, 0.8, 0.0], fov=45),
        lighting=LightingConfig(ambient_intensity=0.85, directional_position=[4.0, 7.0, 4.0]),
        objects=objects,
        parameters=[
            ParameterConfig(name="crank_length", label="Crank Length a", type="float", value=a, min_val=0.5, max_val=2.0, step=0.1, unit="m"),
            ParameterConfig(name="coupler_length", label="Coupler Length b", type="float", value=b, min_val=1.5, max_val=4.0, step=0.1, unit="m"),
            ParameterConfig(name="rocker_length", label="Rocker Length c", type="float", value=c, min_val=1.0, max_val=3.5, step=0.1, unit="m"),
            ParameterConfig(name="ground_length", label="Ground Length d", type="float", value=d, min_val=1.5, max_val=5.0, step=0.1, unit="m"),
        ],
        animation=AnimationConfig(
            has_animation=True,
            duration_s=6.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True)
    )

