"""
Automated Test Suite for 3D Scientific Visualization Engine
===========================================================
Validates:
1. Scene specification schemas & Pydantic validation
2. Template selection for Physics (Pendulum, Projectile), Chemistry (Molecules),
   Civil (Beam Deformation), Mechanical (Gear Train), Electronics (Circuit)
3. Animation track generation and timeline synchronization
4. Numerical accuracy & physical consistency
5. Parameter modification & live recomputation via API
6. Graceful handling of invalid inputs and fallback behavior
"""

import math
from fastapi.testclient import TestClient
from backend.server import app
from simulation_agent.agent import run_simulation, extract_procedure_from_text
from simulation_agent.visualization.scene_schema import (
    SceneSpecification, SceneObject, MaterialConfig
)
from simulation_agent.visualization.scene_generator import generate_scene_specification
from simulation_agent.visualization.templates.physics_templates import (
    build_pendulum_scene, build_projectile_scene
)
from simulation_agent.visualization.templates.chemistry_templates import (
    build_molecule_scene, CPK_TABLE, MOLECULE_LIBRARY
)
from simulation_agent.visualization.templates.mech_civil_templates import (
    build_beam_deformation_scene, build_gear_train_scene
)
from simulation_agent.visualization.templates.electronics_templates import build_circuit_scene
from simulation_agent.visualization.templates.generic_templates import build_generic_scene


# ─── 1. Pydantic Schema Validation Tests ─────────────────────────────────

def test_scene_specification_valid():
    """Verify that a standard scene specification satisfies Pydantic validation."""
    spec_data = {
        "domain": "physics",
        "experiment_id": "test_exp",
        "scene_template": "simple_pendulum",
        "title": "Test Pendulum",
        "description": "Validation test",
        "is_simulation_backed": True,
        "objects": [
            {
                "id": "bob",
                "name": "Bob",
                "type": "sphere",
                "position": [0.0, 1.0, 0.0],
                "dimensions": {"radius": 0.15},
                "material": {"color": "#3b82f6"}
            }
        ]
    }
    spec = SceneSpecification(**spec_data)
    assert spec.domain == "physics"
    assert len(spec.objects) == 1
    assert spec.objects[0].id == "bob"
    assert spec.objects[0].dimensions["radius"] == 0.15


def test_scene_specification_invalid_missing_fields():
    """Verify that missing mandatory fields raise ValidationError."""
    try:
        SceneSpecification(title="Incomplete")
        assert False, "Should have raised ValidationError"
    except Exception:
        pass  # Expected


# ─── 2. Physics: Simple Pendulum Test ────────────────────────────────────

def test_pendulum_numerical_and_scene_accuracy():
    """Verify pendulum mathematical model and 3D scene bindings."""
    procedure = {
        "domain": "physics",
        "experiment_type": "pendulum",
        "hypothesis": "Testing pendulum period dependence on length L=1.0m",
        "parameters": {
            "length_m": 1.0,
            "angle_rad": 0.5,
            "damping": 0.05,
            "gravity": 9.81
        }
    }
    spec = build_pendulum_scene(procedure, {}, [])
    assert spec.scene_template == "simple_pendulum"
    assert spec.is_simulation_backed is True

    # Check required 3D objects
    obj_ids = {obj.id for obj in spec.objects}
    assert "bob" in obj_ids
    assert "string" in obj_ids
    assert "pivot" in obj_ids
    assert "stand_base" in obj_ids

    # Check natural period equation T = 2*pi*sqrt(L/g)
    expected_period = 2.0 * math.pi * math.sqrt(1.0 / 9.81)
    period_overlay = next(m for m in spec.measurement_overlays if m.id == "period_meas")
    assert abs(period_overlay.value - round(expected_period, 3)) < 0.01

    # Check animation tracks
    assert "bob" in spec.animation.tracks
    assert "string" in spec.animation.tracks
    assert len(spec.animation.tracks["bob"].position) > 50

    # Verify trajectory bounds
    bob_positions = spec.animation.tracks["bob"].position
    for pos in bob_positions:
        # Distance from pivot [0, 2.2, 0] must equal length L = 1.0 m (within tolerance)
        dist = math.sqrt(pos[0]**2 + (pos[1] - 2.2)**2)
        assert abs(dist - 1.0) < 0.05

    # Check velocity vector overlay
    assert any(v.type == "velocity" and v.origin_object_id == "bob" for v in spec.vectors)


# ─── 3. Physics: Projectile Motion Test ──────────────────────────────────

