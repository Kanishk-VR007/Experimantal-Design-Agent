"""
Simulation Agent - Main Entry Point
Orchestrates simulation pipeline: parse → route → simulate → format
"""

import re
import json
from . import router
from .output_formatter import format_output
from .schema import ExperimentProcedure, SimulationOutput
from .dynamic_sim import run_dynamic_simulation
from .prompt_refiner import filter_and_compress_context, _heuristic_refinement


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
    "civil": "civil_engineering",
    "civil eng": "civil_engineering",
    "civil_eng": "civil_engineering",
    "civil_engineering": "civil_engineering",
    "mechanical": "mechanical_engineering",
    "mech": "mechanical_engineering",
    "mechanical_engineering": "mechanical_engineering",
    "electronics": "electronics",
    "electrical": "electronics",
    "physics": "physics",
    "chemistry": "chemistry",
}


def normalize_domain_key(domain: str) -> str:
    """Normalize user or raw domain string to standard canonical domain."""
    d = str(domain or "").strip().lower()
    return USER_DOMAIN_NORMALIZATION.get(d, d)


def extract_procedure_from_text(design_text: str, topic: str, user_domain: str = None) -> dict:
    """
    Intelligently extract simulation parameters from experimental design output.
    Uses word-boundary domain classification and assigns 'dynamic_custom' for
    novel experiments outside built-in fixed solver templates.
    If user_domain is provided, it explicitly overrides keyword heuristics to prevent hallucination.
    """

    # Default procedure structure
    procedure = {
        "domain": "general",
        "topic": topic,
        "hypothesis": "",
        "steps": [],
        "reagents": [],
        "parameters": {},
        "expected_metrics": [],
        "experiment_type": None
    }

    # Text extraction normalized strings
    text_lower = (design_text or "").lower()
    topic_lower = (topic or "").lower()
    combined = text_lower + " " + topic_lower

    # Detect domain: prioritize explicit user domain first
    if user_domain:
        procedure["domain"] = normalize_domain_key(user_domain)
    else:
        def _classify_domain(src: str) -> str:
            if _has_kw(src, [
                "strain gauge", "strain gauges", "wheatstone", "load cell", "piezoelectric",
                "cantilever", "torsion", "torque", "spur gear", "gear", "gears", "pinion",
                "shaft", "shafts", "mechanical engineering", "otto cycle", "carnot",
                "thermodynamic cycle", "piston", "crankshaft", "connecting rod",
                "vibration", "hooke", "stress", "strain",
            ]):
                return "mechanical_engineering"
            if _has_kw(src, [
                "arduino", "breadboard", "led", "leds", "blink", "resistor", "resistors",
                "capacitor", "capacitors", "transistor", "transistors", "diode", "diodes",
                "voltage divider", "microcontroller", "atmega", "esp32",
                "electronics", "soldering", "circuit board", "rlc circuit", "rc circuit",
                "op-amp", "wheatstone bridge",
            ]):
                return "electronics"
            if _has_kw(src, [
                "machine learning", "neural network", "cnn", "transformer", "dropout",
                "deep learning", "training", "epoch", "epochs", "loss function", "classifier",
                "classifiers", "algorithm", "algorithms", "algorithm complexity", "sorting",
                "big-o", "convolutional", "computer science", "gradient descent", "backpropagation",
                "dijkstra", "shortest path", "bfs", "dfs", "graph traversal", "tree traversal",
            ]):
                return "computer_science"
            if _has_kw(src, [
                "civil", "structural", "beam", "beams", "truss", "trusses", "bridge", "slab",
                "blueprint", "floor plan", "building design", "column load",
                "construction", "rcc", "reinforced concrete", "architecture",
            ]):
                return "civil_engineering"
            if _has_kw(src, [
                "physics", "pendulum", "pendulums", "projectile", "projectiles",
                "kinematics", "optics", "oscillation", "oscillations", "doppler",
                "thermodynamics", "magnetic",
            ]):
                return "physics"
            if _has_kw(src, [
                "chemical", "chemicals", "chemistry", "chemical reaction", "reaction kinetics",
                "reaction rate", "reactions", "arrhenius", "titration", "molecule", "molecules",
                "molecular", "smiles", "nickel", "chlorine", "chlorium", "chloride", "redox",
                "electrolysis", "acid", "acids", "alkali", "catalyst", "catalysts",
                "stoichiometry", "synthesis",
            ]):
                return "chemistry"
            return "general"

        detected_domain = _classify_domain(topic_lower)
        if detected_domain == "general":
            detected_domain = _classify_domain(combined)
        procedure["domain"] = detected_domain
    
    # Extract hypothesis (look for ## HYPOTHESIS or ## 1. HYPOTHESIS sections)
    lines = design_text.split('\n')
    in_hypothesis = False
    in_methodology = False
    hypothesis_lines = []
    step_lines = []
    
    for line in lines:
        line_strip = line.strip()
        line_lower = line.lower()  # Define line_lower here
        
        # Detect sections
        if "hypothesis" in line_lower and line_strip.startswith("#"):
            in_hypothesis = True
            in_methodology = False
            continue
        elif "methodology" in line_lower or "procedure" in line_lower:
            in_hypothesis = False
            in_methodology = True
            continue
        elif line_strip.startswith("#"):
            in_hypothesis = False
            in_methodology = False
        
        # Collect hypothesis
        if in_hypothesis and line_strip and not line_strip.startswith("#"):
            hypothesis_lines.append(line_strip)
        
        # Collect methodology steps
        if in_methodology and line_strip:
            if line_strip[0].isdigit() or line_strip.startswith("-") or line_strip.startswith("*"):
                step_lines.append(line_strip.lstrip("0123456789.-* "))
    
    procedure["hypothesis"] = " ".join(hypothesis_lines) if hypothesis_lines else topic
    procedure["steps"] = step_lines[:10]  # Limit to 10 steps
    
    # Extract explicit numeric variable assignments from design text (e.g. "w = 5000", "L = 3.0", "E = 200 GPa")
    var_matches = re.findall(r"\b([A-Za-z][A-Za-z0-9_]{0,15})\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z/^°µμ%]+)?\b", design_text)
    for var_name, var_val, unit in var_matches:
        if var_name.lower() not in ("epoch", "step", "fig", "table", "http", "https"):
            try:
                val = float(var_val)
                if unit:
                    u = unit.lower()
                    if u in ("gpa", "gn/m2"): val *= 1e9
                    elif u in ("mpa", "mn/m2"): val *= 1e6
                    elif u in ("kpa", "kn/m2"): val *= 1e3
                    elif u in ("kn", "kilonewtons"): val *= 1e3
                    elif u in ("kohm", "kohms", "kω"): val *= 1e3
                    elif u in ("mohm", "mohms", "mω"): val *= 1e6
                    elif u in ("um", "µm", "micromolar", "microns"): val *= 1e-6
                    elif u in ("mm", "millimeter"): val *= 1e-3
                    elif u in ("cm", "centimeter"): val *= 1e-2
                procedure["parameters"][var_name] = val
            except Exception:
                continue

    # Normalization helper: map physical shorthand aliases into canonical domain keys
    def _normalize_extracted_params(proc: dict):
        p = proc["parameters"]
        d = proc.get("domain", "")
        if "L" in p and "span_m" not in p: p["span_m"] = p["L"]
        if "span_m" in p and "L" not in p: p["L"] = p["span_m"]
        if "w" in p:
            if "load_kN_per_m" not in p: p["load_kN_per_m"] = p["w"] / 1000.0 if p["w"] > 50 else p["w"]
            if "load_N_per_m" not in p: p["load_N_per_m"] = p["w"] if p["w"] > 50 else p["w"] * 1000.0
        if "E" in p:
            if "elastic_modulus_GPa" not in p: p["elastic_modulus_GPa"] = p["E"] / 1e9 if p["E"] > 1e6 else p["E"]
            if "elastic_modulus_Pa" not in p: p["elastic_modulus_Pa"] = p["E"] if p["E"] > 1e6 else p["E"] * 1e9
        if "I" in p:
            if d in ("civil_engineering", "mechanical_engineering"):
                if "moment_of_inertia_m4" not in p: p["moment_of_inertia_m4"] = p["I"]
            elif d in ("biology", "chemistry"):
                if "inhibitor_conc" not in p: p["inhibitor_conc"] = p["I"]
            elif d in ("electronics", "physics"):
                if "current_A" not in p: p["current_A"] = p["I"]
        if "R" in p and "resistance_ohm" not in p: p["resistance_ohm"] = p["R"]
        if "resistance_ohm" in p and "R" not in p: p["R"] = p["resistance_ohm"]
        if "T" in p and "temperature_K" not in p: p["temperature_K"] = p["T"]
        if "V" in p and "supply_voltage_V" not in p: p["supply_voltage_V"] = p["V"]
        if "Ki" in p and "inhibition_constant" not in p: p["inhibition_constant"] = p["Ki"]
        if "Km" in p and "michaelis_constant" not in p: p["michaelis_constant"] = p["Km"]
        if "Vmax" in p and "max_velocity" not in p: p["max_velocity"] = p["Vmax"]

    def _merge_param_defaults(proc: dict, defaults: dict):
        for k, v in defaults.items():
            if k not in proc["parameters"]:
                proc["parameters"][k] = v

    _normalize_extracted_params(procedure)

    # Set domain-specific sub-type ONLY when topic/design clearly matches a built-in model;
    # otherwise route to 'dynamic_custom' so bespoke NumPy/SciPy simulation code & 2D plots are generated.
    if procedure["domain"] == "electronics":
        if _has_kw(combined, ["ohm", "resistor", "i-v", "current vs voltage", "conductance"]):
            procedure["experiment_type"] = "ohms_law"
            _merge_param_defaults(procedure, {"resistance_ohm": 1000.0, "voltage_min": 0.0, "voltage_max": 10.0, "supply_voltage_V": 10.0})
        elif _has_kw(combined, ["strain gauge", "wheatstone", "rc circuit", "capacitor", "op-amp", "thermistor", "photodiode"]):
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {"supply_voltage_V": 5.0})
        elif _has_kw(combined, ["arduino", "blink", "microcontroller", "atmega"]):
            procedure["experiment_type"] = "arduino_led"
            _merge_param_defaults(procedure, {"supply_voltage_V": 5.0, "led_forward_voltage_V": 2.0, "led_current_mA": 20, "blink_frequency_Hz": 1.0})
        elif _has_kw(combined, ["voltage divider"]):
            procedure["experiment_type"] = "voltage_divider"
            _merge_param_defaults(procedure, {"r1_ohm": 1000.0, "r2_ohm": 1000.0, "supply_voltage_V": 5.0})
        elif _has_kw(combined, ["rlc", "inductor", "resonance", "resonant"]):
            procedure["experiment_type"] = "rlc_circuit"
            _merge_param_defaults(procedure, {"resistance_ohm": 10.0, "inductance_H": 0.1, "capacitance_F": 0.001, "voltage_V": 5.0})
        elif _has_kw(combined, ["led", "diode"]):
            procedure["experiment_type"] = "led_resistor"
            _merge_param_defaults(procedure, {"supply_voltage_V": 5.0, "resistance_ohm": 220.0, "led_vf": 2.0})
        else:
            procedure["experiment_type"] = "ohms_law" if any(w in combined for w in ["resis", "volt", "curr"]) else "dynamic_custom"
            _merge_param_defaults(procedure, {"supply_voltage_V": 5.0, "resistance_ohm": 1000.0})

    elif procedure["domain"] == "computer_science":
        if _has_kw(combined, ["cnn", "transformer", "vit", "resnet"]):
            procedure["experiment_type"] = "model_comparison"
        elif _has_kw(combined, ["dropout", "regularization", "regularize"]):
            procedure["experiment_type"] = "dropout_effect"
        elif _has_kw(combined, ["algorithm", "complexity", "sort", "search", "big-o"]):
            procedure["experiment_type"] = "algorithm_complexity"
        elif _has_kw(combined, ["neural network", "training", "epoch"]):
            procedure["experiment_type"] = "neural_network"
        else:
            procedure["experiment_type"] = "dynamic_custom"
        _merge_param_defaults(procedure, {"epochs": 50})

    elif procedure["domain"] == "chemistry":
        _merge_param_defaults(procedure, {
            "temperature_K": 298.15,
            "reaction_time_s": 120,
            "initial_concentration_M": 1.0,
            "activation_energy_kJ": 50,
            "pre_exponential_factor": 1e10
        })
        if _has_kw(combined, ["titration", "pka", "equivalence point"]):
            procedure["experiment_type"] = "titration"
            _merge_param_defaults(procedure, {"pKa": 4.74})
        elif _has_kw(combined, ["arrhenius", "first-order", "reaction kinetics", "concentration"]):
            procedure["experiment_type"] = "kinetics"
        elif _has_kw(combined, ["nickel", "chlorine", "chlorium", "electrolysis", "synthesis", "redox", "haber", "combustion", "reacted", "react"]):
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {
                "temperature_K": 323.15,
                "reaction_time_s": 120,
                "initial_concentration_M": 1.0,
                "activation_energy_kJ": 65.0,
                "pre_exponential_factor": 1e9,
            })
        else:
            procedure["experiment_type"] = "kinetics"
    
    elif procedure["domain"] == "biology":
        if _has_kw(combined, ["gene expression", "transcription", "translation", "mrna"]):
            procedure["experiment_type"] = "gene_expression"
            _merge_param_defaults(procedure, {"transcription_rate": 0.8, "translation_rate": 0.5, "initial_population": 100, "carrying_capacity": 1e6, "growth_rate": 0.5, "time_hours": 24})
        elif _has_kw(combined, ["enzyme", "michaelis", "menten", "allosteric", "substrate", "cataly", "lineweaver", "ki", "km", "vmax"]):
            procedure["experiment_type"] = "enzyme_kinetics"
            _merge_param_defaults(procedure, {
                "Vmax": 100.0, "Km": 5.0, "Ki": 2.5, "I": 2.5,
                "substrate_min": 0.5, "substrate_max": 50.0,
            })
        elif _has_kw(combined, ["epidemic", "sir", "action potential", "photosynthesis"]):
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {"initial_population": 100, "carrying_capacity": 1e6, "growth_rate": 0.5, "time_hours": 24})
        else:
            procedure["experiment_type"] = "growth_curve"
            _merge_param_defaults(procedure, {
                "initial_population": 100,
                "carrying_capacity": 1e6,
                "growth_rate": 0.5,
                "time_hours": 24
            })

    elif procedure["domain"] == "civil_engineering":
        if _has_kw(combined, ["strain gauge", "wheatstone"]):
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {"span_m": 1.0, "gauge_factor": 2.1, "excitation_V": 5.0})
        elif _has_kw(combined, ["cantilever", "fixed-free", "fixed beam"]):
            procedure["experiment_type"] = "cantilever_beam"
            _merge_param_defaults(procedure, {
                "span_m": 3.0, "load_kN_per_m": 5.0,
                "elastic_modulus_GPa": 200.0,
                "moment_of_inertia_m4": 8.333e-6,
                "beam_width_mm": 300, "beam_depth_mm": 500,
            })
        elif _has_kw(combined, ["beam", "beams", "deflect", "deflection", "slab"]):
            procedure["experiment_type"] = "beam_analysis"
            _merge_param_defaults(procedure, {
                "span_m": 6.0, "load_kN_per_m": 10.0,
                "elastic_modulus_GPa": 200.0,
                "moment_of_inertia_m4": 8.33e-6,
                "beam_width_mm": 300, "beam_depth_mm": 500,
            })
        elif _has_kw(combined, ["truss", "bridge", "roof"]):
            procedure["experiment_type"] = "truss_analysis"
            _merge_param_defaults(procedure, {
                "span_m": 10.0, "height_m": 3.0,
                "panels": 4, "point_load_kN": 20.0,
            })
        elif _has_kw(combined, ["blueprint", "floor plan", "building", "house"]):
            procedure["experiment_type"] = "building_blueprint"
            _merge_param_defaults(procedure, {
                "floors": 2, "width_m": 12.0, "depth_m": 8.0,
                "floor_height_m": 3.0, "wall_thickness_mm": 230,
                "column_size_mm": 300, "rooms_per_floor": 4,
            })
        else:
            procedure["experiment_type"] = "dynamic_custom"

    elif procedure["domain"] == "mechanical_engineering":
        if _has_kw(combined, ["strain gauge", "wheatstone", "load cell", "gauge factor"]):
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {
                "gauge_factor": 2.1, "nominal_resistance_ohm": 120.0,
                "excitation_voltage_V": 5.0, "elastic_modulus_GPa": 200.0,
            })
        elif _has_kw(combined, ["gear", "spur gear", "pinion", "teeth"]):
            procedure["experiment_type"] = "gear_train"
            _merge_param_defaults(procedure, {
                "teeth_driver": 20, "teeth_driven": 40,
                "module_mm": 2.5, "rpm_input": 1500,
                "power_kW": 5.0, "pressure_angle_deg": 20,
                "face_width_mm": 25,
            })
        elif _has_kw(combined, ["shaft", "torsion", "torque", "twist"]):
            procedure["experiment_type"] = "shaft_design"
            _merge_param_defaults(procedure, {
                "torque_Nm": 200, "bending_moment_Nm": 150,
                "length_mm": 500, "diameter_mm": 40,
                "material": "AISI 1045 Steel",
            })
        elif _has_kw(combined, ["otto", "carnot", "thermodynamic cycle", "thermo cycle"]):
            procedure["experiment_type"] = "thermo_cycle"
            _merge_param_defaults(procedure, {
                "cycle": "otto", "T_hot_K": 1200, "T_cold_K": 300,
                "compression_ratio": 8, "gamma": 1.4,
                "P1_kPa": 101.325, "V1_L": 0.5,
            })
        else:
            procedure["experiment_type"] = "dynamic_custom"
            _merge_param_defaults(procedure, {"span_m": 1.0, "load_N": 100.0})
    
    elif procedure["domain"] == "physics":
        _merge_param_defaults(procedure, {
            "gravity": 9.81,
            "length_m": 1.0,
            "damping": 0.1,
            "angle_rad": 0.5
        })
        if _has_kw(combined, ["projectile", "trajectory", "ballistic"]):
            procedure["experiment_type"] = "projectile"
            _merge_param_defaults(procedure, {
                "initial_velocity_ms": 20,
                "launch_angle_deg": 45,
                "gravity": 9.81
            })
        elif _has_kw(combined, ["rlc"]):
            procedure["experiment_type"] = "rlc_circuit"
            _merge_param_defaults(procedure, {
                "resistance_ohm": 10,
                "inductance_H": 0.1,
                "capacitance_F": 0.001,
                "voltage_V": 5.0
            })
        elif _has_kw(combined, ["pendulum"]):
            procedure["experiment_type"] = "pendulum"
            m_len = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?(?:m|meter|meters)\b", topic_lower) or re.search(
                r"(?:length|string)[^\d]{0,20}(\d+(?:\.\d+)?)\s*(?:m|meter|meters)\b", combined
            )
            if m_len:
                val = float(m_len.group(1))
                if 0.2 <= val <= 5.0:
                    procedure["parameters"]["length_m"] = val
            m_deg = re.search(r"(\d+(?:\.\d+)?)\s*(?:deg|degree|degrees|°)", topic_lower)
            if m_deg:
                deg = float(m_deg.group(1))
                if 1.0 <= deg <= 75.0:
                    procedure["parameters"]["angle_rad"] = round(deg * 3.14159265 / 180.0, 3)
        else:
            procedure["experiment_type"] = "dynamic_custom"

        if procedure["experiment_type"] == "projectile":
            m_vel = re.search(r"(\d+(?:\.\d+)?)\s*(?:m/s|ms)", combined)
            if m_vel:
                v = float(m_vel.group(1))
                if 2.0 <= v <= 100.0:
                    procedure["parameters"]["initial_velocity_ms"] = v
            m_ang = re.search(r"(\d+(?:\.\d+)?)\s*(?:deg|degree|degrees|°)", topic_lower)
            if m_ang:
                ang = float(m_ang.group(1))
                if 5.0 <= ang <= 85.0:
                    procedure["parameters"]["launch_angle_deg"] = ang
    
    procedure["expected_metrics"] = [
        "quantitative measurements",
        "statistical significance",
        "reproducibility"
    ]
    
    return procedure


