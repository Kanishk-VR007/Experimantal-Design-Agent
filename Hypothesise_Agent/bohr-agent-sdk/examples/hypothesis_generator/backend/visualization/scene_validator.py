"""
Scene Specification Validator & Safety Guard
=============================================
Enforces strict scientific and security constraints on declarative 3D scenes:
  1. Strict Allowlisted Primitive Types (box, sphere, cylinder, capsule, torus, arrow, line, text, plane, group, mesh).
  2. Absolute Prohibition of Executable Code (detects and strips script tags, javascript:, eval, etc.).
  3. Physical Boundary & Coordinate Sanity Checks (positive non-zero finite dimensions, finite coordinates).
  4. Graph Integrity (verifies connections refer to existing object IDs).
  5. Animation Track Time Synchronization (ensures track sample lengths match duration/step).
  6. Solver/Scene Synchronization Check (rejects mismatched experiment_id or scene_template).
"""

import logging
import math
import re
from typing import List, Optional, Tuple

from simulation_agent.visualization.scene_schema import SceneObject, SceneSpecification

logger = logging.getLogger(__name__)

ALLOWLISTED_GEOMETRIES = frozenset({
    "box", "sphere", "cylinder", "capsule", "torus", "arrow", "line", "text", "plane", "group", "mesh"
})

FORBIDDEN_CODE_PATTERNS = [
    re.compile(r"<script.*?>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\beval\(", re.IGNORECASE),
    re.compile(r"\bFunction\(", re.IGNORECASE),
    re.compile(r"\bwindow\.", re.IGNORECASE),
    re.compile(r"\bdocument\.", re.IGNORECASE),
]


class SceneValidationError(ValueError):
    """Raised when a SceneSpecification violates safety or integrity rules."""
    pass


def validate_scene_specification(
    scene: SceneSpecification,
    expected_experiment_id: Optional[str] = None,
    expected_template: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate a SceneSpecification object.
    Returns `(is_valid, list_of_warning_or_error_messages)`.
    """
    issues: List[str] = []
    blocking_errors: List[str] = []
    object_ids = set()

    def _check_string_safety(val: str, field_name: str):
        for pat in FORBIDDEN_CODE_PATTERNS:
            if pat.search(val):
                raise SceneValidationError(
                    f"Security Alert: Prohibited script/code detected in {field_name}: '{val[:40]}'"
                )

    def _validate_object(obj: SceneObject, depth: int = 0):
        if depth > 10:
            issues.append(f"Scene object hierarchy too deep (max 10) at '{obj.id}'")
            return

        _check_string_safety(obj.id, "object.id")
        _check_string_safety(obj.name, "object.name")
        _check_string_safety(obj.type, "object.type")

        if obj.type.lower() not in ALLOWLISTED_GEOMETRIES:
            msg = f"Invalid geometry type '{obj.type}' in object '{obj.id}'. Defaulting to 'box'."
            issues.append(msg)
            blocking_errors.append(msg)
            obj.type = "box"

        if obj.id in object_ids:
            issues.append(f"Duplicate object ID detected: '{obj.id}'")
        object_ids.add(obj.id)

        if len(obj.position) != 3 or any(
            not isinstance(p, (int, float)) or not math.isfinite(float(p))
            for p in obj.position
        ):
            msg = f"Invalid position coordinates on object '{obj.id}'"
            issues.append(msg)
            blocking_errors.append(msg)
            obj.position = [0.0, 0.0, 0.0]

        for dim_k, dim_v in list(obj.dimensions.items()):
            if not isinstance(dim_v, (int, float)) or not math.isfinite(float(dim_v)) or dim_v <= 0:
                issues.append(f"Object '{obj.id}' dimension '{dim_k}' must be > 0 and finite. Resetting to 0.1.")
                obj.dimensions[dim_k] = 0.1

        if obj.children:
            for ch in obj.children:
                _validate_object(ch, depth + 1)

    # 1. Validate all objects
    for root_obj in scene.objects:
        _validate_object(root_obj, depth=0)

    # 2. Check measurement targets
    for m in scene.measurement_overlays:
        _check_string_safety(m.id, "measurement.id")
        _check_string_safety(m.label, "measurement.label")
        if m.target_object_id and m.target_object_id not in object_ids:
            issues.append(f"Measurement overlay '{m.id}' targets non-existent object '{m.target_object_id}'")

    # 3. Check vector targets
    for vec in scene.vectors:
        _check_string_safety(vec.id, "vector.id")
        _check_string_safety(vec.name, "vector.name")
        if vec.origin_object_id and vec.origin_object_id not in object_ids:
            issues.append(f"Vector '{vec.id}' originates from non-existent object '{vec.origin_object_id}'")

    # 4. Check animation synchronization
    if scene.animation and scene.animation.has_animation:
        t_len = len(scene.animation.time_array)
        for obj_id, track in scene.animation.tracks.items():
            if obj_id not in object_ids:
                issues.append(f"Animation track targets unknown object '{obj_id}'")
            if track.position and t_len > 0 and len(track.position) != t_len:
                msg = (
                    f"Invalid animation track length for '{obj_id}': "
                    f"position samples ({len(track.position)}) mismatch time_array length ({t_len})"
                )
                issues.append(msg)
                blocking_errors.append(msg)

    # 5. String safety on root properties
    _check_string_safety(scene.title, "scene.title")
    _check_string_safety(scene.description, "scene.description")
    _check_string_safety(scene.scene_template, "scene.scene_template")

    # 6. Solver <-> 3D scene synchronization check
    if expected_template and scene.scene_template != expected_template:
        msg = (
            f"Scene/Solver template mismatch: expected '{expected_template}', "
            f"got '{scene.scene_template}'"
        )
        issues.append(msg)
        blocking_errors.append(msg)

    if expected_experiment_id and scene.experiment_id != expected_experiment_id:
        # Allow if template matches (e.g., canonical beam variant using beam_deformation)
        if not expected_template or scene.scene_template != expected_template:
            msg = (
                f"Scene/Solver experiment_id mismatch: expected '{expected_experiment_id}', "
                f"got '{scene.experiment_id}'"
            )
            issues.append(msg)
            blocking_errors.append(msg)

    is_valid = len(blocking_errors) == 0
    if issues:
        logger.info(
            "[SceneValidator] Scene '%s' validated (valid=%s) with %d notices: %s",
            scene.experiment_id,
            is_valid,
            len(issues),
            "; ".join(issues[:3]),
        )
    else:
        logger.info("[SceneValidator] Scene '%s' passed all structural & security checks.", scene.experiment_id)

    return is_valid, issues
