"""
Simulation Agent - Main Entry Point
====================================
Orchestrates the deterministic scientific simulation pipeline:
  parse -> classify (EXPERIMENT_REGISTRY) -> route -> simulate -> validate -> format
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional

from . import router
from .dynamic_sim import run_dynamic_simulation
from .experiment_registry import classify_experiment, get_experiment_entry
from .output_formatter import format_output
from .prompt_refiner import _heuristic_refinement, filter_and_compress_context
from .schema import ExperimentProcedure


def _has_kw(src: str, keywords: list) -> bool:
    """Match keywords with strict word boundaries to avoid substring false positives (e.g. 'controlled' matching 'led')."""
    for kw in keywords:
        if len(kw) <= 4 or " " not in kw:
            if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", src):
                return True
        else:
            if kw in src:
                return True
    return False


USER_DOMAIN_NORMALIZATION = {
    "cs": "computer_science",
    "comp sci": "computer_science",
    "comp_sci": "computer_science",
    "computer_science": "computer_science",
    "computer science": "computer_science",
    "civil": "civil_engineering",
    "civil eng": "civil_engineering",
    "civil_eng": "civil_engineering",
    "civil_engineering": "civil_engineering",
    "civil engineering": "civil_engineering",
    "structural": "civil_engineering",
    "mechanical": "mechanical_engineering",
    "mech": "mechanical_engineering",
    "mechanical_engineering": "mechanical_engineering",
    "mechanical engineering": "mechanical_engineering",
    "electronics": "electronics",
    "electrical": "electronics",
    "electrical_engineering": "electronics",
    "physics": "physics",
    "physical": "physics",
    "chemistry": "chemistry",
    "chemical": "chemistry",
    "biology": "biology",
    "bio": "biology",
    "biological": "biology",
    "biochemistry": "biology",
    "microbiology": "biology",
}


def normalize_domain_key(domain: str) -> str:
    """Normalize user or raw domain string to standard canonical domain."""
    d = str(domain or "").strip().lower()
    return USER_DOMAIN_NORMALIZATION.get(d, d)


def _classify_domain(src: str) -> str:
    """Word-boundary domain classifier across all 7 scientific & engineering domains."""
    # Check novel strain gauge / mechanical mechanisms first
    if _has_kw(src, [
        "strain gauge", "strain gauges", "wheatstone", "load cell", "piezoelectric",
        "four-bar", "four bar", "four_bar", "linkage", "crank", "rocker", "coupler",
        "spring-mass", "spring mass", "mass-spring", "viscous damper",
        "torsion", "torque", "spur gear", "gear", "gears", "pinion",
        "shaft", "shafts", "mechanical engineering", "otto cycle", "carnot",
        "diesel cycle", "brayton cycle", "thermodynamic cycle", "piston",
        "crankshaft", "connecting rod", "rotational dynamics", "flywheel",
        "vibration", "hooke",
    ]):
        return "mechanical_engineering"

    if _has_kw(src, [
        "civil", "structural", "beam", "beams", "cantilever", "simply supported",
        "truss", "trusses", "bridge", "slab", "udl", "uniformly distributed load",
        "bending moment", "shear force", "blueprint", "floor plan", "building design",
        "column load", "construction", "rcc", "reinforced concrete", "architecture",
    ]):
        return "civil_engineering"

    if _has_kw(src, [
        "arduino", "breadboard", "led", "leds", "blink", "resistor", "resistors",
        "capacitor", "capacitors", "inductor", "inductors", "transistor", "transistors",
        "diode", "diodes", "voltage divider", "current divider", "ohm's law", "ohms law",
        "microcontroller", "atmega", "esp32", "electronics", "soldering",
        "circuit board", "rlc circuit", "series rlc", "rc circuit", "rl circuit",
        "ac circuit", "step-up transformer", "step-down transformer", "turns ratio",
        "primary winding", "secondary winding", "electrical transformer", "kirchhoff", "op-amp",
    ]):
        return "electronics"

    if _has_kw(src, [
        "machine learning", "neural network", "cnn", "transformer", "vit", "resnet",
        "dropout", "deep learning", "training", "epoch", "epochs", "loss function",
        "classifier", "classifiers", "algorithm", "algorithms", "algorithm complexity",
        "sorting", "bubble sort", "selection sort", "insertion sort", "merge sort",
        "mergesort", "quick sort", "quicksort", "heap sort", "heapsort",
        "linear search", "binary search", "big-o", "convolutional", "computer science",
        "gradient descent", "backpropagation", "dijkstra", "shortest path", "bfs",
        "breadth-first", "breadth first", "dfs", "depth-first", "depth first",
        "topological sort", "connected components", "graph traversal", "tree traversal",
    ]):
        return "computer_science"

    if _has_kw(src, [
        "biology", "biological", "biochemistry", "microbiology", "enzyme", "enzymes",
        "michaelis", "menten", "michaelis-menten", "substrate", "lineweaver",
        "bacterial", "bacteria", "population growth", "logistic growth",
        "exponential growth", "carrying capacity", "doubling time", "cell culture",
        "bioreactor", "gene expression", "transcription", "translation", "mrna",
        "photosynthesis", "epidemic", "sir model",
    ]):
        return "biology"

    if _has_kw(src, [
        "chemical", "chemicals", "chemistry", "chemical reaction", "reaction kinetics",
        "reaction rate", "reactions", "arrhenius", "titration", "weak acid", "strong base",
        "pka", "equivalence point", "chemical equilibrium", "gibbs", "molecule",
        "molecules", "molecular", "smiles", "nickel", "chlorine", "chlorium",
        "chloride", "redox", "electrolysis", "acid", "acids", "alkali", "catalyst",
        "catalysts", "stoichiometry", "synthesis",
    ]):
        return "chemistry"

    if _has_kw(src, [
        "physics", "pendulum", "pendulums", "projectile", "projectiles", "ballistic",
        "trajectory", "kinematics", "optics", "oscillation", "oscillations",
        "doppler", "magnetic", "free fall",
    ]):
        return "physics"

    return "general"


def _extract_natural_parameters(design_text: str, topic: str, domain: str, params: Dict[str, Any]) -> None:
    """Extract physically typed parameters from design text & topic without overwriting explicit assignments."""
    combined = f"{topic or ''} {design_text or ''}"
    combined_low = combined.lower()

    # 1. Beam span (e.g. "5 m simply supported beam", "span 6 m", "L = 5 m")
    if "span_m" not in params:
        m_span = (
            re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?(?:m|meter|meters)\s+(?:long\s+)?(?:simply\s+supported|cantilever|steel|concrete|wooden|uniform)?\s*beam\b", combined_low)
            or re.search(r"\bspan\s*(?:length)?\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)\b", combined_low)
        )
        if m_span:
            params["span_m"] = float(m_span.group(1))

    # 2. UDL (e.g. "10 kN/m") vs Point Load (e.g. "10 kN")
    m_udl = re.search(r"(\d+(?:\.\d+)?)\s*kn\s*/\s*m\b", combined_low)
    if m_udl and "load_kN_per_m" not in params:
        params["load_kN_per_m"] = float(m_udl.group(1))

    m_pt = re.search(r"(\d+(?:\.\d+)?)\s*kn(?!\s*/\s*m)\b", combined_low)
    if m_pt and "point_load_kN" not in params:
        params["point_load_kN"] = float(m_pt.group(1))

    # 3. Elastic modulus E in GPa (only when explicitly stated!)
    m_e = re.search(r"(?:e\s*[:=]\s*|modulus[^\d]{0,15})(\d+(?:\.\d+)?)\s*gpa\b", combined_low)
    if m_e and "elastic_modulus_GPa" not in params:
        params["elastic_modulus_GPa"] = float(m_e.group(1))

    # 4. Moment of inertia I in m^4 (only when explicitly stated!)
    m_i = re.search(r"\bi\s*[:=]\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?\d+)?)\s*(?:m\^?4|m4)\b", combined_low)
    if m_i and "moment_of_inertia_m4" not in params:
        params["moment_of_inertia_m4"] = float(m_i.group(1))

    # 5. Electronics R, L, C, V with unit scaling
    if domain in ("electronics", "physics"):
        m_r = re.search(r"\br\s*[:=]\s*(\d+(?:\.\d+)?)\s*(k|m)?\s*(?:ohm|ohms|Ω)\b", combined, re.IGNORECASE)
        if m_r and "resistance_ohm" not in params:
            val = float(m_r.group(1))
            prefix = (m_r.group(2) or "").lower()
            if prefix == "k":
                val *= 1e3
            elif prefix == "m":
                val *= 1e6
            params["resistance_ohm"] = val

        m_l = re.search(r"\bl\s*[:=]\s*(\d+(?:\.\d+)?)\s*(m|u|µ)?h\b", combined, re.IGNORECASE)
        if m_l and "inductance_H" not in params:
            val = float(m_l.group(1))
            prefix = (m_l.group(2) or "").lower()
            if prefix == "m":
                val *= 1e-3
            elif prefix in ("u", "µ"):
                val *= 1e-6
            params["inductance_H"] = val

        m_c = re.search(r"\bc\s*[:=]\s*(\d+(?:\.\d+)?)\s*(m|u|µ|n|p)?f\b", combined, re.IGNORECASE)
        if m_c and "capacitance_F" not in params:
            val = float(m_c.group(1))
            prefix = (m_c.group(2) or "").lower()
            scale = {"m": 1e-3, "u": 1e-6, "µ": 1e-6, "n": 1e-9, "p": 1e-12}.get(prefix, 1.0)
            params["capacitance_F"] = val * scale

    # 6. Mechanical four-bar linkage link lengths (e.g. "crank 1m coupler 2.5m rocker 2m ground 3m")
    if domain == "mechanical_engineering":
        for key, pat in (
            ("crank_length_m", r"\bcrank(?:\s+length)?\s*(?:=|is|of|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?\b"),
            ("coupler_length_m", r"\bcoupler(?:\s+length)?\s*(?:=|is|of|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?\b"),
            ("rocker_length_m", r"\brocker(?:\s+length)?\s*(?:=|is|of|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?\b"),
            ("ground_length_m", r"\bground(?:\s+length|\s+link)?\s*(?:=|is|of|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?\b"),
        ):
            if key not in params:
                m = re.search(pat, combined_low)
                if m:
                    val = float(m.group(1))
                    unit = (m.group(2) or "m").lower()
                    if unit == "mm":
                        val *= 1e-3
                    elif unit == "cm":
                        val *= 1e-2
                    params[key] = val

    # 7. Pendulum length & release angle
    if domain == "physics":
        m_len = (
            re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?(?:m|meter|meters)\b", (topic or "").lower())
            or re.search(r"(?:length|string)[^\d]{0,20}(\d+(?:\.\d+)?)\s*(?:m|meter|meters)\b", combined_low)
        )
        if m_len and "length_m" not in params:
            val = float(m_len.group(1))
            if 0.05 <= val <= 50.0:
                params["length_m"] = val

        m_deg = re.search(r"(\d+(?:\.\d+)?)\s*(?:deg|degree|degrees|°)", combined_low)
        if m_deg:
            deg = float(m_deg.group(1))
            if "projectile" in combined_low or "trajectory" in combined_low or "launch" in combined_low:
                if "launch_angle_deg" not in params and 1.0 <= deg <= 89.0:
                    params["launch_angle_deg"] = deg
            elif "angle_deg" not in params and "angle_rad" not in params and 0.5 <= deg <= 175.0:
                params["angle_deg"] = deg
                params["angle_rad"] = round(math.radians(deg), 6)

        m_vel = re.search(r"(\d+(?:\.\d+)?)\s*(?:m/s|ms\^-1)\b", combined_low)
        if m_vel and "initial_velocity_ms" not in params:
            v = float(m_vel.group(1))
            if 0.5 <= v <= 1000.0:
                params["initial_velocity_ms"] = v


def extract_procedure_from_text(design_text: str, topic: str, user_domain: Optional[str] = None) -> dict:
    """
    Extract canonical domain, canonical registered `experiment_type`, hypothesis,
    steps, and physically normalized parameters from experimental design text.
    """
    procedure: Dict[str, Any] = {
        "domain": "general",
        "topic": topic,
        "hypothesis": "",
        "steps": [],
        "reagents": [],
        "parameters": {},
        "expected_metrics": [],
        "experiment_type": None,
    }

    text_lower = (design_text or "").lower()
    topic_lower = (topic or "").lower()
    combined = f"{text_lower} {topic_lower}"

    # 1. Domain detection (explicit user domain always wins)
    if user_domain:
        procedure["domain"] = normalize_domain_key(user_domain)
    else:
        detected = _classify_domain(topic_lower)
        if detected == "general":
            detected = _classify_domain(combined)
        procedure["domain"] = detected

    # 2. Extract hypothesis & methodology steps from Markdown
    lines = (design_text or "").split("\n")
    in_hypothesis = False
    in_methodology = False
    hypothesis_lines = []
    step_lines = []

    for line in lines:
        line_strip = line.strip()
        line_lower = line.lower()
        if "hypothesis" in line_lower and line_strip.startswith("#"):
            in_hypothesis = True
            in_methodology = False
            continue
        if "methodology" in line_lower or "procedure" in line_lower:
            in_hypothesis = False
            in_methodology = True
            continue
        if line_strip.startswith("#"):
            in_hypothesis = False
            in_methodology = False

        if in_hypothesis and line_strip and not line_strip.startswith("#"):
            hypothesis_lines.append(line_strip)
        if in_methodology and line_strip:
            if line_strip[0].isdigit() or line_strip.startswith("-") or line_strip.startswith("*"):
                step_lines.append(line_strip.lstrip("0123456789.-* "))

    procedure["hypothesis"] = " ".join(hypothesis_lines) if hypothesis_lines else (topic or "")
    procedure["steps"] = step_lines[:10]

    # 3. Extract explicit numeric variable assignments (e.g. "L = 5.0 m", "Vmax = 100")
    var_matches = re.findall(
        r"\b([A-Za-z][A-Za-z0-9_]{0,18})\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z/^°µμ%]+)?\b",
        f"{topic or ''}\n{design_text or ''}",
    )
    for var_name, var_val, unit in var_matches:
        vn_low = var_name.lower()
        if vn_low in ("epoch", "step", "fig", "table", "http", "https", "version"):
            continue
        try:
            val = float(var_val)
            u = (unit or "").lower()
            if u in ("gpa", "gn/m2"):
                procedure["parameters"]["elastic_modulus_GPa"] = val
                val_si = val * 1e9
            elif u in ("mpa", "mn/m2"):
                val_si = val * 1e6
            elif u in ("kpa", "kn/m2"):
                val_si = val * 1e3
            elif u in ("kn/m",):
                procedure["parameters"]["load_kN_per_m"] = val
                val_si = val
            elif u in ("kn", "kilonewtons"):
                procedure["parameters"]["point_load_kN"] = val
                val_si = val
            elif u in ("kohm", "kohms", "kω"):
                val_si = val * 1e3
            elif u in ("mohm", "mohms", "mω"):
                val_si = val * 1e6
            elif u in ("mh",):
                val_si = val * 1e-3
            elif u in ("uf", "µf"):
                val_si = val * 1e-6
            elif u in ("mf",):
                val_si = val * 1e-3
            elif u in ("mm", "millimeter"):
                val_si = val * 1e-3
            elif u in ("cm", "centimeter"):
                val_si = val * 1e-2
            else:
                val_si = val
            procedure["parameters"].setdefault(var_name, val_si)
        except Exception:
            continue

    # 4. Natural-language physical parameter extraction
    _extract_natural_parameters(design_text, topic, procedure["domain"], procedure["parameters"])

    # 5. Normalize shorthand aliases cleanly by domain
    p = procedure["parameters"]
    d = procedure["domain"]
    if "L" in p:
        if d == "civil_engineering":
            p.setdefault("span_m", p["L"])
        elif d == "electronics":
            p.setdefault("inductance_H", p["L"])
        elif d == "physics":
            p.setdefault("length_m", p["L"])
    if "span" in p:
        p.setdefault("span_m", p["span"])
    if "P" in p and d == "civil_engineering":
        p.setdefault("point_load_kN", p["P"])
    if "w" in p and d == "civil_engineering":
        p.setdefault("load_kN_per_m", p["w"] / 1000.0 if p["w"] > 500 else p["w"])
    if "E" in p and d in ("civil_engineering", "mechanical_engineering"):
        p.setdefault("elastic_modulus_GPa", p["E"] / 1e9 if p["E"] > 1e6 else p["E"])
    if "I" in p:
        if d in ("civil_engineering", "mechanical_engineering"):
            p.setdefault("moment_of_inertia_m4", p["I"])
        elif d == "biology":
            p.setdefault("inhibitor_conc", p["I"])
        elif d == "electronics":
            p.setdefault("current_A", p["I"])
    if "R" in p and d in ("electronics", "physics"):
        p.setdefault("resistance_ohm", p["R"])
    if "C" in p and d in ("electronics", "physics"):
        p.setdefault("capacitance_F", p["C"])
    if "V" in p and d in ("electronics", "physics"):
        p.setdefault("supply_voltage_V", p["V"])
    if "T" in p and d == "chemistry":
        p.setdefault("temperature_K", p["T"])
    if "r" in p and d == "biology":
        p.setdefault("growth_rate", p["r"])
    if "K" in p and d == "biology":
        p.setdefault("carrying_capacity", p["K"])

    # 6. Explicitly mark known novel/custom experiments that belong to dynamic_custom
    novel_custom_markers = [
        "strain gauge", "wheatstone", "load cell", "gauge factor",
        "nickel", "chlorine", "chlorium", "electrolysis", "haber", "combustion",
        "op-amp", "thermistor", "photodiode", "epidemic", "sir model", "photosynthesis",
    ]
    if _has_kw(combined, novel_custom_markers):
        procedure["experiment_type"] = "dynamic_custom"
    else:
        # 7. Canonical classification via EXPERIMENT_REGISTRY
        cls_domain, canonical_id, _ = classify_experiment(
            topic=topic or "",
            design_text=design_text or "",
            user_domain=user_domain or (d if d != "general" else None),
            explicit_experiment_type=None,
            parameters=procedure["parameters"],
        )
        if canonical_id:
            procedure["experiment_type"] = canonical_id
            # Sync domain to normalized long domain name if user didn't lock it
            if not user_domain:
                procedure["domain"] = normalize_domain_key(cls_domain)
        else:
            # Leave experiment_type=None so unsupported experiments return honest status="unsupported"
            procedure["experiment_type"] = None

    procedure["expected_metrics"] = [
        "quantitative measurements",
        "scientific validation checks",
        "reproducibility",
    ]
    return procedure


def run_simulation(design_output: dict) -> dict:
    """
    Main simulation pipeline entry point.
    Routes registered canonical experiments strictly to their deterministic domain engines,
    runs ScientificValidator on every output, and returns the validated v2 SimulationOutput dict.
    """
    design_text = design_output.get("design", "")
    topic = design_output.get("topic", "Unknown Experiment")
    user_domain = design_output.get("domain")
    refinement = design_output.get("refinement") or {}

    procedure_dict = extract_procedure_from_text(design_text, topic, user_domain=user_domain)
    if user_domain:
        procedure_dict["domain"] = normalize_domain_key(user_domain)

    # Allow explicit caller overrides passed directly on design_output (e.g. experiment_type, parameters)
    if design_output.get("experiment_type"):
        procedure_dict["experiment_type"] = str(design_output["experiment_type"]).strip().lower()
    if isinstance(design_output.get("parameters"), dict):
        procedure_dict["parameters"].update(design_output["parameters"])

    # Apply validated prompt-refiner overrides
    if isinstance(refinement, dict) and refinement:
        ref_domain = str(refinement.get("domain", "")).lower().strip()
        if procedure_dict.get("domain") == "general" and ref_domain and ref_domain != "general":
            procedure_dict["domain"] = normalize_domain_key(ref_domain)

        ref_type = refinement.get("experiment_type")
        if isinstance(ref_type, str) and ref_type.strip():
            refined_type = ref_type.strip().lower()
            # Resolve through registry if it's an alias
            _, resolved, _ = classify_experiment(
                topic=topic or "",
                design_text=design_text or "",
                user_domain=procedure_dict["domain"],
                explicit_experiment_type=refined_type,
                parameters=procedure_dict.get("parameters") or {},
            )
            procedure_dict["experiment_type"] = resolved or refined_type

        ref_params = refinement.get("parameters")
        if isinstance(ref_params, dict):
            params = procedure_dict.setdefault("parameters", {})
            for raw_k, raw_v in ref_params.items():
                key = str(raw_k).strip()
                if not key or raw_v is None or isinstance(raw_v, (bool, dict, list)):
                    continue
                val = raw_v
                if isinstance(val, str):
                    stripped = val.strip()
                    if not stripped:
                        continue
                    try:
                        val = float(stripped)
                    except ValueError:
                        lead = re.match(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", stripped)
                        val = float(lead.group(0)) if lead else stripped
                params[key] = val

    # Validate procedure schema (Pydantic v2)
    try:
        procedure = ExperimentProcedure(**procedure_dict)
        procedure_validated = procedure.model_dump()
    except Exception as exc:
        print(f"⚠️  Schema validation warning: {exc}")
        procedure_validated = procedure_dict

    exp_type = procedure_validated.get("experiment_type")
    entry = get_experiment_entry(exp_type) if exp_type else None

    # Build dynamic context for genuinely custom (non-registry) physics/chemistry problems
    effective_refinement = dict(refinement) if isinstance(refinement, dict) else {}
    if exp_type == "dynamic_custom" and not effective_refinement.get("equations"):
        h_ref = _heuristic_refinement(topic, filter_and_compress_context(topic, []))
        for k in ("equations", "independent_vars", "dependent_vars", "control_vars", "refined_objective"):
            if not effective_refinement.get(k) and h_ref.get(k):
                effective_refinement[k] = h_ref[k]

    dynamic_ctx = dict(procedure_validated)
    dynamic_ctx["topic"] = topic
    dynamic_ctx["refinement"] = effective_refinement

    # Route strictly:
    # 1. Registered canonical experiments -> deterministic domain engine via router.route()
    # 2. Explicit dynamic_custom -> dynamic sandboxed synthesis (returns honest unsupported if fails)
    # 3. Unrecognized / unsupported experiments -> router.route() -> honest status="unsupported" (no fabrication!)
    if entry is not None:
        try:
            raw_result = router.route(procedure_validated)
        except Exception as exc:
            raw_result = {
                "status": "failed",
                "simulation_status": "failed",
                "engine_used": entry.engine_module,
                "experiment_id": entry.experiment_id,
                "numerical_results": {},
                "plot_data": [],
                "observations": [f"Deterministic solver '{entry.experiment_id}' failed: {exc}"],
                "warnings": [str(exc)],
                "simulation_log": [f"[agent] Solver error: {exc}"],
            }
    elif exp_type == "dynamic_custom":
        raw_result = run_dynamic_simulation(dynamic_ctx)
        if raw_result.get("status") != "success":
            dyn_logs = list(raw_result.get("simulation_log") or [])
            dyn_err = "; ".join(raw_result.get("observations") or [])[:250]
            raw_result = router.llm_fallback.run(dynamic_ctx, error_context=dyn_err)
            raw_result["simulation_log"] = dyn_logs + list(raw_result.get("simulation_log") or [])
    else:
        raw_result = router.route(procedure_validated)

    # Attach token-filtering & prompt refinement audit trace when available
    if isinstance(refinement, dict) and refinement.get("token_filtering"):
        tf = refinement["token_filtering"]
        raw_result.setdefault("simulation_log", []).insert(
            0,
            f"[L1/L2_refinement] {refinement.get('refiner_source', 'qwen')}: "
            f"tokens {tf.get('raw_token_count', 0)}->{tf.get('filtered_token_count', 0)} "
            f"(-{tf.get('reduction_pct', 0)}% stop words removed)",
        )

    # Validate + Format into v2 SimulationOutput with synchronized 3D scene
    output = format_output(raw_result, procedure_validated)
    return output.model_dump()


def invoke(architect_output: dict) -> dict:
    """Entry point for pipeline / LangChain integration."""
    return run_simulation(architect_output)
