"""
Pydantic Schema for Visual Reconstruction Instructions (Qwen3-VL-4B-Thinking Output)
====================================================================================
Defines the visual structure, spatial relationships, component hierarchy,
joints, connections, and animation hints extracted from the reference image.
Includes resilient coercion validators so LLM formatting quirks (e.g., string
instead of list, float confidence outside [0, 1]) normalize safely.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


def _coerce_str_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if "\n" in s:
            return [p.strip(" -•*\t") for p in s.splitlines() if p.strip(" -•*\t")]
        return [s]
    if isinstance(v, (list, tuple, set)):
        return [str(x).strip() for x in v if x is not None and str(x).strip()]
    return [str(v)]


class VisualObject(BaseModel):
    """Component or apparatus object identified in the reference image."""
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'input_crank', 'fixed_pivot')")
    name: str = Field(default="Component", description="Descriptive label (e.g. 'Input Crank', 'Pinned Support')")
    geometry: str = Field(default="cylinder", description="Primitive geometry: cylinder, cuboid, sphere, box, gear, wire, beam, node")
    relative_position: str = Field(default="origin", description="Spatial placement cue: left_pivot, center, top_flange, etc.")
    orientation: str = Field(default="horizontal", description="Orientation hint: horizontal, vertical, inclined, angled")
    material: str = Field(default="metallic", description="Material appearance: metallic, matte, glowing, transparent")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)

    @field_validator("relative_position", "orientation", "material", "geometry", "name", mode="before")
    @classmethod
    def _stringify(cls, v: Any) -> str:
        if v is None:
            return "default"
        return str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_conf(cls, v: Any) -> float:
        try:
            f = float(v)
            return max(0.0, min(1.0, f))
        except Exception:
            return 0.85


class VisualConnection(BaseModel):
    """Mechanical joint, electrical lead, structural contact, or graph edge."""
    source: str = Field(..., description="Source object ID")
    target: str = Field(..., description="Target object ID")
    type: str = Field(default="fixed_joint", description="revolute_joint, fixed_joint, sliding_joint, gear_mesh, wire_lead, structural_support, directed_edge")


class SceneComposition(BaseModel):
    """Overall camera, perspective, and composition extracted from the reference image."""
    camera_view: str = Field(default="three_quarter", description="three_quarter, elevation, top_down, isometric")
    coordinate_system: str = Field(default="right_handed", description="Coordinate conventions")
    layout: str = Field(default="horizontal", description="Overall arrangement: horizontal, vertical, planar, circular")


class VisualReconstructionInstructions(BaseModel):
    """
    Complete structured visual reconstruction payload provided to `main_reasoner` (DeepSeek-R1-0528-Qwen3-8B).
    """
    domain: str = Field(default="general")
    scene_type: str = Field(default="apparatus_setup")
    scene_composition: SceneComposition = Field(default_factory=SceneComposition)
    objects: List[VisualObject] = Field(default_factory=list)
    connections: List[VisualConnection] = Field(default_factory=list)
    visual_instructions: List[str] = Field(default_factory=list, description="Step-by-step visual assembly directives")
    animation_hints: List[str] = Field(default_factory=list, description="Kinematic motion, rotation, or current pulse hints")
    uncertainties: List[str] = Field(default_factory=list, description="Explicitly noted visual ambiguities or unmeasured dimensions")
    reference_attribution: Dict[str, str] = Field(default_factory=dict, description="Source name, URL, and license metadata")

    @field_validator("visual_instructions", "animation_hints", "uncertainties", mode="before")
    @classmethod
    def _normalize_lists(cls, v: Any) -> List[str]:
        return _coerce_str_list(v)

    @field_validator("reference_attribution", mode="before")
    @classmethod
    def _normalize_attrib(cls, v: Any) -> Dict[str, str]:
        if not isinstance(v, dict):
            return {}
        return {str(k): str(val) for k, val in v.items() if val is not None}
