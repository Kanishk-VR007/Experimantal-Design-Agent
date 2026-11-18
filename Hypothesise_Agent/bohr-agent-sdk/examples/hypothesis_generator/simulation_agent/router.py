"""
Central Experiment-Aware Scientific Router
===========================================
Routes strictly by `(canonical_domain, experiment_id) -> registered deterministic solver`.
Fixes legacy defects:
  - Registers `bio_sim` explicitly (biology routing bug fixed).
  - Never falls back to an unrelated engine or fabricated sine-wave data.
  - Validates experiment identity and required parameters against `EXPERIMENT_REGISTRY`.
  - Returns honest `unsupported` or `failed` status when no verified solver applies.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .engines import (
    bio_sim,
    chem_sim,
    civil_sim,
    cs_sim,
    electronics_sim,
    llm_fallback,
    mech_sim,
    physics_sim,
)
from .experiment_registry import (
    EXPERIMENT_REGISTRY,
    classify_experiment,
    get_experiment_entry,
    list_experiments_by_domain,
)
from .experiment_schema import CanonicalExperimentSpec, normalize_canonical_domain

ENGINE_MODULES: Dict[str, Callable[[dict], dict]] = {
    "civil_sim": civil_sim.run,
    "mech_sim": mech_sim.run,
    "physics_sim": physics_sim.run,
    "electronics_sim": electronics_sim.run,
    "chem_sim": chem_sim.run,
    "bio_sim": bio_sim.run,
    "cs_sim": cs_sim.run,
}

# Explicit domain map (includes biology!) for compatibility & introspection
DOMAIN_MAP: Dict[str, Callable[[dict], dict]] = {
    # Civil Engineering
    "civil_engineering": civil_sim.run,
    "civil": civil_sim.run,
    "structural": civil_sim.run,
    "construction": civil_sim.run,
    "building": civil_sim.run,
    "architecture": civil_sim.run,
    # Mechanical Engineering
    "mechanical_engineering": mech_sim.run,
    "mechanical": mech_sim.run,
    "mech": mech_sim.run,
    "gear": mech_sim.run,
    "shaft": mech_sim.run,
    "thermodynamic": mech_sim.run,
    # Computer Science / Algorithms / ML
    "computer_science": cs_sim.run,
    "cs": cs_sim.run,
    "machine_learning": cs_sim.run,
    "ml": cs_sim.run,
    "deep_learning": cs_sim.run,
    "artificial_intelligence": cs_sim.run,
    "ai": cs_sim.run,
    "algorithm": cs_sim.run,
    "sorting": cs_sim.run,
    "graph": cs_sim.run,
    # Electronics / Electrical
    "electronics": electronics_sim.run,
    "electrical": electronics_sim.run,
    "engineering": electronics_sim.run,
    "circuit": electronics_sim.run,
    "arduino": electronics_sim.run,
    # Physics
    "physics": physics_sim.run,
    "physical": physics_sim.run,
    # Chemistry
    "chemistry": chem_sim.run,
    "chemical": chem_sim.run,
    "molecular": chem_sim.run,
    "titration": chem_sim.run,
    # Biology (Explicitly registered!)
    "biology": bio_sim.run,
    "biological": bio_sim.run,
    "bio": bio_sim.run,
    "life_science": bio_sim.run,
    "biochemistry": bio_sim.run,
}


def route(procedure: dict) -> dict:
    """
    Route a validated or raw experiment procedure to its exact registered solver.
    1. Resolve canonical domain + exact experiment_id via EXPERIMENT_REGISTRY.
    2. Validate required parameters against registry constraints.
    3. Execute the exact registered deterministic engine.
    4. If unsupported or failed, return an honest status without fabricated data.
    """
    proc = dict(procedure or {})
    raw_domain = str(proc.get("domain", "") or "").strip()
    raw_exp_type = str(proc.get("experiment_type") or "").strip()
    topic = str(proc.get("topic") or "")
    hypothesis = str(proc.get("hypothesis") or "")
    params = dict(proc.get("parameters") or {})
    units = dict(proc.get("units") or {})

    # 1. Exact registry classification
    canon_domain, experiment_id, reason = classify_experiment(
        topic=topic,
        design_text=hypothesis,
        user_domain=raw_domain if raw_domain and raw_domain.lower() != "general" else None,
        explicit_experiment_type=raw_exp_type or None,
        parameters=params,
    )

    if not experiment_id:
        supported = [e.experiment_id for e in list_experiments_by_domain(canon_domain)]
        return llm_fallback.build_unsupported_response(
            proc,
            reason=reason,
            supported_examples=supported,
        )

    entry = get_experiment_entry(experiment_id)
    if not entry:
        return llm_fallback.build_unsupported_response(
            proc,
            reason=f"Experiment '{experiment_id}' is not present in EXPERIMENT_REGISTRY.",
        )

    # 2. Canonical schema parameter resolution & missing-parameter check
    spec = CanonicalExperimentSpec(
        experiment_id=entry.experiment_id,
        domain=entry.domain,
        experiment_type=entry.experiment_id,
        description=hypothesis or topic,
        parameters=params,
        units=units,
    )
    resolved_params, missing_required, param_errors, param_warnings = spec.resolve_parameters(
        entry.parameter_constraints,
        allow_documented_defaults=True,
    )

    if missing_required:
        return llm_fallback.build_failed_response(
            {**proc, "domain": entry.domain, "experiment_type": entry.experiment_id},
            f"Missing required parameter(s) for '{entry.experiment_id}': {', '.join(missing_required)}.",
        )
    if param_errors:
        return llm_fallback.build_failed_response(
            {**proc, "domain": entry.domain, "experiment_type": entry.experiment_id},
            f"Parameter validation failed for '{entry.experiment_id}': {'; '.join(param_errors)}",
        )

    # 3. Dispatch to exact registered deterministic engine
    engine_fn = ENGINE_MODULES.get(entry.engine_module)
    if engine_fn is None:
        return llm_fallback.build_unsupported_response(
            proc,
            reason=f"Engine module '{entry.engine_module}' is not registered.",
        )

    routed_proc = dict(proc)
    routed_proc["domain"] = entry.domain
    routed_proc["experiment_type"] = entry.experiment_id
    routed_proc["experiment_id"] = entry.experiment_id
    routed_proc["parameters"] = resolved_params

    try:
        result = engine_fn(routed_proc)
    except Exception as exc:
        return llm_fallback.build_failed_response(routed_proc, f"Solver '{entry.solver}' raised {type(exc).__name__}: {exc}")

    # Annotate canonical experiment_id, domain, and any parameter warnings
    result.setdefault("experiment_id", entry.experiment_id)
    result.setdefault("domain", entry.domain)
    result.setdefault("engine_used", entry.engine_module)
    if param_warnings:
        result.setdefault("warnings", [])
        for w in param_warnings:
            if w not in result["warnings"]:
                result["warnings"].append(w)

    return result
