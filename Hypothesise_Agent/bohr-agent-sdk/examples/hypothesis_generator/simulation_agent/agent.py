"""
Simulation Agent - Main Entry Point
Orchestrates simulation pipeline: parse → route → simulate → format
"""

import json
from . import router
from .output_formatter import format_output
from .schema import ExperimentProcedure, SimulationOutput
from .dynamic_sim import run_dynamic_simulation


def extract_procedure_from_text(design_text: str, topic: str) -> dict:
    """
    Intelligently extract simulation parameters from Ollama's experimental design output.
    This parses the markdown/text output and extracts relevant fields.
    """
    
    # Default procedure structure
    procedure = {
        "domain": "general",
        "hypothesis": "",
        "steps": [],
        "reagents": [],
        "parameters": {},
        "expected_metrics": [],
        "experiment_type": None
    }
    
    # Detect domain from keywords — ordered most-specific first
    text_lower = design_text.lower()
    topic_lower = topic.lower()
    combined = text_lower + " " + topic_lower

    # Electronics / Arduino (check before generic "physics" to avoid misrouting)
    if any(w in combined for w in [
        "arduino", "breadboard", "led", "blink", "resistor", "capacitor",
        "transistor", "voltage divider", "microcontroller", "atmega",
        "electronics", "soldering", "circuit board", "rlc circuit",
    ]):
        procedure["domain"] = "electronics"
    # Computer Science / ML
    elif any(w in combined for w in [
        "machine learning", "neural network", "cnn", "transformer", "dropout",
        "deep learning", "training", "epoch", "loss function", "classifier",
        "algorithm complexity", "sorting", "big-o", "convolutional",
        "computer science", "gradient descent", "backpropagation",
    ]):
        procedure["domain"] = "computer_science"
    elif any(w in combined for w in ["chemical", "chemistry", "reaction", "titration", "molecule", "smiles"]):
        procedure["domain"] = "chemistry"
    elif any(w in combined for w in ["biology", "cell", "growth", "gene", "protein", "bacteria", "dna"]):
        procedure["domain"] = "biology"
    # Civil Engineering (before physics to catch "beam", "truss", "force")
    elif any(w in combined for w in [
        "civil", "structural", "beam", "truss", "bridge", "slab",
        "blueprint", "floor plan", "building design", "column load",
        "construction", "rcc", "reinforced concrete", "architecture",
    ]):
        procedure["domain"] = "civil_engineering"
    # Mechanical Engineering (before physics to catch "gear", "shaft", "engine")
    elif any(w in combined for w in [
        "gear", "spur gear", "shaft", "torsion", "torque",
        "mechanical engineering", "3d print", "cad",
        "otto cycle", "carnot", "thermodynamic cycle", "piston",
        "crankshaft", "connecting rod",
    ]):
        procedure["domain"] = "mechanical_engineering"
    elif any(w in combined for w in ["physics", "pendulum", "force", "motion", "energy", "projectile", "optics"]):
        procedure["domain"] = "physics"
    
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
    
    # Set default parameters based on domain
    if procedure["domain"] == "electronics":
        # Detect sub-type
        if any(w in combined for w in ["arduino", "blink", "microcontroller", "atmega"]):
            procedure["experiment_type"] = "arduino_led"
        elif any(w in combined for w in ["voltage divider"]):
            procedure["experiment_type"] = "voltage_divider"
        elif any(w in combined for w in ["rlc", "inductor", "resonan"]):
            procedure["experiment_type"] = "rlc_circuit"
        elif any(w in combined for w in ["led", "battery"]):
            procedure["experiment_type"] = "led_resistor"
        else:
            procedure["experiment_type"] = "arduino_led"
        procedure["parameters"] = {
            "supply_voltage_V":      5.0,
            "led_forward_voltage_V": 2.0,
            "led_current_mA":        20,
            "blink_frequency_Hz":    1.0,
        }

    elif procedure["domain"] == "computer_science":
        if any(w in combined for w in ["cnn", "transformer", "compare", "vit", "resnet"]):
            procedure["experiment_type"] = "model_comparison"
        elif any(w in combined for w in ["dropout", "regulariz"]):
            procedure["experiment_type"] = "dropout_effect"
        elif any(w in combined for w in ["algorithm", "complexity", "sort", "search", "big"]):
            procedure["experiment_type"] = "algorithm_complexity"
        elif any(w in combined for w in ["neural network", "training"]):
            procedure["experiment_type"] = "neural_network"
        else:
            procedure["experiment_type"] = "model_comparison"
        procedure["parameters"] = {"epochs": 50}

    elif procedure["domain"] == "chemistry":
        procedure["parameters"] = {
            "temperature_K": 298.15,
            "reaction_time_s": 120,
            "initial_concentration_M": 1.0,
            "activation_energy_kJ": 50,
            "pre_exponential_factor": 1e10
        }
        if "titration" in text_lower:
            procedure["experiment_type"] = "titration"
            procedure["parameters"]["pKa"] = 4.74
    
    elif procedure["domain"] == "biology":
        procedure["parameters"] = {
            "initial_population": 100,
            "carrying_capacity": 1e6,
            "growth_rate": 0.5,
            "time_hours": 24
        }
        if "gene" in text_lower or "expression" in text_lower:
            procedure["experiment_type"] = "gene_expression"
            procedure["parameters"]["transcription_rate"] = 0.8
            procedure["parameters"]["translation_rate"] = 0.5

    elif procedure["domain"] == "civil_engineering":
        if any(w in combined for w in ["beam", "load", "deflect", "slab"]):
            procedure["experiment_type"] = "beam_analysis"
            procedure["parameters"] = {
                "span_m": 6.0, "load_kN_per_m": 10.0,
                "elastic_modulus_GPa": 200.0,
                "moment_of_inertia_m4": 8.33e-6,
                "beam_width_mm": 300, "beam_depth_mm": 500,
            }
        elif any(w in combined for w in ["truss", "bridge", "roof"]):
            procedure["experiment_type"] = "truss_analysis"
            procedure["parameters"] = {
                "span_m": 10.0, "height_m": 3.0,
                "panels": 4, "point_load_kN": 20.0,
            }
        else:
            procedure["experiment_type"] = "building_blueprint"
            procedure["parameters"] = {
                "floors": 2, "width_m": 12.0, "depth_m": 8.0,
                "floor_height_m": 3.0, "wall_thickness_mm": 230,
                "column_size_mm": 300, "rooms_per_floor": 4,
            }

    elif procedure["domain"] == "mechanical_engineering":
        if any(w in combined for w in ["gear", "spur", "pinion", "teeth"]):
            procedure["experiment_type"] = "gear_train"
            procedure["parameters"] = {
                "teeth_driver": 20, "teeth_driven": 40,
                "module_mm": 2.5, "rpm_input": 1500,
                "power_kW": 5.0, "pressure_angle_deg": 20,
                "face_width_mm": 25,
            }
        elif any(w in combined for w in ["shaft", "torsion", "torque", "twist"]):
            procedure["experiment_type"] = "shaft_design"
            procedure["parameters"] = {
                "torque_Nm": 200, "bending_moment_Nm": 150,
                "length_mm": 500, "diameter_mm": 40,
                "material": "AISI 1045 Steel",
            }
        else:
            procedure["experiment_type"] = "thermo_cycle"
            procedure["parameters"] = {
                "cycle": "otto", "T_hot_K": 1200, "T_cold_K": 300,
                "compression_ratio": 8, "gamma": 1.4,
                "P1_kPa": 101.325, "V1_L": 0.5,
            }
    
    elif procedure["domain"] == "physics":
        procedure["parameters"] = {
            "gravity": 9.81,
            "length_m": 1.0,
            "damping": 0.1,
            "angle_rad": 0.5
        }
        if "pendulum" in text_lower:
            procedure["experiment_type"] = "pendulum"
        elif "circuit" in text_lower or "rlc" in text_lower:
            procedure["experiment_type"] = "rlc_circuit"
            procedure["parameters"] = {
                "resistance_ohm": 10,
                "inductance_H": 0.1,
                "capacitance_F": 0.001,
                "voltage_V": 5.0
            }
        elif "projectile" in text_lower:
            procedure["experiment_type"] = "projectile"
            procedure["parameters"] = {
                "initial_velocity_ms": 20,
                "launch_angle_deg": 45,
                "gravity": 9.81
            }
    
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
    
    procedure_dict = extract_procedure_from_text(design_text, topic)
    
    # Validate schema
    try:
        procedure = ExperimentProcedure(**procedure_dict)
        procedure_validated = procedure.dict()
    except Exception as e:
        print(f"⚠️  Schema validation warning: {e}")
        procedure_validated = procedure_dict
    
    # Route to dynamic LLM code generation engine
    raw_result = run_dynamic_simulation(procedure_validated)
    
    # Format output
    output = format_output(raw_result, procedure_validated)
    
    return output.dict()


def invoke(architect_output: dict) -> dict:
    """
    Entry point for integration with the pipeline.
    Compatible with both direct calls and LangChain usage.
    """
    return run_simulation(architect_output)