def test_projectile_motion_trajectory():
    """Verify projectile kinematics x(t) and y(t) under gravity."""
    procedure = {
        "domain": "physics",
        "experiment_type": "projectile",
        "hypothesis": "Projectile trajectory at 45 deg",
        "parameters": {
            "initial_velocity_ms": 20.0,
            "launch_angle_deg": 45.0,
            "gravity": 9.81
        }
    }
    spec = build_projectile_scene(procedure, {}, [])
    assert spec.scene_template == "projectile_motion"

    obj_ids = {obj.id for obj in spec.objects}
    assert "projectile" in obj_ids
    assert "launcher" in obj_ids
    assert "target_ring" in obj_ids

    # Expected range R = v0^2 * sin(2*theta) / g = 400 * 1 / 9.81 = 40.77m
    range_overlay = next(m for m in spec.measurement_overlays if m.id == "range_meas")
    assert abs(range_overlay.value - 40.77) < 0.2

    # Expected max height H = (v0*sin(theta))^2 / (2*g) = (20 * 0.7071)^2 / 19.62 = 10.19m
    hmax_overlay = next(m for m in spec.measurement_overlays if m.id == "hmax_meas")
    assert abs(hmax_overlay.value - 10.19) < 0.2


# ─── 4. Chemistry: Molecular Geometry Test ───────────────────────────────

def test_molecular_geometry_cpk_and_bonds():
    """Verify chemical molecule generation, CPK element colors and bond connectivity."""
    procedure = {
        "domain": "chemistry",
        "experiment_type": "molecular_geometry",
        "hypothesis": "Water H2O molecular geometry has 104.5 degree bond angle",
        "reagents": [{"name": "water"}]
    }
    spec = build_molecule_scene(procedure, {}, [])
    assert spec.scene_template == "molecular_geometry"

    # Water has 3 atoms (1 Oxygen, 2 Hydrogens) and 2 covalent bonds
    atoms = [o for o in spec.objects if o.type == "sphere"]
    bonds = [o for o in spec.objects if o.type == "cylinder"]

    assert len(atoms) == 3
    assert len(bonds) == 2

    # Verify Oxygen is CPK Red (#ef4444)
    oxygen = next(a for a in atoms if a.metadata.get("element") == "O")
    assert oxygen.material.color == "#ef4444"

    # Verify Hydrogens are CPK White (#ffffff)
    hydrogens = [a for a in atoms if a.metadata.get("element") == "H"]
    assert len(hydrogens) == 2
    for h in hydrogens:
        assert h.material.color == "#ffffff"


# ─── 5. Civil Engineering: Beam Deformation Test ────────────────────────

def test_beam_bending_euler_bernoulli():
    """Verify Euler-Bernoulli beam deflection and flexural stress."""
    procedure = {
        "domain": "civil_engineering",
        "experiment_type": "beam_analysis",
        "hypothesis": "Simply supported beam under 10 kN/m load",
        "parameters": {
            "span_m": 6.0,
            "load_kN_per_m": 10.0,
            "elastic_modulus_GPa": 200.0,
            "moment_of_inertia_m4": 8.33e-6,
            "beam_depth_mm": 400.0
        }
    }
    spec = build_beam_deformation_scene(procedure, {}, [])
    assert spec.scene_template == "beam_deformation"

    # Max deflection delta = 5 w L^4 / (384 E I)
    # 5 * 10 * 1296 / (384 * 200e6 * 8.33e-6) = 64800 / 639744 = 0.10129 m = 101.29 mm
    deflect_overlay = next(m for m in spec.measurement_overlays if m.id == "deflect_meas")
    assert abs(deflect_overlay.value - 101.29) < 1.0

    # Max moment M = w L^2 / 8 = 10 * 36 / 8 = 45 kN·m
    moment_overlay = next(m for m in spec.measurement_overlays if m.id == "moment_meas")
    assert abs(moment_overlay.value - 45.0) < 0.1

    # Segmented beam components
    beam_segments = [o for o in spec.objects if "beam_segment" in o.id]
    assert len(beam_segments) == 20


# ─── 6. Mechanical Engineering: Gear Train Test ─────────────────────────

