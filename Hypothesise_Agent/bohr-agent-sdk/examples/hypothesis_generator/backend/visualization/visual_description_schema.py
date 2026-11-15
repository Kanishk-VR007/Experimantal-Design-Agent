"""
Pydantic Schema for Visual Reconstruction Instructions (Qwen3-VL-2B Output)
============================================================================
Defines the visual structure, spatial relationships, component hierarchy,
joints, connections, and animation hints extracted from the reference image.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VisualObject(BaseModel):
    """Component or apparatus object identified in the reference image."""
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'input_crank', 'fixed_pivot')")
    name: str = Field(..., description="Descriptive label (e.g. 'Input Crank', 'Pinned Support')")
    geometry: str = Field(default="cylinder", description="Primitive geometry: cylinder, cuboid, sphere, box, gear, wire, beam, node")
    relative_position: str = Field(default="origin", description="Spatial placement cue: left_pivot, center, top_flange, etc.")
    orientation: str = Field(default="horizontal", description="Orientation hint: horizontal, vertical, inclined, angled")
    material: str = Field(default="metallic", description="Material appearance: metallic, matte, glowing, transparent")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


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
    Complete structured visual reconstruction payload provided to DeepSeek R1 7B.
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

