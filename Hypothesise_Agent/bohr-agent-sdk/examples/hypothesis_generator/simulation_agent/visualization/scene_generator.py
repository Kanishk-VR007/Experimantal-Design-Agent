"""
Scene Specification Generator
=============================
Inspects experiment procedure and simulation results, selects the optimal domain
template, builds the declarative 3D scene specification, and validates it with Pydantic.
"""

import re
from typing import Dict, Any, List
from .scene_schema import SceneSpecification
from .templates.physics_templates import build_pendulum_scene, build_projectile_scene
from .templates.chemistry_templates import build_molecule_scene
from .templates.mech_civil_templates import build_beam_deformation_scene, build_gear_train_scene
from .templates.electronics_templates import build_circuit_scene
from .templates.cs_templates import build_cs_scene
from .templates.generic_templates import build_generic_scene


def _has_kw(text: str, keywords: List[str]) -> bool:
    """Matches keywords with word boundary checks for short acronyms to avoid false positives (e.g. 'gravity' matching 'vit')."""
    for kw in keywords:
        if " " in kw:
            if kw in text:
                return True
        else:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return True
    return False


def generate_scene_specification(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point for generating the validated declarative 3D scene specification.
    Returns a JSON-serializable dictionary.
    """
    domain = str(procedure.get("domain", "general")).lower().strip()
    exp_type = str(procedure.get("experiment_type", "")).lower().strip()
    hypothesis = str(procedure.get("hypothesis", "")).lower()
    topic = str(procedure.get("topic", "")).lower()
    combined_text = f"{domain} {exp_type} {hypothesis} {topic}"

    spec: SceneSpecification

    # 1. Physics domain routing
    if domain in ["physics", "physical"]:
        if any(w in combined_text for w in ["projectile", "trajectory", "cannon", "ballistic", "launch"]):
            spec = build_projectile_scene(procedure, numerical_results, plot_data)
        else:
            spec = build_pendulum_scene(procedure, numerical_results, plot_data)

    # 2. Civil Engineering domain routing
    elif domain in ["civil_engineering", "civil", "structural", "construction"]:
        spec = build_beam_deformation_scene(procedure, numerical_results, plot_data)

    # 3. Mechanical Engineering domain routing
    elif domain in ["mechanical_engineering", "mechanical", "mech"]:
        if any(w in combined_text for w in ["gear", "pinion", "teeth"]):
            spec = build_gear_train_scene(procedure, numerical_results, plot_data)
        else:
            spec = build_beam_deformation_scene(procedure, numerical_results, plot_data)

    # 4. Electronics domain routing
    elif domain in ["electronics", "circuit", "electrical", "arduino"]:
        spec = build_circuit_scene(procedure, numerical_results, plot_data)

    # 5. Computer Science domain routing
    elif domain in ["computer_science", "cs", "software", "algorithm", "machine_learning", "ml", "ai", "deep_learning"]:
        spec = build_cs_scene(procedure, numerical_results, plot_data)

    # 6. Chemistry domain routing
    elif domain in ["chemistry", "chemical", "molecular"]:
        spec = build_molecule_scene(procedure, numerical_results, plot_data)

    # 7. Unspecified / General domain heuristic fallback
    else:
        if _has_kw(combined_text, ["pendulum", "projectile", "motion", "gravity", "ballistic", "cannon", "kinematics"]):
            if any(w in combined_text for w in ["projectile", "trajectory", "cannon", "ballistic", "launch"]):
                spec = build_projectile_scene(procedure, numerical_results, plot_data)
            else:
                spec = build_pendulum_scene(procedure, numerical_results, plot_data)
        elif _has_kw(combined_text, ["neural", "cnn", "transformer", "vit", "resnet", "dropout", "sort", "sorting", "algorithm", "complexity", "dijkstra", "bfs", "dfs", "graph", "tree", "backpropagation", "loss function"]):
            spec = build_cs_scene(procedure, numerical_results, plot_data)
        elif _has_kw(combined_text, ["beam", "load", "deflect", "truss", "moment", "cantilever", "deflection", "bending stress"]):
            spec = build_beam_deformation_scene(procedure, numerical_results, plot_data)
        elif _has_kw(combined_text, ["gear", "spur", "shaft", "torque", "pinion", "rpm", "carnot", "otto cycle"]):
            spec = build_gear_train_scene(procedure, numerical_results, plot_data)
        elif _has_kw(combined_text, ["arduino", "led", "resistor", "breadboard", "voltage divider", "ohm's law", "circuit"]):
            spec = build_circuit_scene(procedure, numerical_results, plot_data)
        elif _has_kw(combined_text, ["molecule", "smiles", "titration", "reaction", "water", "methane", "benzene", "ethanol"]):
            spec = build_molecule_scene(procedure, numerical_results, plot_data)
        else:
            spec = build_generic_scene(procedure, numerical_results, plot_data)

    # Return validated dict
    return spec.model_dump()
