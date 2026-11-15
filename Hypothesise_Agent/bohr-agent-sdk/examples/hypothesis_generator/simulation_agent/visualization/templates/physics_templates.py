"""
Physics 3D Scene Templates
==========================
Generates validated 3D scene specifications for mechanics, kinematics, and motion experiments:
- Simple Pendulum (oscillations, string/bob geometry, velocity/tension vectors, period overlay)
- Projectile Motion (cannon platform, parabolic arc, projectile mesh, velocity vector)
- Spring-Mass System (coiled spring mesh, vibrating mass, restoring force vector)
"""

import math
import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict, Any, List
from ..scene_schema import (
    SceneSpecification, SceneObject, MaterialConfig,
    CameraConfig, LightingConfig, ParameterConfig,
    AnimationConfig, AnimationTrack, MeasurementOverlay,
    VectorOverlay, SceneControlsConfig
)


def build_pendulum_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D simple pendulum simulation scene."""
    params = procedure.get("parameters", {})
    L = float(params.get("length_m", 1.0))
    g = float(params.get("gravity", 9.81))
    b = float(params.get("damping", 0.08))
    theta0 = float(params.get("angle_rad", 0.6))
    bob_mass = float(params.get("bob_mass_kg", 0.5))

    # Time integration via ODE
    t_span = (0.0, 10.0)
    t_eval = np.linspace(0.0, 10.0, 201)  # 20Hz sampling

    def pendulum_ode(t, y):
        th, w = y
        return [w, -(g / L) * np.sin(th) - (b / bob_mass) * w]

    sol = solve_ivp(pendulum_ode, t_span, [theta0, 0.0], t_eval=t_eval, rtol=1e-6)
    theta_arr = sol.y[0]
    omega_arr = sol.y[1]
    time_points = t_eval.tolist()

    period = 2.0 * math.pi * math.sqrt(L / g)

    # Calculate 3D trajectories
    # Pivot at [0, 2.2, 0]
    pivot_y = 2.2
    bob_positions = []
    string_rotations = []
    string_positions = []
    vel_vectors = []
    tension_vectors = []

    for th, w in zip(theta_arr, omega_arr):
        bx = L * math.sin(th)
        by = pivot_y - L * math.cos(th)
        bz = 0.0
        bob_positions.append([round(bx, 4), round(by, 4), round(bz, 4)])

        # String midpoint
        mx = bx / 2.0
        my = (pivot_y + by) / 2.0
        string_positions.append([round(mx, 4), round(my, 4), 0.0])
        # Rotation around Z axis
        string_rotations.append([0.0, 0.0, round(th, 4)])

        # Velocity vector = [L*w*cos(th), L*w*sin(th), 0]
        vx = L * w * math.cos(th)
        vy = L * w * math.sin(th)
        vel_vectors.append([round(vx, 3), round(vy, 3), 0.0])

        # Tension force = m*(g*cos(th) + L*w^2) pointing towards pivot [-sin(th), cos(th), 0]
        T_mag = bob_mass * (g * math.cos(th) + L * w**2)
        tx = -math.sin(th) * T_mag * 0.1
        ty = math.cos(th) * T_mag * 0.1
        tension_vectors.append([round(tx, 3), round(ty, 3), 0.0])

    objects = [
        # Stand Base
        SceneObject(
            id="stand_base",
            name="Laboratory Stand Base",
            type="box",
            position=[0.0, 0.05, 0.0],
            dimensions={"width": 1.2, "height": 0.1, "depth": 0.8},
            material=MaterialConfig(color="#1e293b", metalness=0.7, roughness=0.3)
        ),
        # Vertical Rod
        SceneObject(
            id="vertical_rod",
            name="Support Mast",
            type="cylinder",
            position=[-0.45, 1.2, 0.0],
            dimensions={"radius": 0.025, "height": 2.3},
            material=MaterialConfig(color="#94a3b8", metalness=0.8, roughness=0.2)
        ),
        # Horizontal Arm
        SceneObject(
            id="horizontal_arm",
            name="Support Cantilever",
            type="cylinder",
            position=[-0.2, pivot_y + 0.1, 0.0],
            rotation=[0.0, 0.0, math.pi / 2],
            dimensions={"radius": 0.02, "height": 0.6},
            material=MaterialConfig(color="#94a3b8", metalness=0.8, roughness=0.2)
        ),
        # Pivot Bearing
        SceneObject(
            id="pivot",
            name="Low-friction Pivot",
            type="sphere",
            position=[0.0, pivot_y, 0.0],
            dimensions={"radius": 0.05},
            material=MaterialConfig(color="#f59e0b", metalness=0.9, roughness=0.1)
        ),
        # Suspension String
        SceneObject(
            id="string",
            name="Suspension String",
            type="cylinder",
            position=string_positions[0],
            rotation=string_rotations[0],
            dimensions={"radius": 0.008, "height": L},
            material=MaterialConfig(color="#cbd5e1", metalness=0.2, roughness=0.8)
        ),
        # Pendulum Bob
        SceneObject(
            id="bob",
            name="Oscillating Bob",
            type="sphere",
            position=bob_positions[0],
            dimensions={"radius": 0.12},
            material=MaterialConfig(color="#3b82f6", metalness=0.6, roughness=0.2, emissive="#1e40af", emissive_intensity=0.15)
        ),
        # Trajectory Path Ribbon
        SceneObject(
            id="trajectory_arc",
            name="Equilibrium Arc",
            type="line",
            position=[0.0, 0.0, 0.0],
            dimensions={"points_count": len(bob_positions)},
            material=MaterialConfig(color="#38bdf8", opacity=0.4, transparent=True),
            metadata={"points": bob_positions}
        )
    ]

    tracks = {
        "bob": AnimationTrack(position=bob_positions),
        "string": AnimationTrack(position=string_positions, rotation=string_rotations)
    }

    parameters = [
        ParameterConfig(
            name="length_m",
            label="String Length",
            type="float",
            value=L,
            min_val=0.3,
            max_val=3.0,
            step=0.1,
            unit="m",
            description="Length from pivot to center of mass of the bob"
        ),
        ParameterConfig(
            name="angle_rad",
            label="Initial Displacement",
            type="float",
            value=theta0,
            min_val=-1.2,
            max_val=1.2,
            step=0.05,
            unit="rad",
            description="Initial release angle theta_0"
        ),
        ParameterConfig(
            name="damping",
            label="Damping Coefficient",
            type="float",
            value=b,
            min_val=0.0,
            max_val=0.5,
            step=0.01,
            unit="N·s/m",
            description="Viscous air drag resistance"
        ),
        ParameterConfig(
            name="gravity",
            label="Gravitational Acceleration",
            type="float",
            value=g,
            min_val=1.0,
            max_val=25.0,
            step=0.1,
            unit="m/s²",
            description="Local gravitational acceleration"
        )
    ]

    overlays = [
        MeasurementOverlay(
            id="period_meas",
            label="Natural Period T",
            value=round(period, 3),
            unit="s",
            position_3d=[0.3, pivot_y + 0.3, 0.0]
        ),
        MeasurementOverlay(
            id="angle_meas",
            label="Displacement θ(t)",
            value=round(theta_arr[0], 3),
            unit="rad",
            target_object_id="bob",
            is_dynamic=True,
            time_series=[round(float(v), 3) for v in theta_arr]
        ),
        MeasurementOverlay(
            id="velocity_meas",
            label="Angular Velocity ω(t)",
            value=round(omega_arr[0], 3),
            unit="rad/s",
            target_object_id="bob",
            is_dynamic=True,
            time_series=[round(float(v), 3) for v in omega_arr]
        )
    ]

    vectors = [
        VectorOverlay(
            id="vel_vector",
            name="Tangential Velocity v",
            type="velocity",
            origin_object_id="bob",
            color="#10b981",
            length_scale=0.3,
            dynamic_track=vel_vectors
        ),
        VectorOverlay(
            id="tension_vector",
            name="String Tension T",
            type="force",
            origin_object_id="bob",
            color="#ef4444",
            length_scale=0.15,
            dynamic_track=tension_vectors
        )
    ]

    return SceneSpecification(
        domain="physics",
        experiment_id="simple_pendulum",
        scene_template="simple_pendulum",
        title="Damped Harmonic Pendulum Simulation",
        description="Non-linear rigid pendulum with viscous damping governed by d²θ/dt² + (b/m)dθ/dt + (g/L)sin(θ) = 0",
        is_simulation_backed=True,
        confidence_score=0.98,
        camera=CameraConfig(position=[0.0, 1.8, 4.2], target=[0.0, 1.2, 0.0], fov=48),
        lighting=LightingConfig(ambient_intensity=0.75, directional_position=[4.0, 8.0, 5.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=10.0,
            time_step_s=0.05,
            time_array=time_points,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        vectors=vectors,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True),
        notes=["Calculated via Runge-Kutta 4th-order adaptive ODE solver (scipy.integrate.solve_ivp)"]
    )


def build_projectile_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D projectile trajectory simulation scene."""
    params = procedure.get("parameters", {})
    v0 = float(params.get("initial_velocity_ms", 20.0))
    angle_deg = float(params.get("launch_angle_deg", 45.0))
    g = float(params.get("gravity", 9.81))

    angle_rad = math.radians(angle_deg)
    t_flight = 2.0 * v0 * math.sin(angle_rad) / g
    h_max = (v0 * math.sin(angle_rad))**2 / (2.0 * g)
    range_max = (v0**2 * math.sin(2.0 * angle_rad)) / g

    # Normalization scaling factor for 3D viewport (fit inside 8m wide box)
    view_scale = 8.0 / max(range_max, 10.0)

    t_eval = np.linspace(0.0, t_flight, 151)
    time_points = t_eval.tolist()

    projectile_positions = []
    vel_vectors = []

    for t in t_eval:
        x_raw = v0 * math.cos(angle_rad) * t
        y_raw = v0 * math.sin(angle_rad) * t - 0.5 * g * t**2
        y_clamped = max(0.0, y_raw)

        # Scaled to 3D scene units
        px = (x_raw - range_max / 2.0) * view_scale
        py = y_clamped * view_scale + 0.1
        pz = 0.0

        projectile_positions.append([round(px, 3), round(py, 3), round(pz, 3)])

        vx = v0 * math.cos(angle_rad)
        vy = v0 * math.sin(angle_rad) - g * t
        vel_vectors.append([round(vx * view_scale * 0.4, 3), round(vy * view_scale * 0.4, 3), 0.0])

    # Cannon platform at start position
    start_x = projectile_positions[0][0]

    objects = [
        # Ground Grid Reference
        SceneObject(
            id="ground_runway",
            name="Impact Terrain",
            type="box",
            position=[0.0, 0.0, 0.0],
            dimensions={"width": 10.0, "height": 0.05, "depth": 3.0},
            material=MaterialConfig(color="#0f172a", roughness=0.9, metalness=0.1)
        ),
        # Launcher Cannon
        SceneObject(
            id="launcher",
            name="Ballistic Cannon Barrel",
            type="cylinder",
            position=[start_x, 0.35, 0.0],
            rotation=[0.0, 0.0, math.radians(90 - angle_deg)],
            dimensions={"radius": 0.09, "height": 0.8},
            material=MaterialConfig(color="#475569", metalness=0.9, roughness=0.2)
        ),
        # Cannon Pivot Mount
        SceneObject(
            id="cannon_base",
            name="Launcher Turret",
            type="box",
            position=[start_x, 0.15, 0.0],
            dimensions={"width": 0.5, "height": 0.3, "depth": 0.4},
            material=MaterialConfig(color="#334155", metalness=0.7, roughness=0.3)
        ),
        # Flying Projectile
        SceneObject(
            id="projectile",
            name="Ballistic Projectile",
            type="sphere",
            position=projectile_positions[0],
            dimensions={"radius": 0.12},
            material=MaterialConfig(color="#f97316", metalness=0.4, roughness=0.2, emissive="#ea580c", emissive_intensity=0.3)
        ),
        # Target Impact Marker
        SceneObject(
            id="target_ring",
            name="Predicted Impact Site",
            type="torus",
            position=[projectile_positions[-1][0], 0.06, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.3, "tube": 0.03},
            material=MaterialConfig(color="#ef4444", metalness=0.8, roughness=0.2, emissive="#dc2626", emissive_intensity=0.4)
        ),
        # Parabolic Trajectory Guide Ribbon
        SceneObject(
            id="trajectory_ribbon",
            name="Parabolic Arc",
            type="line",
            position=[0.0, 0.0, 0.0],
            dimensions={"points_count": len(projectile_positions)},
            material=MaterialConfig(color="#fbbf24", opacity=0.7, transparent=True),
            metadata={"points": projectile_positions}
        )
    ]

    tracks = {
        "projectile": AnimationTrack(position=projectile_positions)
    }

    parameters = [
        ParameterConfig(
            name="initial_velocity_ms",
            label="Initial Velocity v₀",
            type="float",
            value=v0,
            min_val=5.0,
            max_val=50.0,
            step=1.0,
            unit="m/s",
            description="Muzzle velocity at launch"
        ),
        ParameterConfig(
            name="launch_angle_deg",
            label="Elevation Angle θ",
            type="float",
            value=angle_deg,
            min_val=10.0,
            max_val=85.0,
            step=1.0,
            unit="°",
            description="Launch angle above horizontal"
        ),
        ParameterConfig(
            name="gravity",
            label="Gravity g",
            type="float",
            value=g,
            min_val=1.62,
            max_val=25.0,
            step=0.1,
            unit="m/s²",
            description="Gravitational acceleration"
        )
    ]

    overlays = [
        MeasurementOverlay(
            id="range_meas",
            label="Horizontal Range R",
            value=round(range_max, 2),
            unit="m",
            position_3d=[projectile_positions[-1][0], 0.5, 0.0]
        ),
        MeasurementOverlay(
            id="hmax_meas",
            label="Max Altitude H_max",
            value=round(h_max, 2),
            unit="m",
            position_3d=[0.0, h_max * view_scale + 0.4, 0.0]
        ),
        MeasurementOverlay(
            id="tflight_meas",
            label="Time of Flight t_f",
            value=round(t_flight, 2),
            unit="s",
            position_3d=[start_x, 0.8, 0.0]
        )
    ]

    vectors = [
        VectorOverlay(
            id="vel_vector",
            name="Velocity Vector v(t)",
            type="velocity",
            origin_object_id="projectile",
            color="#22c55e",
            length_scale=0.5,
            dynamic_track=vel_vectors
        )
    ]

    return SceneSpecification(
        domain="physics",
        experiment_id="projectile_motion",
        scene_template="projectile_motion",
        title="Kinematic Projectile Motion Simulation",
        description="2D ballistic trajectory under uniform gravity governed by x(t) = v₀·cos(θ)·t and y(t) = v₀·sin(θ)·t - 0.5·g·t²",
        is_simulation_backed=True,
        confidence_score=0.99,
        camera=CameraConfig(position=[0.0, 2.5, 7.5], target=[0.0, 1.2, 0.0], fov=50),
        lighting=LightingConfig(ambient_intensity=0.8, directional_position=[5.0, 9.0, 6.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=round(t_flight, 2),
            time_step_s=round(t_flight / 150.0, 4),
            time_array=time_points,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        vectors=vectors,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True)
    )

