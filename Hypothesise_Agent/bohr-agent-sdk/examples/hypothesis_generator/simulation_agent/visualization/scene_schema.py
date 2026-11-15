"""
Declarative 3D Scene Specification Schema (Pydantic v2)
======================================================
Defines the strict JSON contract between scientific simulation engines,
LLM visualization generator, and the Three.js / React Three Fiber renderer.
Arbitrary executable code is strictly prohibited; only declarative,
allowlisted geometries, transformations, and animation tracks are supported.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class MaterialConfig(BaseModel):
    """Visual material properties for a 3D scene object."""
    color: str = Field(default="#ffffff", description="Hex color or CSS color string")
    metalness: float = Field(default=0.1, ge=0.0, le=1.0)
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    transparent: bool = Field(default=False)
    wireframe: bool = Field(default=False)
    emissive: Optional[str] = Field(default=None, description="Hex color for glowing materials")
    emissive_intensity: float = Field(default=0.0, ge=0.0)


class SceneObject(BaseModel):
    """
    Allowlisted 3D mesh or group in the experiment scene.
    Type must be an allowlisted primitive:
    'box', 'sphere', 'cylinder', 'capsule', 'torus', 'arrow', 'line', 'text', 'plane', 'group'
    """
    id: str = Field(..., description="Unique identifier within the scene, e.g. 'bob', 'support', 'string'")
    name: str = Field(..., description="Human-readable label, e.g. 'Pendulum Bob'")
    type: str = Field(..., description="Allowlisted geometry type: box, sphere, cylinder, capsule, torus, arrow, line, text, plane, group")
    position: List[float] = Field(default=[0.0, 0.0, 0.0], description="[x, y, z] in simulation world coordinates (meters/units)")
    rotation: List[float] = Field(default=[0.0, 0.0, 0.0], description="[rx, ry, rz] in radians")
    scale: List[float] = Field(default=[1.0, 1.0, 1.0], description="[sx, sy, sz] scale factors")
    dimensions: Dict[str, float] = Field(default_factory=dict, description="Shape parameters: radius, height, width, length, depth, etc.")
    material: MaterialConfig = Field(default_factory=MaterialConfig)
    children: Optional[List["SceneObject"]] = Field(default=None, description="Nested child objects for hierarchical scene graphs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain properties (e.g. mass_kg, element_symbol)")


class CameraConfig(BaseModel):
    """Scene camera setup."""
    position: List[float] = Field(default=[0.0, 2.5, 6.0], description="[x, y, z] camera origin")
    target: List[float] = Field(default=[0.0, 0.5, 0.0], description="[x, y, z] lookAt focal point")
    fov: int = Field(default=50, ge=20, le=100, description="Field of view in degrees")


class LightingConfig(BaseModel):
    """Studio lighting for clear scientific visibility."""
    ambient_intensity: float = Field(default=0.7, ge=0.0, le=2.0)
    directional_position: List[float] = Field(default=[5.0, 10.0, 7.0])
    directional_intensity: float = Field(default=0.9, ge=0.0, le=3.0)


class ParameterConfig(BaseModel):
    """Interactive physical or experimental parameter controllable by the user."""
    name: str = Field(..., description="Key matching simulation parameter, e.g. 'length_m', 'angle_rad'")
    label: str = Field(..., description="Human-readable label, e.g. 'Pendulum Length'")
    type: str = Field(default="float", description="'float', 'int', 'select', 'boolean'")
    value: Any = Field(..., description="Current value")
    min_val: Optional[float] = Field(default=None, description="Lower slider bound")
    max_val: Optional[float] = Field(default=None, description="Upper slider bound")
    step: Optional[float] = Field(default=None, description="Slider step increment")
    unit: str = Field(default="", description="Physical unit, e.g. 'm', 'rad', 'N', 'K'")
    options: Optional[List[str]] = Field(default=None, description="Available options if type is 'select'")
    description: str = Field(default="", description="Scientific context for this parameter")


class AnimationTrack(BaseModel):
    """Keyframed or sampled property track for one object."""
    position: Optional[List[List[float]]] = Field(default=None, description="Array of [x, y, z] coords per time step")
    rotation: Optional[List[List[float]]] = Field(default=None, description="Array of [rx, ry, rz] Euler angles per time step")
    scale: Optional[List[List[float]]] = Field(default=None, description="Array of [sx, sy, sz] per time step")
    emissive_intensity: Optional[List[float]] = Field(default=None, description="Emissive pulse values per time step")
    custom: Optional[Dict[str, List[Any]]] = Field(default=None, description="Any custom scalar track")


class AnimationConfig(BaseModel):
    """Time-dependent motion and transformation synchronization."""
    has_animation: bool = Field(default=False)
    duration_s: float = Field(default=0.0, description="Total duration of simulated animation in seconds")
    time_step_s: float = Field(default=0.05, description="Time delta between sampled frames")
    time_array: List[float] = Field(default_factory=list, description="Array of time points t_0, t_1, ..., t_N")
    tracks: Dict[str, AnimationTrack] = Field(default_factory=dict, description="Mapping: object_id -> AnimationTrack")


class MeasurementOverlay(BaseModel):
    """Annotated measurement readout rendered in 3D scene space or HUD."""
    id: str = Field(..., description="Unique overlay ID")
    label: str = Field(..., description="Measurement title, e.g. 'Period T', 'Deflection δ'")
    value: Any = Field(..., description="Numerical or text value")
    unit: str = Field(default="", description="Unit, e.g. 's', 'mm', 'MPa'")
    target_object_id: Optional[str] = Field(default=None, description="ID of the object this label anchors to")
    position_3d: Optional[List[float]] = Field(default=None, description="Anchor coordinate [x, y, z]")
    is_dynamic: bool = Field(default=False, description="Whether value changes across the animation timeline")
    time_series: Optional[List[float]] = Field(default=None, description="Values matching animation time_array")


class VectorOverlay(BaseModel):
    """Directional 3D vector arrow visualizing physics quantities."""
    id: str = Field(..., description="Unique vector ID")
    name: str = Field(..., description="Label, e.g. 'Velocity v', 'Tension T'")
    type: str = Field(default="velocity", description="'velocity', 'force', 'acceleration', 'normal'")
    origin_object_id: str = Field(..., description="Object from which the arrow originates")
    color: str = Field(default="#10b981", description="Arrow color hex")
    visible_by_default: bool = Field(default=True)
    length_scale: float = Field(default=1.0, description="Scale factor to convert quantity to 3D meter units")
    static_vector: Optional[List[float]] = Field(default=None, description="Fixed direction [vx, vy, vz]")
    dynamic_track: Optional[List[List[float]]] = Field(default=None, description="Vector [vx, vy, vz] per time step")


class SceneControlsConfig(BaseModel):
    """Interactive control toggles."""
    allow_orbit: bool = Field(default=True)
    allow_pan: bool = Field(default=True)
    allow_zoom: bool = Field(default=True)
    show_grid: bool = Field(default=True)
    show_axes: bool = Field(default=True)
    allow_tweak_parameters: bool = Field(default=True)
    background_color: str = Field(default="#0b0f19")


class SceneSpecification(BaseModel):
    """
    Complete root declarative 3D scene specification.
    Validated by Pydantic before transmission to frontend Three.js renderer.
    """
    version: str = Field(default="1.0.0")
    domain: str = Field(..., description="Scientific domain: physics, chemistry, biology, civil_engineering, mechanical_engineering, electronics, computer_science, general")
    experiment_id: str = Field(..., description="Identifier of the experiment, e.g. 'simple_pendulum'")
    scene_template: str = Field(..., description="Visualization template key, e.g. 'simple_pendulum', 'molecular_geometry', 'beam_deformation', 'gear_train', 'arduino_circuit', 'generic_apparatus'")
    title: str = Field(..., description="Experiment title")
    description: str = Field(default="", description="Scientific summary of the visualization")
    is_simulation_backed: bool = Field(default=True, description="True if driven by deterministic numerical engine; False if illustrative fallback")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    lighting: LightingConfig = Field(default_factory=LightingConfig)
    objects: List[SceneObject] = Field(default_factory=list)
    parameters: List[ParameterConfig] = Field(default_factory=list)
    animation: AnimationConfig = Field(default_factory=AnimationConfig)
    measurement_overlays: List[MeasurementOverlay] = Field(default_factory=list)
    vectors: List[VectorOverlay] = Field(default_factory=list)
    controls: SceneControlsConfig = Field(default_factory=SceneControlsConfig)
    notes: List[str] = Field(default_factory=list)