def run_simulation(design_output: dict) -> dict:
    """
    Main simulation function.
    
    Input: Output from Ollama's experimental design (text-based)
    Output: SimulationOutput with plots and numerical results
    """
    
    # Extract procedure from design text
    design_text = design_output.get("design", "")
    topic = design_output.get("topic", "Unknown Experiment")
    user_domain = design_output.get("domain")
    refinement = design_output.get("refinement") or {}

    procedure_dict = extract_procedure_from_text(design_text, topic, user_domain=user_domain)
    if user_domain:
        procedure_dict["domain"] = normalize_domain_key(user_domain)

    # Incorporate validated refinement hints. Refined values from the Qwen prompt
    # refiner are AUTHORITATIVE: they override deterministic extracted defaults and
    # supply keys the text parser could not recover.
    if isinstance(refinement, dict) and refinement:
        ref_domain = str(refinement.get("domain", "")).lower().strip()
        if procedure_dict.get("domain") == "general" and ref_domain and ref_domain != "general":
            procedure_dict["domain"] = ref_domain

        # Refined experiment_type supersedes keyword-based classification
        ref_type = refinement.get("experiment_type")
        if isinstance(ref_type, str) and ref_type.strip():
            refined_type = ref_type.strip().lower()
            previous_type = procedure_dict.get("experiment_type")
            if previous_type != refined_type:
                print(
                    f"🔧 Refined experiment_type override: "
                    f"{previous_type} -> {refined_type}"
                )
                procedure_dict["experiment_type"] = refined_type

        ref_params = refinement.get("parameters")
        if isinstance(ref_params, dict):
            params = procedure_dict.setdefault("parameters", {})
            overrides = []
            added = []
            rejected = []
            for raw_k, raw_v in ref_params.items():
                key = str(raw_k).strip()
                if not key:
                    continue
                value = raw_v
                # Coerce numeric strings ("0.5" / "0.5 m") emitted by the refiner
                if isinstance(value, str):
                    stripped = value.strip()
                    if not stripped:
                        rejected.append(key)
                        continue
                    try:
                        value = float(stripped)
                    except ValueError:
                        lead = re.match(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", stripped)
                        value = float(lead.group(0)) if lead else stripped
                elif isinstance(value, bool) or value is None:
                    rejected.append(key)
                    continue
                elif isinstance(value, (dict, list)):
                    rejected.append(key)
                    continue

                if key in params:
                    old_value = params[key]
                    if old_value != value:
                        overrides.append(f"{key} {old_value} -> {value}")
                        params[key] = value
                else:
                    added.append(f"{key}={value}")
                    params[key] = value

            # Keep refined values for missing keys even when they are non-numeric
            if overrides:
                print(
                    "🔧 Refined parameters applied (override): "
                    + "; ".join(overrides)
                )
            if added:
                print(
                    "🔧 Refined parameters applied (new keys): "
                    + "; ".join(added)
                )
            if rejected:
                print(
                    "⚠️  Refined parameters skipped (non-scalar/empty): "
                    + "; ".join(rejected)
                )
    
    # Validate schema
    try:
        procedure = ExperimentProcedure(**procedure_dict)
        procedure_validated = procedure.dict()
    except Exception as e:
        print(f"⚠️  Schema validation warning: {e}")
        procedure_validated = procedure_dict
    
    # Build dynamic execution context with full topic & refinement hints
    effective_refinement = dict(refinement) if isinstance(refinement, dict) else {}
    if procedure_validated.get("experiment_type") == "dynamic_custom" and not effective_refinement.get("equations"):
        h_ref = _heuristic_refinement(topic, filter_and_compress_context(topic, []))
        for k in ("equations", "independent_vars", "dependent_vars", "control_vars", "refined_objective"):
            if not effective_refinement.get(k) and h_ref.get(k):
                effective_refinement[k] = h_ref[k]

    dynamic_ctx = dict(procedure_validated)
    dynamic_ctx["topic"] = topic
    dynamic_ctx["refinement"] = effective_refinement

    # Route novel / custom experiments directly to bespoke NumPy/SciPy synthesis;
    # known canonical sub-types go to authoritative deterministic engines first.
    if procedure_validated.get("experiment_type") == "dynamic_custom":
        raw_result = run_dynamic_simulation(dynamic_ctx)
        if raw_result.get("status") != "success":
            # Never hijack custom experiments into an unrelated preset (e.g. Otto cycle or LED)
            dyn_logs = list(raw_result.get("simulation_log") or [])
            dyn_err = "; ".join(raw_result.get("observations") or [])[:250]
            raw_result = router.llm_fallback.run(dynamic_ctx, error_context=dyn_err)
            raw_result["simulation_log"] = dyn_logs + list(raw_result.get("simulation_log") or [])
            raw_result["engine_used"] = "llm_fallback"
            raw_result["status"] = "fallback"
    else:
        try:
            raw_result = router.route(procedure_validated)
            if raw_result.get("status") == "fallback":
                dyn_res = run_dynamic_simulation(dynamic_ctx)
                if dyn_res.get("status") == "success":
                    raw_result = dyn_res
        except Exception as e:
            print(f"⚠️  Deterministic engine failed: {e}. Trying dynamic LLM engine...")
            try:
                raw_result = run_dynamic_simulation(dynamic_ctx)
            except Exception as dyn_err:
                raw_result = {
                    "status": "failed",
                    "engine_used": "fallback_error",
                    "numerical_results": {},
                    "plot_data": [],
                    "observations": [f"Simulation encountered an error: {e}"],
                    "confidence_score": 0.0,
                    "simulation_log": [f"Error: {e}", f"Dynamic error: {dyn_err}"]
                }

    # Attach token-filtering & prompt refinement audit trace when available
    if isinstance(refinement, dict) and refinement.get("token_filtering"):
        tf = refinement["token_filtering"]
        raw_result.setdefault("simulation_log", []).insert(
            0,
            f"[L1/L2_refinement] {refinement.get('refiner_source', 'qwen')}: "
            f"tokens {tf.get('raw_token_count', 0)}->{tf.get('filtered_token_count', 0)} "
            f"(-{tf.get('reduction_pct', 0)}% stop words removed)"
        )

    # Format output with validated 3D scene specification
    output = format_output(raw_result, procedure_validated)
    
    return output.dict()


def invoke(architect_output: dict) -> dict:
    """
    Entry point for integration with the pipeline.
    Compatible with both direct calls and LangChain usage.
    """
    return run_simulation(architect_output)
