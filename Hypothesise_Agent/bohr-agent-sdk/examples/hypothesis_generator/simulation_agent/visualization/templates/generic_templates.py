"""
Generic Scientific Laboratory 3D Scene Template
===============================================
Provides an honest, safe, non-blank fallback visualization when an experiment
does not map to a pre-defined deterministic physical/chemical/mechanical template:
- Renders a clean 3D laboratory apparatus (specimen chamber, optical/sensor probe, diagnostic pedestal)
- Explicitly sets `is_simulation_backed = False`
- Displays notes distinguishing illustrative 3D visualization from validated numerical data
- Never leaves the canvas blank or broken
"""

import math
from typing import Dict, Any, List
from ..scene_schema import (
    SceneSpecification, SceneObject, MaterialConfig,
    CameraConfig, LightingConfig, ParameterConfig,
    AnimationConfig, AnimationTrack, MeasurementOverlay,
    SceneControlsConfig
)


def build_generic_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds a safe, elegant generic 3D laboratory visualization for unclassified or custom experiments."""
    domain = procedure.get("domain", "general")
    hypothesis = procedure.get("hypothesis", "Scientific Experiment")
    title = f"{domain.replace('_', ' ').title()} Experimental Apparatus"

    objects = [
        # Lab Countertop
        SceneObject(
            id="lab_counter",
            name="Optical Granite Countertop",
            type="box",
            position=[0.0, -0.05, 0.0],
            dimensions={"width": 3.0, "height": 0.1, "depth": 2.2},
            material=MaterialConfig(color="#0f172a", metalness=0.8, roughness=0.2)
        ),
        # Specimen Pedestal Base
        SceneObject(
            id="specimen_pedestal",
            name="Measurement Stage",
            type="cylinder",
            position=[0.0, 0.25, 0.0],
            dimensions={"radius": 0.6, "height": 0.4},
            material=MaterialConfig(color="#334155", metalness=0.7, roughness=0.3)
        ),
        # Interactive Sample Chamber (Translucent Cylinder)
        SceneObject(
            id="sample_chamber",
            name="Environmental Test Chamber",
            type="cylinder",
            position=[0.0, 0.75, 0.0],
            dimensions={"radius": 0.4, "height": 0.6},
            material=MaterialConfig(color="#38bdf8", opacity=0.35, transparent=True, metalness=0.1, roughness=0.1)
        ),
        # Core Reaction Sample Sphere
        SceneObject(
            id="specimen_core",
            name="Specimen Under Observation",
            type="sphere",
            position=[0.0, 0.75, 0.0],
            dimensions={"radius": 0.18},
            material=MaterialConfig(color="#6366f1", emissive="#4f46e5", emissive_intensity=0.5, metalness=0.4, roughness=0.2)
        ),
        # Upper Sensor Gantry
        SceneObject(
            id="sensor_gantry",
            name="Spectrometric Probe Array",
            type="cylinder",
            position=[0.0, 1.4, 0.0],
            dimensions={"radius": 0.12, "height": 0.4},
            material=MaterialConfig(color="#94a3b8", metalness=0.9, roughness=0.1)
        ),
        # Holographic Data Ring
        SceneObject(
            id="hologram_ring",
            name="Telemetry Ring",
            type="torus",
            position=[0.0, 0.75, 0.0],
            rotation=[math.pi / 2, 0.0, 0.0],
            dimensions={"radius": 0.55, "tube": 0.015},
            material=MaterialConfig(color="#22d3ee", emissive="#06b6d4", emissive_intensity=0.8, transparent=True, opacity=0.7)
        )
    ]

    # Gentle pulsing & rotation animation
    frames = 80
    time_array = [round(t * 0.05, 3) for t in range(frames)]
    ring_rots = []
    core_pulses = []
    for t in time_array:
        ring_rots.append([math.pi / 2, round(t * 0.5, 3), 0.0])
        pulse = 0.5 + 0.3 * math.sin(t * 2.0)
        core_pulses.append(round(pulse, 3))

    tracks = {
        "hologram_ring": AnimationTrack(rotation=ring_rots),
        "specimen_core": AnimationTrack(emissive_intensity=core_pulses)
    }

    # Extract dynamic measurements from numerical_results if present
    overlays: List[MeasurementOverlay] = []
    flat_results = {}
    for k, v in numerical_results.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat_results[f"{k}.{sub_k}"] = sub_v
        else:
            flat_results[k] = v

    pos_y = 1.3
    for idx, (k, v) in enumerate(list(flat_results.items())[:3]):
        overlays.append(MeasurementOverlay(
            id=f"metric_{idx}",
            label=k.replace("_", " ").title(),
            value=round(float(v), 3) if isinstance(v, (int, float)) else str(v),
            position_3d=[0.8, pos_y, 0.0]
        ))
        pos_y -= 0.3

    return SceneSpecification(
        domain=domain,
        experiment_id="generic_experiment",
        scene_template="generic_apparatus",
        title=title,
        description=f"Generic scientific 3D apparatus for testing: {hypothesis[:120]}...",
        is_simulation_backed=False,
        confidence_score=0.85,
        camera=CameraConfig(position=[0.0, 1.8, 3.2], target=[0.0, 0.75, 0.0], fov=45),
        lighting=LightingConfig(ambient_intensity=0.8, directional_position=[4.0, 7.0, 4.0]),
        objects=objects,
        parameters=[
            ParameterConfig(
                name="observation_rate",
                label="Sensor Sampling Frequency",
                type="float",
                value=10.0,
                min_val=1.0,
                max_val=100.0,
                step=1.0,
                unit="Hz"
            )
        ],
        animation=AnimationConfig(
            has_animation=True,
            duration_s=4.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True),
        notes=[
            "Illustrative 3D visualization: Specific mechanical/chemical 3D equations are not mapped for this custom setup.",
            "All quantitative findings are preserved in the numerical results and 2D charts below."
        ]
    )

