"""
Domain Router
Routes experiments to appropriate simulation engines
"""

from .engines import chem_sim, physics_sim, electronics_sim, cs_sim, civil_sim, mech_sim, llm_fallback

DOMAIN_MAP = {
    # Civil Engineering
    "civil_engineering": civil_sim.run,
    "civil":             civil_sim.run,
    "structural":        civil_sim.run,
    "construction":      civil_sim.run,
    "building":          civil_sim.run,
    "architecture":      civil_sim.run,
    # Mechanical Engineering
    "mechanical_engineering": mech_sim.run,
    "mechanical":        mech_sim.run,
    "mech":              mech_sim.run,
    "gear":              mech_sim.run,
    "shaft":             mech_sim.run,
    "thermodynamic":     mech_sim.run,
    # Computer Science / ML / Algorithms
    "computer_science":  cs_sim.run,
    "cs":                cs_sim.run,
    "machine_learning":  cs_sim.run,
    "ml":                cs_sim.run,
    "deep_learning":     cs_sim.run,
    "artificial_intelligence": cs_sim.run,
    "ai":                cs_sim.run,
    "algorithm":         cs_sim.run,
    "sorting":           cs_sim.run,
    "graph":             cs_sim.run,
    # Electronics / circuits
    "electronics":       electronics_sim.run,
    "electrical":        electronics_sim.run,
    "engineering":       electronics_sim.run,
    "circuit":           electronics_sim.run,
    "arduino":           electronics_sim.run,
    # Physics
    "physics":           physics_sim.run,
    "physical":          physics_sim.run,
    # Chemistry
    "chemistry":         chem_sim.run,
    "chemical":          chem_sim.run,
    "molecular":         chem_sim.run,
    "titration":         chem_sim.run,
}


def route(procedure: dict) -> dict:
    """
    Route experiment procedure to appropriate simulation engine.
    Falls back to LLM if deterministic engine fails.
    """
    domain = procedure.get("domain", "").lower().strip()
    sim_fn = DOMAIN_MAP.get(domain)

    if sim_fn:
        try:
            return sim_fn(procedure)
        except Exception as e:
            # Deterministic engine failed — fall back to LLM
            return llm_fallback.run(procedure, str(e))
    else:
        # Unknown domain — use LLM fallback
        return llm_fallback.run(procedure, f"Unknown domain: {domain}")
