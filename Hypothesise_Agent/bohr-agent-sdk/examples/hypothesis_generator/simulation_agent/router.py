"""
Domain Router
Routes experiments to appropriate simulation engines
"""

from .engines import chem_sim, bio_sim, physics_sim, electronics_sim, cs_sim, civil_sim, mech_sim, llm_fallback

DOMAIN_MAP = {
    # Chemistry
    "chemistry":    chem_sim.run,
    "chemical":     chem_sim.run,
    "molecular":    chem_sim.run,
    "titration":    chem_sim.run,
    # Biology
    "biology":      bio_sim.run,
    "biological":   bio_sim.run,
    "genomics":     bio_sim.run,
    "protein":      bio_sim.run,
    "microbiology": bio_sim.run,
    # Physics
    "physics":      physics_sim.run,
    "physical":     physics_sim.run,
    # Civil Engineering
    "civil_engineering": civil_sim.run,
    "civil":        civil_sim.run,
    "structural":   civil_sim.run,
    "construction": civil_sim.run,
    "building":     civil_sim.run,
    "architecture": civil_sim.run,
    # Mechanical Engineering
    "mechanical_engineering": mech_sim.run,
    "mechanical":   mech_sim.run,
    "mech":         mech_sim.run,
    "gear":         mech_sim.run,
    "shaft":        mech_sim.run,
    "thermodynamic": mech_sim.run,
    # Electronics / circuits
    "electronics":  electronics_sim.run,
    "electrical":   electronics_sim.run,
    "engineering":  electronics_sim.run,
    "circuit":      electronics_sim.run,
    "arduino":      electronics_sim.run,
    # Computer Science / ML
    "computer_science": cs_sim.run,
    "cs":           cs_sim.run,
    "machine_learning": cs_sim.run,
    "ml":           cs_sim.run,
    "deep_learning": cs_sim.run,
    "artificial_intelligence": cs_sim.run,
    "ai":           cs_sim.run,
    "algorithm":    cs_sim.run,
}


def route(procedure: dict) -> dict:
    """
    Route experiment procedure to appropriate simulation engine.
    Falls back to LLM if deterministic engine fails.
    """
    domain = procedure.get("domain", "").lower().strip()
    engine_fn = DOMAIN_MAP.get(domain, llm_fallback.run)

    # Try deterministic engine first, fall back to LLM on failure
    if engine_fn is not llm_fallback.run:
        try:
            result = engine_fn(procedure)
            result["engine_used"] = engine_fn.__module__.split(".")[-1]
            result["status"] = "success"
            return result
        except Exception as e:
            print(f"⚠️  {engine_fn.__name__} failed: {e}. Falling back to LLM...")
            result = llm_fallback.run(procedure, error_context=str(e))
            result["engine_used"] = "llm_fallback"
            result["status"] = "fallback"
            return result
    else:
        result = llm_fallback.run(procedure)
        result["engine_used"] = "llm_fallback"
        result["status"] = "fallback"
        return result
