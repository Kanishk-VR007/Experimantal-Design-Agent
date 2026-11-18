"""
Canonical Scientific Experiment Schema & SI Unit System
========================================================
Provides:
  - Deterministic SI unit conversion across all supported engineering/scientific quantities.
  - Canonical Pydantic v2 experiment specification (`CanonicalExperimentSpec`).
  - Central result contract (`ExperimentResultContract`) shared between simulation engines,
    scientific validation, output formatting, and 3D scene generation.
  - Strict parameter & range validation that reports missing required physical parameters
    instead of silently inventing arbitrary values.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator


# ─── Allowed Simulation Statuses & Domains ────────────────────────────────────

SimulationStatus = Literal[
    "success",
    "partial",
    "unsupported",
    "failed",
    "validation_failed",
    "illustrative",
]

SimulationType = Literal[
    "deterministic_analytical",
    "deterministic_numerical",
    "algorithm_execution",
    "parametric_model",
    "illustrative",
    "unsupported",
]

CanonicalDomain = Literal[
    "civil",
    "mechanical",
    "physics",
    "chemistry",
    "biology",
    "electronics",
    "computer_science",
    "general",
]

DOMAIN_NORMALIZATION_MAP: Dict[str, str] = {
    # Civil
    "civil": "civil",
    "civil_engineering": "civil",
    "civil eng": "civil",
    "civil_eng": "civil",
    "structural": "civil",
    "structural_engineering": "civil",
    "construction": "civil",
    "building": "civil",
    "architecture": "civil",
    # Mechanical
    "mechanical": "mechanical",
    "mechanical_engineering": "mechanical",
    "mech": "mechanical",
    "mech_engineering": "mechanical",
    "mechanics": "mechanical",
    "gear": "mechanical",
    "shaft": "mechanical",
    "thermodynamic": "mechanical",
    "kinematics": "mechanical",
    # Physics
    "physics": "physics",
    "physical": "physics",
    "phys": "physics",
    # Chemistry
    "chemistry": "chemistry",
    "chemical": "chemistry",
    "chem": "chemistry",
    "molecular": "chemistry",
    "titration": "chemistry",
    # Biology
    "biology": "biology",
    "biological": "biology",
    "bio": "biology",
    "life_science": "biology",
    "biochemistry": "biology",
    # Electronics / Electrical
    "electronics": "electronics",
    "electronic": "electronics",
    "electrical": "electronics",
    "electrical_engineering": "electronics",
    "electronic_engineering": "electronics",
    "ee": "electronics",
    "circuit": "electronics",
    "circuits": "electronics",
    "arduino": "electronics",
    # Computer Science
    "computer_science": "computer_science",
    "cs": "computer_science",
    "comp sci": "computer_science",
    "comp_sci": "computer_science",
    "computerscience": "computer_science",
    "algorithm": "computer_science",
    "algorithms": "computer_science",
    "sorting": "computer_science",
    "graph": "computer_science",
    "machine_learning": "computer_science",
    "ml": "computer_science",
    "deep_learning": "computer_science",
    "ai": "computer_science",
    "artificial_intelligence": "computer_science",
    # General
    "general": "general",
    "unknown": "general",
    "other": "general",
}

# Backwards-compatible long domain names used by existing frontend/tests
LEGACY_DOMAIN_NAME: Dict[str, str] = {
    "civil": "civil_engineering",
    "mechanical": "mechanical_engineering",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "electronics": "electronics",
    "computer_science": "computer_science",
    "general": "general",
}


def normalize_canonical_domain(domain: Optional[str]) -> str:
    """Normalize any domain alias into the canonical short domain key."""
    d = str(domain or "").strip().lower()
    return DOMAIN_NORMALIZATION_MAP.get(d, "general")


def to_legacy_domain_name(domain: Optional[str]) -> str:
    """Convert canonical domain into legacy API/UI domain key where expected."""
    canon = normalize_canonical_domain(domain)
    return LEGACY_DOMAIN_NAME.get(canon, canon)


# ─── Deterministic SI Unit Conversion Engine ──────────────────────────────────

class UnitConversionError(ValueError):
    """Raised when an unknown or dimensionally incompatible unit conversion is requested."""


# Mapping: dimension -> {unit_alias_lower: (scale_to_SI, offset_to_SI)}
# Conversion to SI: value_SI = value * scale + offset
# Conversion from SI: value = (value_SI - offset) / scale
_UNIT_TABLES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "length": {
        "m": (1.0, 0.0), "meter": (1.0, 0.0), "meters": (1.0, 0.0),
        "mm": (1e-3, 0.0), "millimeter": (1e-3, 0.0), "millimeters": (1e-3, 0.0),
        "cm": (1e-2, 0.0), "centimeter": (1e-2, 0.0), "centimeters": (1e-2, 0.0),
        "km": (1e3, 0.0), "kilometer": (1e3, 0.0),
        "um": (1e-6, 0.0), "µm": (1e-6, 0.0), "micron": (1e-6, 0.0),
        "in": (0.0254, 0.0), "inch": (0.0254, 0.0), "inches": (0.0254, 0.0),
        "ft": (0.3048, 0.0), "foot": (0.3048, 0.0), "feet": (0.3048, 0.0),
    },
    "force": {
        "n": (1.0, 0.0), "newton": (1.0, 0.0), "newtons": (1.0, 0.0),
        "kn": (1e3, 0.0), "kilonewton": (1e3, 0.0), "kilonewtons": (1e3, 0.0),
        "mn": (1e6, 0.0), "meganewton": (1e6, 0.0),
        "lbf": (4.4482216152605, 0.0),
    },
    "distributed_load": {
        "n/m": (1.0, 0.0), "kn/m": (1e3, 0.0), "mn/m": (1e6, 0.0),
        "lbf/ft": (14.593902937, 0.0),
    },
    "moment": {
        "n*m": (1.0, 0.0), "nm": (1.0, 0.0), "n·m": (1.0, 0.0), "n-m": (1.0, 0.0),
        "kn*m": (1e3, 0.0), "knm": (1e3, 0.0), "kn·m": (1e3, 0.0), "kn-m": (1e3, 0.0),
        "mn*m": (1e6, 0.0), "lbf*ft": (1.3558179483, 0.0),
    },
    "mass": {
        "kg": (1.0, 0.0), "kilogram": (1.0, 0.0), "kilograms": (1.0, 0.0),
        "g": (1e-3, 0.0), "gram": (1e-3, 0.0), "grams": (1e-3, 0.0),
        "mg": (1e-6, 0.0), "lb": (0.45359237, 0.0), "lbm": (0.45359237, 0.0),
    },
    "time": {
        "s": (1.0, 0.0), "sec": (1.0, 0.0), "second": (1.0, 0.0), "seconds": (1.0, 0.0),
        "ms": (1e-3, 0.0), "us": (1e-6, 0.0), "µs": (1e-6, 0.0),
        "min": (60.0, 0.0), "minute": (60.0, 0.0), "minutes": (60.0, 0.0),
        "h": (3600.0, 0.0), "hr": (3600.0, 0.0), "hour": (3600.0, 0.0), "hours": (3600.0, 0.0),
    },
    "temperature": {
        "k": (1.0, 0.0), "kelvin": (1.0, 0.0),
        "c": (1.0, 273.15), "degc": (1.0, 273.15), "°c": (1.0, 273.15), "celsius": (1.0, 273.15),
        "f": (5.0 / 9.0, 273.15 - 32.0 * 5.0 / 9.0),
        "degf": (5.0 / 9.0, 273.15 - 32.0 * 5.0 / 9.0),
        "°f": (5.0 / 9.0, 273.15 - 32.0 * 5.0 / 9.0),
    },
    "pressure": {
        "pa": (1.0, 0.0), "n/m2": (1.0, 0.0), "n/m^2": (1.0, 0.0),
        "kpa": (1e3, 0.0), "kn/m2": (1e3, 0.0),
        "mpa": (1e6, 0.0), "n/mm2": (1e6, 0.0),
        "gpa": (1e9, 0.0), "gn/m2": (1e9, 0.0),
        "bar": (1e5, 0.0), "atm": (101325.0, 0.0),
        "psi": (6894.757293168, 0.0), "ksi": (6894757.293168, 0.0),
    },
    "stress": {
        "pa": (1.0, 0.0), "kpa": (1e3, 0.0), "mpa": (1e6, 0.0), "gpa": (1e9, 0.0),
        "psi": (6894.757293168, 0.0), "ksi": (6894757.293168, 0.0),
    },
    "strain": {
        "1": (1.0, 0.0), "dimensionless": (1.0, 0.0), "m/m": (1.0, 0.0),
        "%": (1e-2, 0.0), "microstrain": (1e-6, 0.0), "ue": (1e-6, 0.0), "µε": (1e-6, 0.0),
    },
    "voltage": {
        "v": (1.0, 0.0), "volt": (1.0, 0.0), "volts": (1.0, 0.0),
        "mv": (1e-3, 0.0), "kv": (1e3, 0.0), "uv": (1e-6, 0.0),
    },
    "current": {
        "a": (1.0, 0.0), "amp": (1.0, 0.0), "amps": (1.0, 0.0), "ampere": (1.0, 0.0),
        "ma": (1e-3, 0.0), "ua": (1e-6, 0.0), "µa": (1e-6, 0.0), "ka": (1e3, 0.0),
    },
    "resistance": {
        "ohm": (1.0, 0.0), "ohms": (1.0, 0.0), "ω": (1.0, 0.0),
        "kohm": (1e3, 0.0), "kohms": (1e3, 0.0), "kω": (1e3, 0.0),
        "mohm": (1e6, 0.0), "mohms": (1e6, 0.0), "mω": (1e6, 0.0),
    },
    "inductance": {
        "h": (1.0, 0.0), "henry": (1.0, 0.0),
        "mh": (1e-3, 0.0), "uh": (1e-6, 0.0), "µh": (1e-6, 0.0),
    },
    "capacitance": {
        "f": (1.0, 0.0), "farad": (1.0, 0.0),
        "mf": (1e-3, 0.0), "uf": (1e-6, 0.0), "µf": (1e-6, 0.0),
        "nf": (1e-9, 0.0), "pf": (1e-12, 0.0),
    },
    "energy": {
        "j": (1.0, 0.0), "joule": (1.0, 0.0), "joules": (1.0, 0.0),
        "kj": (1e3, 0.0), "mj": (1e6, 0.0),
        "cal": (4.184, 0.0), "kcal": (4184.0, 0.0),
        "ev": (1.602176634e-19, 0.0),
    },
    "power": {
        "w": (1.0, 0.0), "watt": (1.0, 0.0), "watts": (1.0, 0.0),
        "mw": (1e-3, 0.0), "kw": (1e3, 0.0), "megawatt": (1e6, 0.0),
        "hp": (745.699872, 0.0),
    },
    "angle": {
        "rad": (1.0, 0.0), "radian": (1.0, 0.0), "radians": (1.0, 0.0),
        "deg": (math.pi / 180.0, 0.0), "°": (math.pi / 180.0, 0.0),
        "degree": (math.pi / 180.0, 0.0), "degrees": (math.pi / 180.0, 0.0),
        "rev": (2.0 * math.pi, 0.0),
    },
    "angular_velocity": {
        "rad/s": (1.0, 0.0), "rad_s": (1.0, 0.0),
        "rpm": (2.0 * math.pi / 60.0, 0.0),
        "deg/s": (math.pi / 180.0, 0.0),
        "hz": (2.0 * math.pi, 0.0),
    },
    "frequency": {
        "hz": (1.0, 0.0), "khz": (1e3, 0.0), "mhz": (1e6, 0.0),
        "rad/s": (1.0 / (2.0 * math.pi), 0.0),
    },
    "area": {
        "m2": (1.0, 0.0), "m^2": (1.0, 0.0), "m²": (1.0, 0.0),
        "cm2": (1e-4, 0.0), "cm^2": (1e-4, 0.0),
        "mm2": (1e-6, 0.0), "mm^2": (1e-6, 0.0),
    },
    "second_moment_of_area": {
        "m4": (1.0, 0.0), "m^4": (1.0, 0.0), "m⁴": (1.0, 0.0),
        "cm4": (1e-8, 0.0), "cm^4": (1e-8, 0.0),
        "mm4": (1e-12, 0.0), "mm^4": (1e-12, 0.0),
    },
    "volume": {
        "l": (1.0, 0.0), "liter": (1.0, 0.0), "liters": (1.0, 0.0),
        "ml": (1e-3, 0.0), "cm3": (1e-3, 0.0),
        "m3": (1e3, 0.0), "m^3": (1e3, 0.0),
    },
    "concentration": {
        "m": (1.0, 0.0), "mol/l": (1.0, 0.0), "mol/dm3": (1.0, 0.0),
        "mm": (1e-3, 0.0), "mmol/l": (1e-3, 0.0),
        "um": (1e-6, 0.0), "µm": (1e-6, 0.0), "umol/l": (1e-6, 0.0),
    },
    "velocity": {
        "m/s": (1.0, 0.0), "ms": (1.0, 0.0),
        "km/h": (1.0 / 3.6, 0.0), "kph": (1.0 / 3.6, 0.0),
        "cm/s": (1e-2, 0.0), "ft/s": (0.3048, 0.0),
    },
}


class UnitConverter:
    """Explicit, dimension-checked SI unit converter."""

    @classmethod
    def supported_dimensions(cls) -> List[str]:
        return sorted(_UNIT_TABLES.keys())

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str, dimension: Optional[str] = None) -> float:
        """Convert numeric value between compatible units."""
        fu = str(from_unit).strip().lower()
        tu = str(to_unit).strip().lower()
        if fu == tu:
            return float(value)

        dims_to_check = [dimension] if dimension else list(_UNIT_TABLES.keys())
        for dim in dims_to_check:
            table = _UNIT_TABLES.get(dim)
            if not table:
                continue
            if fu in table and tu in table:
                f_scale, f_off = table[fu]
                t_scale, t_off = table[tu]
                si_val = float(value) * f_scale + f_off
                return (si_val - t_off) / t_scale

        raise UnitConversionError(
            f"Incompatible or unsupported unit conversion: '{from_unit}' -> '{to_unit}'"
            + (f" (dimension='{dimension}')" if dimension else "")
        )

    @classmethod
    def to_si(cls, value: float, unit: str, dimension: str) -> float:
        """Convert value in `unit` to canonical SI unit for `dimension`."""
        table = _UNIT_TABLES.get(dimension)
        if not table:
            raise UnitConversionError(f"Unknown physical dimension: '{dimension}'")
        u = str(unit).strip().lower()
        if u not in table:
            raise UnitConversionError(f"Unit '{unit}' is not valid for dimension '{dimension}'")
        scale, offset = table[u]
        return float(value) * scale + offset

    @classmethod
    def is_valid_unit(cls, unit: str, dimension: str) -> bool:
        table = _UNIT_TABLES.get(dimension, {})
        return str(unit).strip().lower() in table


# ─── Parameter Specification & Canonical Experiment Schema ────────────────────

class ParameterConstraint(BaseModel):
    """Schema constraints for a single physical/algorithmic input parameter."""
    name: str
    unit: str = ""
    dimension: Optional[str] = None
    required: bool = True
    positive: bool = False
    non_negative: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    value_type: Literal["float", "int", "str", "bool", "dict", "list", "any"] = "float"
    default: Optional[Any] = None
    default_justification: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class CanonicalExperimentSpec(BaseModel):
    """
    Canonical Pydantic scientific experiment specification shared across
    experiment classification, routing, deterministic solvers, validation,
    and 3D scene generation.
    """
    experiment_id: str = Field(..., description="Registered canonical experiment identifier")
    domain: str = Field(..., description="Canonical scientific domain")
    experiment_type: str = Field(..., description="Exact solver/experiment type key")
    description: str = Field(default="", description="Natural-language scientific description")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    units: Dict[str, str] = Field(default_factory=dict)
    independent_variables: List[str] = Field(default_factory=list)
    dependent_variables: List[str] = Field(default_factory=list)
    boundary_conditions: List[str] = Field(default_factory=list)
    initial_conditions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    requested_outputs: List[str] = Field(default_factory=list)
    visualization_requirements: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("domain")
    @classmethod
    def _norm_domain(cls, v: str) -> str:
        return normalize_canonical_domain(v)

    def resolve_parameters(
        self,
        constraints: List[ParameterConstraint],
        allow_documented_defaults: bool = True,
    ) -> Tuple[Dict[str, Any], List[str], List[str], List[str]]:
        """
        Validate parameters against registry constraints.
        Returns: (resolved_params, missing_required, errors, warnings).
        Never silently fabricates critical missing parameters that lack documented defaults.
        """
        resolved = dict(self.parameters)
        missing: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        for c in constraints:
            val = None
            source_key = None
            if c.name in resolved and resolved[c.name] is not None:
                val = resolved[c.name]
                source_key = c.name
            else:
                for alias in c.aliases:
                    if alias in resolved and resolved[alias] is not None:
                        val = resolved[alias]
                        source_key = alias
                        break

            # Explicit unit conversion if alias encodes a different unit or self.units specifies one
            if val is not None and c.dimension and c.unit:
                provided_unit = self.units.get(source_key or c.name)
                if not provided_unit and source_key and source_key != c.name:
                    provided_unit = _infer_unit_from_key(source_key)
                if provided_unit and provided_unit.lower() != c.unit.lower():
                    try:
                        val = UnitConverter.convert(float(val), provided_unit, c.unit, dimension=c.dimension)
                    except UnitConversionError as exc:
                        errors.append(f"Parameter '{c.name}': {exc}")
                        continue

            if val is None:
                if c.required:
                    if allow_documented_defaults and c.default is not None:
                        val = c.default
                        justification = c.default_justification or "documented standard default"
                        warnings.append(
                            f"Parameter '{c.name}' not explicitly provided; using documented default "
                            f"{c.default} {c.unit} ({justification})."
                        )
                    else:
                        missing.append(c.name)
                        continue
                else:
                    if c.default is not None:
                        val = c.default
                    else:
                        continue

            # Type & numeric range validation
            if c.value_type in ("float", "int"):
                try:
                    num = int(val) if c.value_type == "int" and not isinstance(val, bool) else float(val)
                except (TypeError, ValueError):
                    errors.append(f"Parameter '{c.name}' must be numeric ({c.value_type}), got {val!r}.")
                    continue
                if isinstance(val, bool):
                    errors.append(f"Parameter '{c.name}' cannot be boolean.")
                    continue
                if not math.isfinite(float(num)):
                    errors.append(f"Parameter '{c.name}' must be finite, got {num!r}.")
                    continue
                if c.positive and num <= 0:
                    errors.append(f"Parameter '{c.name}' must be strictly positive (> 0), got {num}.")
                    continue
                if c.non_negative and num < 0:
                    errors.append(f"Parameter '{c.name}' must be non-negative (>= 0), got {num}.")
                    continue
                if c.min_value is not None and num < c.min_value:
                    errors.append(f"Parameter '{c.name}'={num} is below valid minimum {c.min_value}.")
                    continue
                if c.max_value is not None and num > c.max_value:
                    errors.append(f"Parameter '{c.name}'={num} exceeds valid maximum {c.max_value}.")
                    continue
                resolved[c.name] = num
            elif c.value_type == "dict":
                if not isinstance(val, dict):
                    errors.append(f"Parameter '{c.name}' must be a dictionary, got {type(val).__name__}.")
                    continue
                resolved[c.name] = val
            elif c.value_type == "list":
                if not isinstance(val, list):
                    errors.append(f"Parameter '{c.name}' must be a list, got {type(val).__name__}.")
                    continue
                resolved[c.name] = val
            else:
                resolved[c.name] = val

        return resolved, missing, errors, warnings


def _infer_unit_from_key(key: str) -> Optional[str]:
    """Infer physical unit suffix from conventional snake_case parameter names."""
    k = key.strip()
    suffix_map = [
        ("_GPa", "GPa"), ("_gpa", "GPa"),
        ("_MPa", "MPa"), ("_mpa", "MPa"),
        ("_kPa", "kPa"), ("_kpa", "kPa"),
        ("_Pa", "Pa"), ("_pa", "Pa"),
        ("_kN_per_m", "kN/m"), ("_N_per_m", "N/m"),
        ("_kNm", "kN*m"), ("_Nm", "N*m"),
        ("_kN", "kN"), ("_kn", "kN"), ("_N", "N"),
        ("_mm4", "mm4"), ("_cm4", "cm4"), ("_m4", "m4"),
        ("_mm2", "mm2"), ("_cm2", "cm2"), ("_m2", "m2"),
        ("_mm", "mm"), ("_cm", "cm"), ("_km", "km"), ("_m", "m"),
        ("_deg", "deg"), ("_rad", "rad"),
        ("_rpm", "rpm"), ("_rad_s", "rad/s"),
        ("_kW", "kW"), ("_mW", "mW"), ("_W", "W"),
        ("_kJ", "kJ"), ("_J", "J"),
        ("_mA", "mA"), ("_uA", "uA"), ("_A", "A"),
        ("_mV", "mV"), ("_kV", "kV"), ("_V", "V"),
        ("_kohm", "kohm"), ("_Mohm", "Mohm"), ("_ohm", "ohm"),
        ("_mH", "mH"), ("_uH", "uH"), ("_H", "H"),
        ("_uF", "uF"), ("_mF", "mF"), ("_nF", "nF"), ("_F", "F"),
        ("_mL", "mL"), ("_L", "L"),
        ("_uM", "uM"), ("_mM", "mM"), ("_M", "M"),
        ("_K", "K"), ("_C", "C"),
        ("_kg", "kg"), ("_g", "g"),
        ("_ms", "m/s"), ("_h", "h"), ("_s", "s"),
    ]
    for suf, unit in suffix_map:
        if k.endswith(suf):
            return unit
    return None


# ─── Central Experiment Result Contract ───────────────────────────────────────

class SolverInfo(BaseModel):
    name: str
    version: str = "2.0"
    method: str
    equations: List[str] = Field(default_factory=list)


class ValidationCheckItem(BaseModel):
    name: str
    passed: bool
    detail: str
    residual: Optional[float] = None
    tolerance: Optional[float] = None


class ValidationSummary(BaseModel):
    input_valid: bool = False
    dimensional_valid: bool = False
    equilibrium_valid: Optional[bool] = None
    physical_constraints_valid: bool = False
    benchmark_valid: Optional[bool] = None
    numerical_convergence: Optional[bool] = None
    overall_valid: bool = False
    validation_level: Literal[
        "implemented",
        "tested",
        "benchmark_validated",
        "validated_within_assumptions",
        "failed",
    ] = "implemented"
    checks: List[ValidationCheckItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class VisualizationContract(BaseModel):
    template: str
    scene_specification: Optional[Dict[str, Any]] = None
    animation_data: Dict[str, Any] = Field(default_factory=dict)
    parameter_bindings: List[str] = Field(default_factory=list)
    is_simulation_backed: bool = False
    scene_valid: bool = False
    validation_notices: List[str] = Field(default_factory=list)


class ExperimentResultContract(BaseModel):
    """
    Central structured result contract connecting simulation engine,
    scientific validator, output formatter, 3D scene generator, and frontend.
    """
    experiment_id: str
    domain: str
    simulation_status: SimulationStatus
    simulation_type: SimulationType = "deterministic_analytical"
    solver: SolverInfo
    solver_results: Dict[str, Any] = Field(default_factory=dict)
    plots: List[Dict[str, Any]] = Field(default_factory=list)
    validation: ValidationSummary = Field(default_factory=ValidationSummary)
    visualization: Optional[VisualizationContract] = None
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

