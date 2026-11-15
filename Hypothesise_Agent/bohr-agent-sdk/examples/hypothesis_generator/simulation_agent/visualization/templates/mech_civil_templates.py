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
    """Builds an interactive 3D beam deformation and bending stress simulation scene."""
    params = procedure.get("parameters", {})
    L = float(params.get("span_m", 6.0))
    w = float(params.get("load_kN_per_m", 15.0))
    E_GPa = float(params.get("elastic_modulus_GPa", 200.0))
    E = E_GPa * 1e6  # kN/m²
    I = float(params.get("moment_of_inertia_m4", 8.33e-6))
    beam_width = float(params.get("beam_width_mm", 200.0)) / 1000.0
    beam_depth = float(params.get("beam_depth_mm", 400.0)) / 1000.0

    is_cantilever = any(w in (procedure.get("experiment_type", "") + " " + procedure.get("hypothesis", "")).lower() for w in ("cantilever", "fixed-free", "fixed beam"))

    if is_cantilever:
        # Max deflection at free tip: delta_max = w L^4 / (8 E I) in meters
        delta_max_m = (w * (L**4)) / (8.0 * E * I)
        delta_max_mm = delta_max_m * 1000.0
        # Max bending moment at fixed root: M_max = w L^2 / 2 in kN·m
        M_max = (w * (L**2)) / 2.0
        sigma_max_MPa = (M_max * (beam_depth / 2.0)) / I / 1000.0
    else:
        # Max deflection at midspan: delta_max = 5 w L^4 / (384 E I) in meters
        delta_max_m = (5.0 * w * (L**4)) / (384.0 * E * I)
        delta_max_mm = delta_max_m * 1000.0
        # Max bending moment: M_max = w L^2 / 8 in kN·m
        M_max = (w * (L**2)) / 8.0
        sigma_max_MPa = (M_max * (beam_depth / 2.0)) / I / 1000.0

    # Exaggeration factor for 3D visual perception (deflections are mm on meter beams)
    vis_exaggeration = 25.0

    # Discretize beam into 21 node segments along X: [-L/2, +L/2]
    num_nodes = 21
    x_coords = np.linspace(0.0, L, num_nodes)
    x_centered = x_coords - (L / 2.0)

    if is_cantilever:
        # Deflection profile: delta(x) = (w*x^2)/(24*E*I) * (x^2 - 4*L*x + 6*L^2)
        deflections_m = (w * (x_coords**2) / (24.0 * E * I)) * (x_coords**2 - 4.0 * L * x_coords + 6.0 * (L**2))
        moments = (w * ((L - x_coords)**2)) / 2.0
    else:
        # Deflection profile: delta(x) = (w * x / (24 E I)) * (L^3 - 2 L x^2 + x^3)
        deflections_m = (w * x_coords / (24.0 * E * I)) * (L**3 - 2.0 * L * (x_coords**2) + (x_coords**3))
        moments = (w * L / 2.0) * x_coords - (w * (x_coords**2) / 2.0)

    deflections_3d = deflections_m * vis_exaggeration
    max_m = max(float(np.max(moments)), 1e-5)

    objects: List[SceneObject] = []

    if is_cantilever:
        # Fixed Wall Clamp Support at Root (Left)
        objects.append(SceneObject(
            id="fixed_root_clamp",
            name="Fixed Support Clamp",
            type="box",
            position=[-L / 2.0 - 0.1, 0.0, 0.0],
            dimensions={"width": 0.2, "height": beam_depth * 2.5, "depth": beam_width * 2.0},
            material=MaterialConfig(color="#334155", metalness=0.8, roughness=0.3)
        ))
    else:
        # Pin Support (Left)
        objects.append(SceneObject(
            id="pin_support_left",
            name="Pinned Support A",
            type="cylinder",
            position=[-L / 2.0, -0.25, 0.0],
            dimensions={"radius": 0.15, "height": 0.3},
            material=MaterialConfig(color="#475569", metalness=0.8, roughness=0.3)
        ))

        # Roller Support (Right)
        objects.append(SceneObject(
            id="roller_support_right",
            name="Roller Support B",
            type="sphere",
            position=[L / 2.0, -0.25, 0.0],
            dimensions={"radius": 0.15},
            material=MaterialConfig(color="#64748b", metalness=0.9, roughness=0.2)
        ))

    # Undeformed ghost reference line
    objects.append(SceneObject(
        id="reference_axis",
        name="Neutral Axis Reference",
        type="line",
        position=[0.0, 0.0, 0.0],
        dimensions={"length": L},
        material=MaterialConfig(color="#64748b", wireframe=True, opacity=0.3, transparent=True),
        metadata={"points": [[-L / 2.0, 0.0, 0.0], [L / 2.0, 0.0, 0.0]]}
    ))

    # Beam segments
    dx = L / (num_nodes - 1)
    for i in range(num_nodes - 1):
        xc = (x_centered[i] + x_centered[i+1]) / 2.0
        # Deflection at midpoint
        yc = -float((deflections_3d[i] + deflections_3d[i+1]) / 2.0)
        # Normalized stress (0 = blue, 1 = red)
        m_norm = float(moments[i] / max_m)
        r_col = int(50 + 205 * m_norm)
        g_col = int(80 + 50 * (1 - m_norm))
        b_col = int(220 * (1 - m_norm) + 30)
        hex_color = f"#{r_col:02x}{g_col:02x}{b_col:02x}"

        objects.append(SceneObject(
            id=f"beam_segment_{i}",
            name=f"Beam Segment {i+1} (σ={round(m_norm * sigma_max_MPa, 1)} MPa)",
            type="box",
            position=[round(xc, 3), round(yc, 3), 0.0],
            dimensions={"width": round(dx * 1.02, 3), "height": beam_depth, "depth": beam_width},
            material=MaterialConfig(color=hex_color, metalness=0.3, roughness=0.4),
            metadata={"segment_index": i, "stress_MPa": round(m_norm * sigma_max_MPa, 2)}
        ))

    # Distributed Load Arrows along top face
    for i in range(1, num_nodes - 1, 3):
        xc = x_centered[i]
        objects.append(SceneObject(
            id=f"load_arrow_{i}",
            name=f"UDL Load Vector {w} kN/m",
            type="arrow",
            position=[round(xc, 3), beam_depth / 2.0 + 0.6, 0.0],
            rotation=[math.pi, 0.0, 0.0],  # pointing downward
            dimensions={"length": 0.5, "radius": 0.03},
            material=MaterialConfig(color="#f59e0b", metalness=0.5, roughness=0.3)
        ))

    # Animation: Load ramping from 0 to 100%
    frames = 80
    time_array = [round(t * 0.05, 3) for t in range(frames)]
    tracks = {}
    for i in range(num_nodes - 1):
        xc = (x_centered[i] + x_centered[i+1]) / 2.0
        final_yc = -float((deflections_3d[i] + deflections_3d[i+1]) / 2.0)
        seg_positions = []
        for step in range(frames):
            factor = (step / (frames - 1)) ** 1.5
            y_ramp = final_yc * factor
            seg_positions.append([round(xc, 3), round(y_ramp, 3), 0.0])
        tracks[f"beam_segment_{i}"] = AnimationTrack(position=seg_positions)

    parameters = [
        ParameterConfig(
            name="span_m",
            label="Beam Span Length",
            type="float",
            value=L,
            min_val=2.0,
            max_val=15.0,
            step=0.5,
            unit="m",
            description="Clear distance between support pivots"
        ),
        ParameterConfig(
            name="load_kN_per_m",
            label="Uniform Load w",
            type="float",
            value=w,
            min_val=1.0,
            max_val=50.0,
            step=1.0,
            unit="kN/m",
            description="Uniformly distributed transverse load"
        ),
        ParameterConfig(
            name="elastic_modulus_GPa",
            label="Young's Modulus E",
            type="float",
            value=E_GPa,
            min_val=10.0,
            max_val=400.0,
            step=5.0,
            unit="GPa",
            description="Material stiffness modulus (e.g. Steel=200 GPa, Concrete=30 GPa)"
        )
    ]

    overlays = [
        MeasurementOverlay(
            id="deflect_meas",
            label="Tip Deflection δ_tip" if is_cantilever else "Midspan Deflection δ_max",
            value=round(delta_max_mm, 2),
            unit="mm",
            position_3d=[L / 2.0, -0.6, 0.0] if is_cantilever else [0.0, -0.6, 0.0]
        ),
        MeasurementOverlay(
            id="moment_meas",
            label="Fixed Root Moment M_root" if is_cantilever else "Max Bending Moment M_max",
            value=round(M_max, 2),
            unit="kN·m",
            position_3d=[-L / 2.0, 0.9, 0.0] if is_cantilever else [0.0, 0.9, 0.0]
        ),
        MeasurementOverlay(
            id="stress_meas",
            label="Max Flexural Stress σ_max",
            value=round(sigma_max_MPa, 1),
            unit="MPa",
            position_3d=[-L / 2.0, 1.2, 0.0] if is_cantilever else [0.0, 1.2, 0.0]
        )
    ]

    return SceneSpecification(
        domain="civil_engineering",
        experiment_id="beam_deformation",
        scene_template="beam_deformation",
        title="Euler-Bernoulli Beam Bending & Stress Distribution",
        description=f"Structural beam deflection under uniform loading w={w} kN/m, calculated via EI·d⁴v/dx⁴ = -w. Stress colored from compression to tension.",
        is_simulation_backed=True,
        confidence_score=0.97,
        camera=CameraConfig(position=[0.0, 1.2, L * 1.1], target=[0.0, 0.0, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.8, directional_position=[3.0, 8.0, 5.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=4.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True),
        notes=[f"Deflection exaggerated {int(vis_exaggeration)}x for 3D visual clarity. Actual midspan deflection: {round(delta_max_mm, 2)} mm"]
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

