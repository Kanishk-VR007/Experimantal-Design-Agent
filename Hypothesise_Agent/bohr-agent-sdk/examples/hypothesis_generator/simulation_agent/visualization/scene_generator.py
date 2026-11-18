"""
Scene Specification Generator (Registry-Synchronized)
=====================================================
Maps strictly from canonical `(domain, experiment_id) -> EXPERIMENT_REGISTRY[experiment_id].visualization_template -> builder`.
Never selects a 3D template by domain alone, and never returns a fabricated 3D scene
for an `unsupported` or `failed` simulation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..experiment_registry import classify_experiment, get_experiment_entry
from .scene_schema import SceneSpecification
from .templates.chemistry_templates import build_molecule_scene
from .templates.cs_templates import build_neural_net_scene
from .templates.domain_templates import (
    build_building_scene,
    build_enzyme_kinetics_scene,
    build_graph_traversal_scene,
    build_population_growth_scene,
    build_reaction_kinetics_scene,
    build_resistive_circuit_scene,
    build_rlc_circuit_scene,
    build_shaft_torsion_scene,
    build_sorting_array_scene,
    build_spring_mass_damper_scene,
    build_thermo_cycle_scene,
    build_titration_scene,
    build_truss_structure_scene,
)
from .templates.electronics_templates import build_circuit_scene
from .templates.generic_templates import build_generic_scene
from .templates.mech_civil_templates import (
    build_beam_deformation_scene,
    build_four_bar_linkage_scene,
    build_gear_train_scene,
)
from .templates.physics_templates import build_pendulum_scene, build_projectile_scene

TemplateBuilder = Callable[[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]], SceneSpecification]

TEMPLATE_BUILDERS: Dict[str, TemplateBuilder] = {
    # Physics
    "simple_pendulum": build_pendulum_scene,
    "projectile_motion": build_projectile_scene,
    # Civil
    "beam_deformation": build_beam_deformation_scene,
    "truss_structure": build_truss_structure_scene,
    "building_blueprint": build_building_scene,
    # Mechanical
    "four_bar_linkage": build_four_bar_linkage_scene,
    "gear_train": build_gear_train_scene,
    "shaft_torsion": build_shaft_torsion_scene,
    "spring_mass_damper": build_spring_mass_damper_scene,
    "thermo_cycle": build_thermo_cycle_scene,
    # Electronics
    "rlc_circuit": build_rlc_circuit_scene,
    "ohms_law_circuit": build_resistive_circuit_scene,
    "voltage_divider_circuit": build_resistive_circuit_scene,
    "arduino_circuit": build_circuit_scene,
    # Chemistry
    "titration_apparatus": build_titration_scene,
    "reaction_kinetics": build_reaction_kinetics_scene,
    "molecular_geometry": build_molecule_scene,
    # Biology
    "enzyme_kinetics": build_enzyme_kinetics_scene,
    "population_growth": build_population_growth_scene,
    # Computer Science
    "graph_traversal": build_graph_traversal_scene,
    "sorting_array": build_sorting_array_scene,
    "neural_network_3d": build_neural_net_scene,
}


def resolve_visualization_template(
    procedure: Dict[str, Any],
    numerical_results: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve `(canonical_experiment_id, visualization_template)` strictly via the registry.
    Never falls back to an unrelated domain template.
    """
    numerical_results = numerical_results or {}
    exp_id = str(
        procedure.get("experiment_id")
        or procedure.get("experiment_type")
        or numerical_results.get("experiment_id")
        or ""
    ).lower().strip()

    entry = get_experiment_entry(exp_id)
    if entry is None:
        domain = str(procedure.get("domain", "")).lower().strip()
        topic = str(procedure.get("topic", "") or procedure.get("hypothesis", ""))
        design_text = " ".join(
            str(procedure.get(k, ""))
            for k in ("experiment_id", "experiment_type", "hypothesis", "description")
        )
        _, resolved_id, _ = classify_experiment(
            topic=topic,
            design_text=design_text,
            user_domain=domain or None,
            explicit_experiment_type=exp_id or None,
            parameters=procedure.get("parameters") or {},
        )
        entry = get_experiment_entry(resolved_id) if resolved_id else None

    if entry is not None:
        return entry.experiment_id, entry.visualization_template

    return (exp_id or None), None


def generate_scene_specification(
    procedure: Dict[str, Any],
    numerical_results: Dict[str, Any],
    plot_data: List[Dict[str, Any]],
    *,
    simulation_status: Optional[str] = None,
    allow_illustrative: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Generate a validated declarative 3D scene specification strictly synchronized to
    the executed experiment and its numerical solver output.

    Returns `None` when the simulation is `unsupported` or `failed` (or has no matching
    registered template and `allow_illustrative` is False).
    """
    status = str(
        simulation_status
        or (numerical_results.get("simulation_status") if isinstance(numerical_results, dict) else "")
        or ""
    ).lower().strip()

    if status in ("unsupported", "failed"):
        return None

    exp_id, template_key = resolve_visualization_template(procedure, numerical_results)

    if template_key and template_key in TEMPLATE_BUILDERS:
        # Ensure procedure carries canonical experiment_type so template builders read exact metadata
        proc_view = dict(procedure)
        if exp_id:
            proc_view["experiment_type"] = exp_id
            proc_view["experiment_id"] = exp_id

        builder = TEMPLATE_BUILDERS[template_key]
        spec = builder(proc_view, numerical_results or {}, plot_data or [])
        spec.experiment_id = exp_id or spec.experiment_id
        spec.scene_template = template_key

        # Mark illustrative transparently if the underlying solver was parametric/illustrative
        if status == "illustrative":
            spec.is_simulation_backed = False
            if "Illustrative parametric model" not in " ".join(spec.notes):
                spec.notes.append("Illustrative parametric model — not trained on an external dataset.")
        return spec.model_dump()

    if allow_illustrative:
        spec = build_generic_scene(procedure, numerical_results or {}, plot_data or [])
        spec.is_simulation_backed = False
        if exp_id:
            spec.experiment_id = exp_id
        return spec.model_dump()

    return None