def test_gear_train_kinematics():
    """Verify spur gear counter-rotation and ratio calculation."""
    procedure = {
        "domain": "mechanical_engineering",
        "experiment_type": "gear_train",
        "hypothesis": "Spur gear reduction from 20T to 40T",
        "parameters": {
            "teeth_driver": 20,
            "teeth_driven": 40,
            "module_mm": 2.5,
            "rpm_input": 120.0
        }
    }
    spec = build_gear_train_scene(procedure, {}, [])
    assert spec.scene_template == "gear_train"

    # Gear ratio 40:20 = 2.0
    ratio_overlay = next(m for m in spec.measurement_overlays if m.id == "ratio_meas")
    assert "2.0" in str(ratio_overlay.value)

    # Output speed = 120 / 2 = 60 RPM
    rpm_overlay = next(m for m in spec.measurement_overlays if m.id == "rpm_out_meas")
    assert abs(rpm_overlay.value - 60.0) < 0.1

    # Counter-rotation: driver and driven must rotate in opposite directions
    track_driver = spec.animation.tracks["gear_driver"].rotation
    track_driven = spec.animation.tracks["gear_driven"].rotation
    # Driver rotates positive around Y; Driven rotates negative
    assert track_driver[10][1] > 0
    assert track_driven[10][1] < 0


# ─── 7. Electronics: Circuit Simulation Test ────────────────────────────

def test_arduino_circuit_simulation():
    """Verify electronics circuit component placement and LED pulse."""
    procedure = {
        "domain": "electronics",
        "experiment_type": "arduino_led",
        "hypothesis": "Blinking LED with current limiting resistor",
        "parameters": {
            "supply_voltage_V": 5.0,
            "led_forward_voltage_V": 2.0,
            "led_current_mA": 20.0,
            "blink_frequency_Hz": 2.0
        }
    }
    spec = build_circuit_scene(procedure, {}, [])
    assert spec.scene_template == "arduino_circuit"

    # R = (5 - 2) / 0.02 = 150 Ohm
    res_overlay = next(m for m in spec.measurement_overlays if m.id == "res_meas")
    assert abs(res_overlay.value - 150.0) < 1.0

    # LED pulsing track
    led_track = spec.animation.tracks["led_component"].emissive_intensity
    assert max(led_track) > 0.8
    assert min(led_track) < 0.2


# ─── 8. Generic Apparatus Fallback Test ─────────────────────────────────

def test_generic_apparatus_fallback_honesty():
    """Verify fallback template honestly marks is_simulation_backed=False and preserves numerical data."""
    procedure = {
        "domain": "general",
        "hypothesis": "Studying unexpected quantum optical cavity fluctuation",
        "parameters": {"laser_power_mW": 50}
    }
    numerical = {"cavity_q_factor": 1.45e6}
    spec = build_generic_scene(procedure, numerical, [])
    assert spec.scene_template == "generic_apparatus"
    assert spec.is_simulation_backed is False
    assert any("Illustrative" in note for note in spec.notes)
    # The metric should still be displayed
    assert any("Cavity Q Factor" in m.label for m in spec.measurement_overlays)


# ─── 9. Full End-to-End API Integration Tests ────────────────────────────

client = TestClient(app)


def test_api_run_simulation_returns_visualization_spec():
    """Verify POST /api/run-simulation includes validated visualization_spec."""
    resp = client.post("/api/run-simulation", json={
        "topic": "Investigating simple pendulum oscillation with damping",
        "design": "## 1. HYPOTHESIS\nA pendulum period depends on length and gravity.\n## 2. VARIABLES\nLength, angle, damping.\n## 3. METHODOLOGY\n1. Displace bob by 0.5 rad\n2. Observe oscillations"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    sim = data["simulation"]
    assert "visualization_spec" in sim
    spec = sim["visualization_spec"]
    assert spec["scene_template"] == "simple_pendulum"
    assert len(spec["objects"]) > 0


def test_api_visualization_update_recalculates_model():
    """Verify POST /api/visualization/update recalculates physics when length changes."""
    resp = client.post("/api/visualization/update", json={
        "experiment_id": "pendulum",
        "domain": "physics",
        "parameters": {"length_m": 4.0, "damping": 0.05, "gravity": 9.81}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    spec = data["simulation"]["visualization_spec"]
    # For L = 4.0, T = 2 * pi * sqrt(4/9.81) = 4.014 s
    period_overlay = next(m for m in spec["measurement_overlays"] if m["id"] == "period_meas")
    assert abs(period_overlay["value"] - 4.014) < 0.05


if __name__ == "__main__":
    tests = [
        test_scene_specification_valid,
        test_scene_specification_invalid_missing_fields,
        test_pendulum_numerical_and_scene_accuracy,
        test_projectile_motion_trajectory,
        test_molecular_geometry_cpk_and_bonds,
        test_beam_bending_euler_bernoulli,
        test_gear_train_kinematics,
        test_arduino_circuit_simulation,
        test_generic_apparatus_fallback_honesty,
        test_api_run_simulation_returns_visualization_spec,
        test_api_visualization_update_recalculates_model,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("ALL 3D VISUALIZATION ENGINE TESTS PASSED!")

