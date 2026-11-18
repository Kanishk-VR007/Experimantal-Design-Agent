"""
Tests for simulation_agent.experiment_schema
Covers deterministic SI UnitConverter across physical dimensions, parameter
validation, missing-parameter reporting, and negative/out-of-range rejection.
"""

import math
import pytest
from simulation_agent.experiment_schema import (
    CanonicalExperimentSpec,
    ParameterConstraint,
    UnitConverter,
)


def test_unit_converter_length_force_pressure_electrical():
    assert math.isclose(UnitConverter.to_si(500.0, "mm", "length"), 0.5, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(10.0, "kN", "force"), 10000.0, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(200.0, "GPa", "stress"), 200e9, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(10.0, "kOhm", "resistance"), 10000.0, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(100.0, "uF", "capacitance"), 100e-6, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(10.0, "mH", "inductance"), 0.01, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(180.0, "deg", "angle"), math.pi, rel_tol=1e-9)
    assert math.isclose(UnitConverter.to_si(25.0, "C", "temperature"), 298.15, rel_tol=1e-9)


def test_unit_converter_rejects_incompatible_unit():
    with pytest.raises(ValueError):
        UnitConverter.to_si(5.0, "invalid_unit_xyz", "length")


def test_canonical_experiment_spec_validates_constraints_and_defaults():
    constraints = [
        ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True),
        ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True),
        ParameterConstraint(name="gravity", unit="m/s^2", required=False, positive=True, default=9.81, default_justification="Earth g"),
    ]
    spec = CanonicalExperimentSpec(
        domain="civil",
        experiment_type="simply_supported_beam_point_load",
        experiment_id="simply_supported_beam_point_load",
        parameters={"span_m": 5.0, "point_load_kN": 10.0},
    )
    validated, missing, errors, warnings = spec.resolve_parameters(constraints)
    assert missing == []
    assert errors == []
    assert validated["span_m"] == 5.0
    assert validated["point_load_kN"] == 10.0
    assert validated["gravity"] == 9.81


def test_canonical_experiment_spec_rejects_negative_and_missing():
    constraints = [
        ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True),
        ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True),
    ]
    spec = CanonicalExperimentSpec(
        domain="civil",
        experiment_type="simply_supported_beam_point_load",
        experiment_id="simply_supported_beam_point_load",
        parameters={"span_m": -3.0},
    )
    _, missing, errors, _ = spec.resolve_parameters(constraints, allow_documented_defaults=False)
    assert "point_load_kN" in missing
    assert any("positive" in e.lower() or "> 0" in e for e in errors)
