"""
Central Scientific Experiment Registry & Deterministic Classifier
=================================================================
Single source of truth mapping every supported scientific/engineering experiment to:
  - Unique canonical experiment identifier (`experiment_id`)
  - Canonical scientific domain (`civil`, `mechanical`, `physics`, `chemistry`,
    `biology`, `electronics`, `computer_science`)
  - Exact deterministic solver name & engine module
  - Required & optional parameters, SI units, constraints, and justified defaults
  - Governing equations, operating conditions, assumptions, and limitations
  - Supported outputs & validation test names
  - Exact compatible 3D visualization template

No router or scene generator may invent an arbitrary default solver or scene for
an unrecognized experiment.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from .experiment_schema import ParameterConstraint, normalize_canonical_domain


class ExperimentRegistryEntry(BaseModel):
    experiment_id: str
    domain: str
    solver: str
    engine_module: str
    method: str
    equations: List[str] = Field(default_factory=list)
    required_parameters: List[str] = Field(default_factory=list)
    optional_parameters: List[str] = Field(default_factory=list)
    parameter_units: Dict[str, str] = Field(default_factory=dict)
    parameter_constraints: List[ParameterConstraint] = Field(default_factory=list)
    operating_conditions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    supported_outputs: List[str] = Field(default_factory=list)
    validation_tests: List[str] = Field(default_factory=list)
    visualization_template: str
    aliases: List[str] = Field(default_factory=list)


def _entry(**kwargs) -> ExperimentRegistryEntry:
    constraints = kwargs.get("parameter_constraints", [])
    if constraints and not kwargs.get("required_parameters"):
        kwargs["required_parameters"] = [c.name for c in constraints if c.required]
    if constraints and not kwargs.get("optional_parameters"):
        kwargs["optional_parameters"] = [c.name for c in constraints if not c.required]
    if constraints and not kwargs.get("parameter_units"):
        kwargs["parameter_units"] = {c.name: c.unit for c in constraints if c.unit}
    return ExperimentRegistryEntry(**kwargs)


# ─── Master Experiment Registry ───────────────────────────────────────────────

EXPERIMENT_REGISTRY: Dict[str, ExperimentRegistryEntry] = {
    # ═══════════════════════════════════════════════════════════════════════════
    # CIVIL ENGINEERING
    # ═══════════════════════════════════════════════════════════════════════════
    "simply_supported_beam_point_load": _entry(
        experiment_id="simply_supported_beam_point_load",
        domain="civil",
        solver="beam_central_point_load",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical static equilibrium & beam deflection",
        equations=[
            "R_A = R_B = P / 2",
            "M_max = P * L / 4",
            "delta_max = P * L^3 / (48 * E * I)",
            "V(x) = +P/2 for x < L/2; -P/2 for x > L/2",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L", "length_m"]),
            ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True, aliases=["P_kN", "P", "load_kN", "point_load_N"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E_Pa", "E_GPa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I_m4", "I"]),
            ParameterConstraint(name="beam_width_mm", unit="mm", dimension="length", required=False, positive=True, default=200.0, default_justification="Reference rectangular section width for stress display"),
            ParameterConstraint(name="beam_depth_mm", unit="mm", dimension="length", required=False, positive=True, default=400.0, default_justification="Reference rectangular section depth for stress display"),
        ],
        operating_conditions=["Linear elastic isotropic material", "Small deflections (delta << L)", "Static central vertical point load"],
        assumptions=[
            "Euler-Bernoulli plane sections remain plane and perpendicular to neutral axis",
            "Shear deformation neglected (slender beam L/h >= 5)",
            "Self-weight neglected unless added explicitly",
            "Deflection requires explicit E and I; omitted if E or I is missing",
        ],
        limitations=["Does not model plastic yielding, buckling, or shear-thick beams"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "max_bending_moment_kNm", "max_shear_force_kN", "max_deflection_mm", "shear_force_diagram", "bending_moment_diagram", "deflection_curve"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium", "benchmark_5m_10kN_central_point_load"],
        visualization_template="beam_deformation",
        aliases=["beam_point_load", "central_point_load_beam", "simply_supported_point_load"],
    ),
    "simply_supported_beam_eccentric_point_load": _entry(
        experiment_id="simply_supported_beam_eccentric_point_load",
        domain="civil",
        solver="beam_eccentric_point_load",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical static equilibrium & Macaulay deflection",
        equations=[
            "R_A = P * b / L, R_B = P * a / L (a + b = L)",
            "M_max = P * a * b / L at x = a",
            "y(x) via Macaulay singularity integration",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L", "length_m"]),
            ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True, aliases=["P_kN", "P", "load_kN"]),
            ParameterConstraint(name="load_position_m", unit="m", dimension="length", required=True, positive=True, aliases=["a_m", "a", "x_load_m"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E_Pa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
        ],
        operating_conditions=["0 < a < L", "Linear elastic small deflection"],
        assumptions=["Euler-Bernoulli linear elastic beam theory", "Pin at x=0, roller at x=L"],
        limitations=["Single concentrated vertical load; shear deformation neglected"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "max_bending_moment_kNm", "max_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium"],
        visualization_template="beam_deformation",
        aliases=["eccentric_point_load", "beam_eccentric_load"],
    ),
    "simply_supported_beam_udl": _entry(
        experiment_id="simply_supported_beam_udl",
        domain="civil",
        solver="beam_udl",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical UDL solution",
        equations=[
            "R_A = R_B = w * L / 2",
            "M_max = w * L^2 / 8",
            "delta_max = 5 * w * L^4 / (384 * E * I)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L", "length_m"]),
            ParameterConstraint(name="load_kN_per_m", unit="kN/m", dimension="distributed_load", required=True, positive=True, aliases=["w", "udl_kN_per_m", "load_N_per_m"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E_Pa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
            ParameterConstraint(name="beam_width_mm", unit="mm", dimension="length", required=False, positive=True, default=300.0, default_justification="Reference rectangular section width"),
            ParameterConstraint(name="beam_depth_mm", unit="mm", dimension="length", required=False, positive=True, default=500.0, default_justification="Reference rectangular section depth"),
        ],
        operating_conditions=["Uniformly distributed downward load over full span", "Linear elastic small deflection"],
        assumptions=["Euler-Bernoulli beam theory", "Uniform cross-section along span"],
        limitations=["Linear elastic range only"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "max_bending_moment_kNm", "max_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium", "benchmark_5m_10kNm_udl"],
        visualization_template="beam_deformation",
        aliases=["beam_udl", "beam_analysis", "simply_supported_beam"],
    ),
    "simply_supported_beam_multiple_loads": _entry(
        experiment_id="simply_supported_beam_multiple_loads",
        domain="civil",
        solver="beam_multiple_loads",
        engine_module="civil_sim",
        method="Euler-Bernoulli linear superposition of concentrated loads",
        equations=[
            "R_B = sum(P_i * a_i) / L; R_A = sum(P_i) - R_B",
            "V(x), M(x), y(x) by exact superposition",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L"]),
            ParameterConstraint(name="point_loads", value_type="list", required=True),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
        ],
        operating_conditions=["Linear elastic superposition", "All load positions satisfy 0 < a_i < L"],
        assumptions=["Linear elasticity permits exact superposition of individual point-load responses"],
        limitations=["Does not include geometric nonlinearity"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "max_bending_moment_kNm", "max_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium"],
        visualization_template="beam_deformation",
        aliases=["multiple_point_loads_beam"],
    ),
    "simply_supported_beam_moment": _entry(
        experiment_id="simply_supported_beam_moment",
        domain="civil",
        solver="beam_applied_moment",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical applied couple moment solution",
        equations=[
            "R_A = -M_0 / L, R_B = +M_0 / L",
            "M(x) step discontinuity of M_0 at x = a",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L"]),
            ParameterConstraint(name="applied_moment_kNm", unit="kN*m", dimension="moment", required=True, aliases=["M0_kNm", "moment_kNm"]),
            ParameterConstraint(name="moment_position_m", unit="m", dimension="length", required=False, non_negative=True, aliases=["a_m", "a"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
        ],
        operating_conditions=["0 <= a <= L", "Linear elastic small deflection"],
        assumptions=["Concentrated clockwise moment M_0 applied at x=a"],
        limitations=["Linear elastic range only"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "max_bending_moment_kNm", "max_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium"],
        visualization_template="beam_deformation",
        aliases=["beam_applied_moment", "applied_bending_moment"],
    ),
    "cantilever_beam_point_load": _entry(
        experiment_id="cantilever_beam_point_load",
        domain="civil",
        solver="cantilever_point_load",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical cantilever point-load solution",
        equations=[
            "R_fixed = P, M_fixed = -P * a",
            "delta_tip = P * a^2 * (3*L - a) / (6 * E * I)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L", "length_m"]),
            ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True, aliases=["P_kN", "P", "load_kN"]),
            ParameterConstraint(name="load_position_m", unit="m", dimension="length", required=False, positive=True, aliases=["a_m", "a"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E_Pa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
        ],
        operating_conditions=["Fixed at x=0, free at x=L", "0 < a <= L (defaults to tip a=L)"],
        assumptions=["Euler-Bernoulli linear elastic beam theory"],
        limitations=["Small deflection theory"],
        supported_outputs=["fixed_reaction_kN", "fixed_moment_kNm", "tip_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium"],
        visualization_template="beam_deformation",
        aliases=["cantilever_point_load"],
    ),
    "cantilever_beam_udl": _entry(
        experiment_id="cantilever_beam_udl",
        domain="civil",
        solver="cantilever_udl",
        engine_module="civil_sim",
        method="Euler-Bernoulli analytical cantilever UDL solution",
        equations=[
            "R_fixed = w * L, M_fixed = -w * L^2 / 2",
            "delta_tip = w * L^4 / (8 * E * I)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, aliases=["L", "length_m"]),
            ParameterConstraint(name="load_kN_per_m", unit="kN/m", dimension="distributed_load", required=True, positive=True, aliases=["w", "udl_kN_per_m"]),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, aliases=["elastic_modulus_GPa", "E_Pa", "E"]),
            ParameterConstraint(name="second_moment_of_area_m4", unit="m4", dimension="second_moment_of_area", required=False, positive=True, aliases=["moment_of_inertia_m4", "I"]),
        ],
        operating_conditions=["Fixed at x=0, free at x=L", "Uniform load over full span"],
        assumptions=["Euler-Bernoulli linear elastic beam theory"],
        limitations=["Small deflection theory"],
        supported_outputs=["fixed_reaction_kN", "fixed_moment_kNm", "tip_deflection_mm"],
        validation_tests=["static_force_equilibrium", "static_moment_equilibrium"],
        visualization_template="beam_deformation",
        aliases=["cantilever_beam", "cantilever_udl"],
    ),
    "truss_analysis": _entry(
        experiment_id="truss_analysis",
        domain="civil",
        solver="truss_matrix_stiffness",
        engine_module="civil_sim",
        method="2D Direct Stiffness Method (Linear Elastic Matrix Structural Analysis)",
        equations=[
            "K_global * u = F",
            "k_local = (E*A/L) * [[c^2, cs, -c^2, -cs], ...]",
            "N_member = (E*A/L) * [-c, -s, c, s] . u_elem",
        ],
        parameter_constraints=[
            ParameterConstraint(name="span_m", unit="m", dimension="length", required=True, positive=True, default=10.0, default_justification="Standard 10 m Pratt bridge truss span", aliases=["L"]),
            ParameterConstraint(name="height_m", unit="m", dimension="length", required=True, positive=True, default=3.0, default_justification="Standard 3 m truss depth"),
            ParameterConstraint(name="panels", value_type="int", required=False, min_value=2, max_value=12, default=4, default_justification="4-panel symmetric Pratt truss"),
            ParameterConstraint(name="point_load_kN", unit="kN", dimension="force", required=True, positive=True, default=20.0, default_justification="20 kN vertical joint load"),
            ParameterConstraint(name="elastic_modulus_Pa", unit="Pa", dimension="stress", required=False, positive=True, default=200e9, default_justification="Structural steel E = 200 GPa", aliases=["elastic_modulus_GPa", "E"]),
            ParameterConstraint(name="member_area_m2", unit="m2", dimension="area", required=False, positive=True, default=0.0025, default_justification="50x50mm solid steel equivalent area 25 cm^2", aliases=["A_m2"]),
        ],
        operating_conditions=["Pin-jointed 2D planar truss", "Loads applied strictly at joints", "Linear elastic small displacements"],
        assumptions=["Frictionless pin joints", "Axial-only member forces", "Buckling of compression members not checked"],
        limitations=["2D linear-elastic static analysis only; no dynamic or nonlinear buckling"],
        supported_outputs=["reaction_A_kN", "reaction_B_kN", "member_forces_kN", "nodal_displacements_mm", "max_stress_MPa", "joint_equilibrium_residual_N"],
        validation_tests=["global_force_equilibrium", "joint_equilibrium_residual"],
        visualization_template="truss_structure",
        aliases=["truss", "pratt_truss", "bridge_truss"],
    ),
    "building_blueprint": _entry(
        experiment_id="building_blueprint",
        domain="civil",
        solver="building_blueprint",
        engine_module="civil_sim",
        method="Geometric architectural floor-plan & preliminary gravity load estimation",
        equations=["A_floor = W * D", "A_total = floors * A_floor"],
        parameter_constraints=[
            ParameterConstraint(name="floors", value_type="int", required=False, min_value=1, max_value=20, default=2, default_justification="2-story reference residential layout"),
            ParameterConstraint(name="width_m", unit="m", dimension="length", required=False, positive=True, default=12.0, default_justification="12 m footprint width"),
            ParameterConstraint(name="depth_m", unit="m", dimension="length", required=False, positive=True, default=8.0, default_justification="8 m footprint depth"),
        ],
        operating_conditions=["Preliminary architectural layout"],
        assumptions=["Simplified uniform live+dead area load of 5 kN/m^2 for preliminary estimation"],
        limitations=["Not a structural finite-element building design"],
        supported_outputs=["floor_area_sqm", "total_built_area_sqm", "column_grid"],
        validation_tests=["area_consistency"],
        visualization_template="building_blueprint",
        aliases=["floor_plan", "architectural_blueprint"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # MECHANICAL ENGINEERING
    # ═══════════════════════════════════════════════════════════════════════════
    "four_bar_linkage": _entry(
        experiment_id="four_bar_linkage",
        domain="mechanical",
        solver="four_bar_kinematics",
        engine_module="mech_sim",
        method="Planar Vector-Loop Closure (Freudenstein / Circle-Circle Intersection) & Velocity Analysis",
        equations=[
            "a*cos(th2) + b*cos(th3) - c*cos(th4) - d = 0",
            "a*sin(th2) + b*sin(th3) - c*sin(th4) = 0",
            "omega3 = -(a*omega2*sin(th2 - th4)) / (b*sin(th3 - th4))",
            "omega4 = (a*omega2*sin(th2 - th3)) / (c*sin(th4 - th3))",
        ],
        parameter_constraints=[
            ParameterConstraint(name="ground_length_m", unit="m", dimension="length", required=True, positive=True, aliases=["ground_length", "d", "L1", "length_d"]),
            ParameterConstraint(name="crank_length_m", unit="m", dimension="length", required=True, positive=True, aliases=["crank_length", "a", "L2", "length_a"]),
            ParameterConstraint(name="coupler_length_m", unit="m", dimension="length", required=True, positive=True, aliases=["coupler_length", "b", "L3", "length_b"]),
            ParameterConstraint(name="rocker_length_m", unit="m", dimension="length", required=True, positive=True, aliases=["rocker_length", "c", "L4", "length_c"]),
            ParameterConstraint(name="input_angle_deg", unit="deg", dimension="angle", required=False, default=45.0, default_justification="Reference starting crank angle 45 deg", aliases=["theta2_deg", "crank_angle_deg"]),
            ParameterConstraint(name="angular_velocity_rad_s", unit="rad/s", dimension="angular_velocity", required=False, default=3.14159265, default_justification="30 RPM (~pi rad/s) steady crank speed", aliases=["omega2", "rpm", "rpm_input"]),
            ParameterConstraint(name="assembly_mode", value_type="str", required=False, default="open", default_justification="Open (non-crossed) kinematic assembly branch"),
            ParameterConstraint(name="motion_direction", value_type="str", required=False, default="ccw", default_justification="Counter-clockwise positive angular rotation"),
        ],
        operating_conditions=["Rigid planar links with ideal revolute joints", "Triangle inequality satisfied at solved angles"],
        assumptions=["Planar rigid-body kinematics; zero joint clearance and link elasticity"],
        limitations=["Pure kinematic (position & velocity) analysis; inertia/joint reaction forces not included"],
        supported_outputs=["grashof_classification", "joint_positions", "angular_positions", "angular_velocities", "closure_residual_m", "transmission_angle_deg"],
        validation_tests=["vector_loop_closure", "link_length_preservation", "grashof_condition"],
        visualization_template="four_bar_linkage",
        aliases=["four_bar", "planar_four_bar", "crank_rocker"],
    ),
    "gear_train": _entry(
        experiment_id="gear_train",
        domain="mechanical",
        solver="gear_train",
        engine_module="mech_sim",
        method="Involute Spur Gear Kinematics, Torque Multiplication & Lewis Bending Stress",
        equations=[
            "i = N_2 / N_1",
            "omega_out = omega_in / i",
            "T_in = P / omega_in; T_out = eta * i * T_in",
            "C = m * (N_1 + N_2) / 2",
        ],
        parameter_constraints=[
            ParameterConstraint(name="teeth_driver", value_type="int", required=True, min_value=6, max_value=300, default=20, default_justification="Standard 20-tooth pinion avoids undercut at 20 deg pressure angle", aliases=["N1", "driver_teeth"]),
            ParameterConstraint(name="teeth_driven", value_type="int", required=True, min_value=6, max_value=500, default=40, default_justification="Standard 40-tooth driven gear (2:1 reduction)", aliases=["N2", "driven_teeth"]),
            ParameterConstraint(name="module_mm", unit="mm", dimension="length", required=False, positive=True, default=2.5, default_justification="ISO metric module 2.5 mm"),
            ParameterConstraint(name="rpm_input", unit="rpm", dimension="angular_velocity", required=False, positive=True, default=1500.0, default_justification="Standard 4-pole AC motor speed 1500 RPM", aliases=["input_rpm"]),
            ParameterConstraint(name="power_kW", unit="kW", dimension="power", required=False, positive=True, default=5.0, default_justification="5 kW mechanical drive rating"),
            ParameterConstraint(name="efficiency", value_type="float", required=False, min_value=0.1, max_value=1.0, default=0.97, default_justification="Typical single-stage spur gear mesh efficiency 97%"),
        ],
        operating_conditions=["Standard full-depth involute spur gears", "Steady-state constant-power transmission"],
        assumptions=["Constant mesh efficiency", "Lewis form factor approximation for tooth root bending"],
        limitations=["Does not include AGMA dynamic/pitting factors or thermal lubrication limits"],
        supported_outputs=["gear_ratio", "rpm_output", "torque_input_Nm", "torque_output_Nm", "centre_distance_mm", "tangential_force_N", "bending_stress_MPa"],
        validation_tests=["gear_ratio_speed_product", "power_balance"],
        visualization_template="gear_train",
        aliases=["spur_gear", "gear", "spur_gear_train"],
    ),
    "shaft_design": _entry(
        experiment_id="shaft_design",
        domain="mechanical",
        solver="shaft_torsion_bending",
        engine_module="mech_sim",
        method="Circular Shaft Torsion & Combined Bending (von Mises Distortion Energy Criterion)",
        equations=[
            "J = pi * d^4 / 32, I = pi * d^4 / 64",
            "tau_max = T * r / J, sigma_b = M * r / I",
            "sigma_vm = sqrt(sigma_b^2 + 3 * tau_max^2)",
            "theta = T * L / (G * J)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="torque_Nm", unit="N*m", dimension="moment", required=True, non_negative=True, default=200.0, default_justification="200 N*m reference drive torque", aliases=["T_Nm", "T"]),
            ParameterConstraint(name="bending_moment_Nm", unit="N*m", dimension="moment", required=False, non_negative=True, default=0.0, default_justification="Pure torsion when bending moment is not specified", aliases=["M_Nm", "M"]),
            ParameterConstraint(name="length_m", unit="m", dimension="length", required=False, positive=True, default=0.5, default_justification="0.5 m shaft span", aliases=["length_mm", "L_m", "L"]),
            ParameterConstraint(name="diameter_mm", unit="mm", dimension="length", required=True, positive=True, default=40.0, default_justification="40 mm solid shaft diameter", aliases=["d_mm", "diameter_m"]),
            ParameterConstraint(name="shear_modulus_GPa", unit="GPa", dimension="stress", required=False, positive=True, default=80.0, default_justification="Steel shear modulus G = 80 GPa", aliases=["G_GPa"]),
            ParameterConstraint(name="yield_strength_MPa", unit="MPa", dimension="stress", required=False, positive=True, default=310.0, default_justification="AISI 1045 normalized steel yield strength", aliases=["Sy_MPa"]),
        ],
        operating_conditions=["Solid circular isotropic shaft", "Linear elastic static loading"],
        assumptions=["Steady static loading; stress concentration factors Kt = 1.0"],
        limitations=["Fatigue/endurance life and keyway stress risers not modeled"],
        supported_outputs=["max_shear_stress_MPa", "max_bending_stress_MPa", "von_mises_stress_MPa", "factor_of_safety", "twist_angle_deg"],
        validation_tests=["torsion_formula_exact", "von_mises_exact"],
        visualization_template="shaft_torsion",
        aliases=["shaft", "shaft_torsion", "torsion"],
    ),
    "spring_mass_damper": _entry(
        experiment_id="spring_mass_damper",
        domain="mechanical",
        solver="spring_mass_damper",
        engine_module="mech_sim",
        method="SciPy RK45 ODE Integration & Exact Analytical Modal Parameters",
        equations=[
            "m * x'' + c * x' + k * x = F(t)",
            "omega_n = sqrt(k / m), zeta = c / (2 * sqrt(k * m))",
        ],
        parameter_constraints=[
            ParameterConstraint(name="mass_kg", unit="kg", dimension="mass", required=True, positive=True, default=1.0, default_justification="1 kg reference mass", aliases=["m"]),
            ParameterConstraint(name="stiffness_N_per_m", unit="N/m", dimension="distributed_load", required=True, positive=True, default=100.0, default_justification="100 N/m coil spring", aliases=["k", "spring_constant"]),
            ParameterConstraint(name="damping_Ns_per_m", unit="N*s/m", required=False, non_negative=True, default=2.0, default_justification="Underdamped viscous damper (zeta=0.1)", aliases=["c", "damping"]),
            ParameterConstraint(name="initial_displacement_m", unit="m", dimension="length", required=False, default=0.1, default_justification="0.1 m initial displacement", aliases=["x0"]),
            ParameterConstraint(name="initial_velocity_ms", unit="m/s", dimension="velocity", required=False, default=0.0, default_justification="Released from rest", aliases=["v0"]),
        ],
        operating_conditions=["Linear Hookean spring", "Linear viscous damper", "1-DOF translation"],
        assumptions=["Constant mass, stiffness, and damping coefficient"],
        limitations=["No nonlinear dry friction or spring saturation"],
        supported_outputs=["natural_frequency_Hz", "damping_ratio", "damped_frequency_Hz", "regime", "peak_displacement_m"],
        validation_tests=["analytical_underdamped_comparison", "energy_dissipation_monotonic"],
        visualization_template="spring_mass_damper",
        aliases=["harmonic_oscillator", "mass_spring_damper", "vibration"],
    ),
    "rotational_dynamics": _entry(
        experiment_id="rotational_dynamics",
        domain="mechanical",
        solver="rotational_dynamics",
        engine_module="mech_sim",
        method="Rigid-Body Rotational Newton-Euler Equation",
        equations=[
            "I * alpha = tau_net - b_rot * omega",
            "K_rot = 0.5 * I * omega^2",
        ],
        parameter_constraints=[
            ParameterConstraint(name="moment_of_inertia_kgm2", unit="kg*m^2", required=True, positive=True, default=0.5, default_justification="0.5 kg*m^2 flywheel", aliases=["I_rot", "inertia"]),
            ParameterConstraint(name="applied_torque_Nm", unit="N*m", dimension="moment", required=True, default=10.0, default_justification="10 N*m constant drive torque", aliases=["torque_Nm"]),
            ParameterConstraint(name="viscous_damping_Nms_rad", unit="N*m*s/rad", required=False, non_negative=True, default=0.2, default_justification="Bearing viscous drag"),
            ParameterConstraint(name="duration_s", unit="s", dimension="time", required=False, positive=True, default=10.0, default_justification="10 s spin-up window"),
        ],
        operating_conditions=["Fixed-axis rigid-body rotation"],
        assumptions=["Constant moment of inertia; linear viscous bearing drag"],
        limitations=["1-DOF fixed-axis rotation only"],
        supported_outputs=["angular_acceleration_rad_s2", "final_angular_velocity_rad_s", "rotational_kinetic_energy_J"],
        validation_tests=["work_energy_theorem"],
        visualization_template="gear_train",
        aliases=["flywheel", "rotational_motion"],
    ),
    "otto_cycle": _entry(
        experiment_id="otto_cycle",
        domain="mechanical",
        solver="otto_cycle",
        engine_module="mech_sim",
        method="Air-Standard Ideal Otto Cycle Thermodynamics",
        equations=[
            "eta_otto = 1 - r^(1 - gamma)",
            "P2 = P1 * r^gamma, T2 = T1 * r^(gamma - 1)",
            "P3 = P2 * (T3 / T2), P4 = P3 / r^gamma",
        ],
        parameter_constraints=[
            ParameterConstraint(name="compression_ratio", value_type="float", required=True, min_value=1.5, max_value=25.0, default=8.0, default_justification="Typical spark-ignition compression ratio r=8", aliases=["r"]),
            ParameterConstraint(name="T_cold_K", unit="K", dimension="temperature", required=False, positive=True, default=300.0, default_justification="Ambient intake 300 K", aliases=["T1_K"]),
            ParameterConstraint(name="T_hot_K", unit="K", dimension="temperature", required=False, positive=True, default=1800.0, default_justification="Peak combustion temperature 1800 K", aliases=["T3_K"]),
            ParameterConstraint(name="gamma", value_type="float", required=False, min_value=1.05, max_value=1.67, default=1.4, default_justification="Diatomic ideal gas (air) gamma=1.4"),
            ParameterConstraint(name="P1_kPa", unit="kPa", dimension="pressure", required=False, positive=True, default=101.325, default_justification="Standard atmospheric intake pressure"),
            ParameterConstraint(name="V1_L", unit="L", dimension="volume", required=False, positive=True, default=0.5, default_justification="0.5 L cylinder displacement"),
        ],
        operating_conditions=["Ideal air-standard cold assumptions", "Constant specific heats"],
        assumptions=["Reversible adiabatic compression/expansion", "Isochoric heat addition/rejection"],
        limitations=["Idealized cycle; ignores combustion kinetics, heat loss, and pumping work"],
        supported_outputs=["efficiency_percent", "net_work_kJ", "mean_effective_pressure_kPa", "state_points"],
        validation_tests=["first_law_work_heat_balance", "otto_efficiency_exact"],
        visualization_template="thermo_cycle",
        aliases=["thermo_cycle"],
    ),
    "carnot_cycle": _entry(
        experiment_id="carnot_cycle",
        domain="mechanical",
        solver="carnot_cycle",
        engine_module="mech_sim",
        method="Ideal Reversible Carnot Cycle (2 Isotherms + 2 Adiabats)",
        equations=[
            "eta_carnot = 1 - T_cold / T_hot",
            "Isothermal P*V = const; Adiabatic P*V^gamma = const",
        ],
        parameter_constraints=[
            ParameterConstraint(name="T_hot_K", unit="K", dimension="temperature", required=True, positive=True, default=800.0, default_justification="Hot reservoir 800 K"),
            ParameterConstraint(name="T_cold_K", unit="K", dimension="temperature", required=True, positive=True, default=300.0, default_justification="Cold reservoir 300 K"),
            ParameterConstraint(name="isothermal_expansion_ratio", value_type="float", required=False, min_value=1.1, max_value=20.0, default=2.0, default_justification="V2/V1 = 2.0 isothermal expansion"),
            ParameterConstraint(name="gamma", value_type="float", required=False, min_value=1.05, max_value=1.67, default=1.4, default_justification="Ideal diatomic gas gamma=1.4"),
        ],
        operating_conditions=["T_hot_K > T_cold_K > 0", "Reversible ideal gas"],
        assumptions=["Zero entropy generation (ideal theoretical upper bound)"],
        limitations=["Theoretical limit; cannot be achieved in real heat engines"],
        supported_outputs=["efficiency_percent", "heat_in_kJ", "heat_out_kJ", "net_work_kJ", "state_points"],
        validation_tests=["carnot_efficiency_exact", "zero_net_entropy_change"],
        visualization_template="thermo_cycle",
        aliases=["carnot"],
    ),
    "diesel_cycle": _entry(
        experiment_id="diesel_cycle",
        domain="mechanical",
        solver="diesel_cycle",
        engine_module="mech_sim",
        method="Air-Standard Ideal Diesel Cycle (Constant-Pressure Heat Addition)",
        equations=[
            "eta_diesel = 1 - (1 / r^(gamma-1)) * ((r_c^gamma - 1) / (gamma * (r_c - 1)))",
        ],
        parameter_constraints=[
            ParameterConstraint(name="compression_ratio", value_type="float", required=True, min_value=5.0, max_value=30.0, default=18.0, default_justification="Typical compression-ignition ratio r=18"),
            ParameterConstraint(name="cutoff_ratio", value_type="float", required=False, min_value=1.1, max_value=6.0, default=2.0, default_justification="Standard fuel cutoff ratio r_c=2.0"),
            ParameterConstraint(name="T_cold_K", unit="K", dimension="temperature", required=False, positive=True, default=300.0, default_justification="Ambient intake 300 K"),
            ParameterConstraint(name="gamma", value_type="float", required=False, min_value=1.05, max_value=1.67, default=1.4, default_justification="Air gamma=1.4"),
        ],
        operating_conditions=["Air-standard ideal gas", "r > cutoff_ratio > 1"],
        assumptions=["Isobaric heat addition, isochoric heat rejection"],
        limitations=["Ideal cold air-standard approximation"],
        supported_outputs=["efficiency_percent", "net_work_kJ", "state_points"],
        validation_tests=["diesel_efficiency_exact"],
        visualization_template="thermo_cycle",
        aliases=["diesel"],
    ),
    "brayton_cycle": _entry(
        experiment_id="brayton_cycle",
        domain="mechanical",
        solver="brayton_cycle",
        engine_module="mech_sim",
        method="Air-Standard Ideal Brayton Gas-Turbine Cycle",
        equations=["eta_brayton = 1 - r_p^((1 - gamma) / gamma)"],
        parameter_constraints=[
            ParameterConstraint(name="pressure_ratio", value_type="float", required=True, min_value=1.5, max_value=50.0, default=10.0, default_justification="Gas turbine pressure ratio r_p=10"),
            ParameterConstraint(name="T_cold_K", unit="K", dimension="temperature", required=False, positive=True, default=300.0, default_justification="Compressor inlet 300 K"),
            ParameterConstraint(name="T_hot_K", unit="K", dimension="temperature", required=False, positive=True, default=1400.0, default_justification="Turbine inlet 1400 K"),
            ParameterConstraint(name="gamma", value_type="float", required=False, min_value=1.05, max_value=1.67, default=1.4, default_justification="Air gamma=1.4"),
        ],
        operating_conditions=["Ideal closed gas turbine cycle"],
        assumptions=["Isentropic compressor & turbine; constant-pressure heat exchangers"],
        limitations=["Ignores compressor/turbine isentropic inefficiencies"],
        supported_outputs=["efficiency_percent", "back_work_ratio", "net_work_kJ_per_kg"],
        validation_tests=["brayton_efficiency_exact"],
        visualization_template="thermo_cycle",
        aliases=["brayton", "gas_turbine"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # PHYSICS
    # ═══════════════════════════════════════════════════════════════════════════
    "pendulum": _entry(
        experiment_id="pendulum",
        domain="physics",
        solver="pendulum",
        engine_module="physics_sim",
        method="SciPy RK45 Nonlinear/Damped/Driven Pendulum ODE with Analytical Comparison",
        equations=[
            "Nonlinear: theta'' + (b/m)*theta' + (g/L)*sin(theta) = (A_drive/(m*L))*cos(omega_d*t)",
            "Small-angle: T_0 = 2*pi*sqrt(L/g)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="length_m", unit="m", dimension="length", required=True, positive=True, default=1.0, default_justification="1 m reference pendulum length", aliases=["L"]),
            ParameterConstraint(name="gravity", unit="m/s^2", required=False, positive=True, default=9.81, default_justification="Standard Earth gravity 9.81 m/s^2", aliases=["g"]),
            ParameterConstraint(name="angle_rad", unit="rad", dimension="angle", required=False, default=0.5, default_justification="0.5 rad (~28.6 deg) release angle", aliases=["theta0_rad", "angle_deg"]),
            ParameterConstraint(name="damping", unit="kg/s", required=False, non_negative=True, default=0.0, default_justification="Undamped baseline unless damping is specified", aliases=["b"]),
            ParameterConstraint(name="bob_mass_kg", unit="kg", dimension="mass", required=False, positive=True, default=0.5, default_justification="0.5 kg pendulum bob", aliases=["mass_kg", "m"]),
            ParameterConstraint(name="model_mode", value_type="str", required=False, default="nonlinear", default_justification="Full nonlinear sin(theta) model by default"),
            ParameterConstraint(name="drive_amplitude", value_type="float", required=False, non_negative=True, default=0.0, default_justification="Unforced unless driven amplitude provided"),
            ParameterConstraint(name="drive_frequency_rad_s", unit="rad/s", dimension="angular_velocity", required=False, positive=True, default=2.0, default_justification="Default driving frequency when driven"),
        ],
        operating_conditions=["Point mass on massless rigid rod", "Planar swing"],
        assumptions=["Small-angle mode explicitly restricted to |theta| < 0.25 rad (~14 deg)"],
        limitations=["Ignores air drag nonlinearity (quadratic drag) and pivot friction"],
        supported_outputs=["natural_period_s", "numerical_period_s", "initial_energy_J", "final_energy_J", "energy_conservation_error_pct"],
        validation_tests=["energy_conservation_undamped", "small_angle_period_convergence", "tolerance_convergence"],
        visualization_template="simple_pendulum",
        aliases=["simple_pendulum", "damped_pendulum", "nonlinear_pendulum", "driven_pendulum"],
    ),
    "projectile_motion": _entry(
        experiment_id="projectile_motion",
        domain="physics",
        solver="projectile",
        engine_module="physics_sim",
        method="Analytical Ballistic Kinematics (Vacuum) or RK45 ODE (Quadratic Air Drag)",
        equations=[
            "Vacuum: x(t) = v0*cos(th)*t, y(t) = y0 + v0*sin(th)*t - 0.5*g*t^2",
            "Drag: m*dv/dt = m*g - 0.5*rho*Cd*A*|v|*v",
        ],
        parameter_constraints=[
            ParameterConstraint(name="initial_velocity_ms", unit="m/s", dimension="velocity", required=True, positive=True, default=20.0, default_justification="20 m/s launch speed", aliases=["v0", "velocity_ms"]),
            ParameterConstraint(name="launch_angle_deg", unit="deg", dimension="angle", required=True, min_value=0.0, max_value=90.0, default=45.0, default_justification="45 deg optimal vacuum launch angle", aliases=["angle_deg"]),
            ParameterConstraint(name="gravity", unit="m/s^2", required=False, positive=True, default=9.81, default_justification="Standard gravity 9.81 m/s^2", aliases=["g"]),
            ParameterConstraint(name="mass_kg", unit="kg", dimension="mass", required=False, positive=True, default=1.0, default_justification="1 kg projectile mass"),
            ParameterConstraint(name="drag_coeff", value_type="float", required=False, non_negative=True, default=0.0, default_justification="Zero air resistance unless drag requested", aliases=["Cd"]),
            ParameterConstraint(name="cross_section_m2", unit="m2", dimension="area", required=False, positive=True, default=0.01, default_justification="0.01 m^2 reference cross-section for drag"),
        ],
        operating_conditions=["Uniform gravitational field", "Flat ground at y=0"],
        assumptions=["Vacuum (no air resistance) when drag_coeff == 0; quadratic aerodynamic drag when drag_coeff > 0"],
        limitations=["Coriolis effect, wind, and Magnus spin lift neglected"],
        supported_outputs=["max_range_m", "max_height_m", "flight_time_s", "impact_speed_ms", "air_resistance_included"],
        validation_tests=["energy_conservation_vacuum", "analytical_range_height_exact"],
        visualization_template="projectile_motion",
        aliases=["projectile", "ballistic_trajectory"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # ELECTRICAL & ELECTRONICS
    # ═══════════════════════════════════════════════════════════════════════════
    "ohms_law": _entry(
        experiment_id="ohms_law",
        domain="electronics",
        solver="ohms_law",
        engine_module="electronics_sim",
        method="Linear Resistive Circuit Law (I = V/R, P = V*I)",
        equations=["I = V / R", "P = V * I = I^2 * R = V^2 / R"],
        parameter_constraints=[
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=1000.0, default_justification="1 kOhm standard laboratory resistor", aliases=["R", "R_ohm"]),
            ParameterConstraint(name="supply_voltage_V", unit="V", dimension="voltage", required=True, non_negative=True, default=10.0, default_justification="10 V DC bench supply", aliases=["voltage_max", "V", "V0"]),
            ParameterConstraint(name="voltage_min", unit="V", dimension="voltage", required=False, non_negative=True, default=0.0, default_justification="0 V sweep start"),
        ],
        operating_conditions=["Ideal linear ohmic resistor", "DC steady state"],
        assumptions=["Constant resistance independent of temperature"],
        limitations=["Ignores thermal self-heating and power rating failure"],
        supported_outputs=["resistance_ohm", "conductance_S", "max_current_mA", "max_power_mW", "power_balance_error_W"],
        validation_tests=["ohms_law_exact", "power_conservation"],
        visualization_template="ohms_law_circuit",
        aliases=["ohm", "iv_curve"],
    ),
    "series_parallel_circuit": _entry(
        experiment_id="series_parallel_circuit",
        domain="electronics",
        solver="series_parallel_circuit",
        engine_module="electronics_sim",
        method="Exact Series/Parallel Equivalent Resistance & Branch KCL/KVL Analysis",
        equations=["R_series = sum(R_i)", "1/R_parallel = sum(1/R_i)", "sum(I_branch) = I_total"],
        parameter_constraints=[
            ParameterConstraint(name="supply_voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=12.0, default_justification="12 V DC supply", aliases=["V", "V0"]),
            ParameterConstraint(name="resistors_ohm", value_type="list", required=False, default=[100.0, 200.0, 300.0], default_justification="Three reference resistors [100, 200, 300] Ohm"),
            ParameterConstraint(name="topology", value_type="str", required=False, default="parallel", default_justification="Parallel or series network"),
        ],
        operating_conditions=["Linear resistive DC network"],
        assumptions=["Ideal voltage source and ideal conductors"],
        limitations=["Purely resistive DC steady state"],
        supported_outputs=["equivalent_resistance_ohm", "total_current_A", "branch_currents_A", "branch_voltages_V", "kcl_residual_A", "kvl_residual_V", "power_balance_residual_W"],
        validation_tests=["kcl_exact", "kvl_exact", "power_balance"],
        visualization_template="ohms_law_circuit",
        aliases=["series_circuit", "parallel_circuit", "resistor_network"],
    ),
    "voltage_divider": _entry(
        experiment_id="voltage_divider",
        domain="electronics",
        solver="voltage_divider",
        engine_module="electronics_sim",
        method="Resistive Voltage Divider with KVL & Power Verification",
        equations=["V_out = V_in * R_2 / (R_1 + R_2)", "I = V_in / (R_1 + R_2)"],
        parameter_constraints=[
            ParameterConstraint(name="supply_voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=5.0, default_justification="5 V logic rail", aliases=["V_in", "V"]),
            ParameterConstraint(name="r1_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=1000.0, default_justification="1 kOhm top resistor", aliases=["R1"]),
            ParameterConstraint(name="r2_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=1000.0, default_justification="1 kOhm bottom resistor", aliases=["R2"]),
        ],
        operating_conditions=["Unloaded (open-circuit) output node", "DC steady state"],
        assumptions=["Infinite output load impedance"],
        limitations=["Output loading shifts V_out if finite R_load is attached"],
        supported_outputs=["Vout_V", "current_mA", "division_ratio", "kvl_residual_V"],
        validation_tests=["kvl_exact", "power_balance"],
        visualization_template="voltage_divider_circuit",
        aliases=[],
    ),
    "current_divider": _entry(
        experiment_id="current_divider",
        domain="electronics",
        solver="current_divider",
        engine_module="electronics_sim",
        method="Parallel Resistive Current Divider with KCL Verification",
        equations=["I_1 = I_total * R_2 / (R_1 + R_2)", "I_2 = I_total * R_1 / (R_1 + R_2)"],
        parameter_constraints=[
            ParameterConstraint(name="total_current_A", unit="A", dimension="current", required=True, positive=True, default=0.1, default_justification="0.1 A source current", aliases=["I_total", "I"]),
            ParameterConstraint(name="r1_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=100.0, default_justification="100 Ohm branch 1", aliases=["R1"]),
            ParameterConstraint(name="r2_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=300.0, default_justification="300 Ohm branch 2", aliases=["R2"]),
        ],
        operating_conditions=["Two parallel resistive branches"],
        assumptions=["Ideal current source"],
        limitations=["Two-branch DC steady state"],
        supported_outputs=["I1_A", "I2_A", "node_voltage_V", "kcl_residual_A"],
        validation_tests=["kcl_exact", "power_balance"],
        visualization_template="ohms_law_circuit",
        aliases=[],
    ),
    "rc_circuit": _entry(
        experiment_id="rc_circuit",
        domain="electronics",
        solver="rc_transient",
        engine_module="electronics_sim",
        method="First-Order RC Step-Response Analytical & ODE Solution",
        equations=["tau = R * C", "V_C(t) = V_0 * (1 - exp(-t / tau))", "I(t) = (V_0 / R) * exp(-t / tau)"],
        parameter_constraints=[
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=1000.0, default_justification="1 kOhm resistor", aliases=["R"]),
            ParameterConstraint(name="capacitance_F", unit="F", dimension="capacitance", required=True, positive=True, default=1e-4, default_justification="100 uF capacitor", aliases=["C"]),
            ParameterConstraint(name="voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=5.0, default_justification="5 V step input", aliases=["supply_voltage_V", "V0"]),
        ],
        operating_conditions=["Initially uncharged capacitor V_C(0) = 0"],
        assumptions=["Ideal linear R and C components"],
        limitations=["Ignores capacitor ESR and leakage resistance"],
        supported_outputs=["time_constant_s", "steady_state_V", "initial_current_mA", "stored_energy_mJ", "kvl_max_residual_V"],
        validation_tests=["kvl_exact", "rc_analytical_tau"],
        visualization_template="rlc_circuit",
        aliases=["rc_charging", "rc_transient"],
    ),
    "rl_circuit": _entry(
        experiment_id="rl_circuit",
        domain="electronics",
        solver="rl_transient",
        engine_module="electronics_sim",
        method="First-Order RL Step-Response Analytical Solution",
        equations=["tau = L / R", "I(t) = (V_0 / R) * (1 - exp(-t / tau))", "V_L(t) = V_0 * exp(-t / tau)"],
        parameter_constraints=[
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=10.0, default_justification="10 Ohm resistor", aliases=["R"]),
            ParameterConstraint(name="inductance_H", unit="H", dimension="inductance", required=True, positive=True, default=0.1, default_justification="100 mH inductor", aliases=["L"]),
            ParameterConstraint(name="voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=5.0, default_justification="5 V step input", aliases=["supply_voltage_V", "V0"]),
        ],
        operating_conditions=["Zero initial inductor current I(0) = 0"],
        assumptions=["Ideal linear R and L"],
        limitations=["Ignores core saturation and winding capacitance"],
        supported_outputs=["time_constant_s", "steady_state_current_A", "stored_energy_mJ", "kvl_max_residual_V"],
        validation_tests=["kvl_exact", "rl_analytical_tau"],
        visualization_template="rlc_circuit",
        aliases=["rl_transient"],
    ),
    "series_rlc": _entry(
        experiment_id="series_rlc",
        domain="electronics",
        solver="rlc_series",
        engine_module="electronics_sim",
        method="Series RLC Second-Order ODE (RK45 rtol=1e-9) + Analytical Resonance & KVL Verification",
        equations=[
            "L * d^2q/dt^2 + R * dq/dt + q / C = V_0",
            "f_0 = 1 / (2*pi*sqrt(L*C)), zeta = R / (2*sqrt(L/C))",
            "KVL: V_R(t) + V_L(t) + V_C(t) = V_0",
        ],
        parameter_constraints=[
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=10.0, default_justification="10 Ohm series resistance", aliases=["R"]),
            ParameterConstraint(name="inductance_H", unit="H", dimension="inductance", required=True, positive=True, default=0.1, default_justification="0.1 H inductor", aliases=["L"]),
            ParameterConstraint(name="capacitance_F", unit="F", dimension="capacitance", required=True, positive=True, default=0.001, default_justification="1 mF capacitor", aliases=["C"]),
            ParameterConstraint(name="voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=5.0, default_justification="5 V step source", aliases=["supply_voltage_V", "V0"]),
        ],
        operating_conditions=["Zero initial state q(0)=0, i(0)=0", "Step voltage excitation V_0"],
        assumptions=["Linear time-invariant passive components"],
        limitations=["Ignores parasitic capacitance and core nonlinearity"],
        supported_outputs=["resonant_frequency_Hz", "damping_ratio_zeta", "quality_factor_Q", "peak_current_A", "steady_state_cap_V", "kvl_max_residual_V", "response_type"],
        validation_tests=["kvl_exact", "rlc_resonant_frequency_exact", "tolerance_convergence"],
        visualization_template="rlc_circuit",
        aliases=["rlc_circuit", "rlc", "physics_rlc"],
    ),
    "ac_circuit": _entry(
        experiment_id="ac_circuit",
        domain="electronics",
        solver="ac_phasor_circuit",
        engine_module="electronics_sim",
        method="Steady-State Sinusoidal Phasor Impedance Analysis",
        equations=["Z = R + j*(omega*L - 1/(omega*C))", "I_rms = V_rms / |Z|", "PF = cos(phi)"],
        parameter_constraints=[
            ParameterConstraint(name="voltage_rms_V", unit="V", dimension="voltage", required=True, positive=True, default=120.0, default_justification="120 V RMS AC source", aliases=["V_rms", "voltage_V"]),
            ParameterConstraint(name="frequency_Hz", unit="Hz", dimension="frequency", required=True, positive=True, default=60.0, default_justification="60 Hz AC mains frequency", aliases=["f_Hz", "freq"]),
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=True, positive=True, default=50.0, default_justification="50 Ohm load resistance", aliases=["R"]),
            ParameterConstraint(name="inductance_H", unit="H", dimension="inductance", required=False, non_negative=True, default=0.1, default_justification="0.1 H inductance", aliases=["L"]),
            ParameterConstraint(name="capacitance_F", unit="F", dimension="capacitance", required=False, positive=True, default=1e-4, default_justification="100 uF capacitance", aliases=["C"]),
        ],
        operating_conditions=["Sinusoidal steady state"],
        assumptions=["Pure single-frequency sinusoid; linear components"],
        limitations=["Does not include harmonics or turn-on transient"],
        supported_outputs=["impedance_mag_ohm", "phase_angle_deg", "current_rms_A", "power_factor", "real_power_W", "reactive_power_VAR", "apparent_power_VA"],
        validation_tests=["apparent_power_triangle"],
        visualization_template="rlc_circuit",
        aliases=["ac_impedance", "phasor_circuit"],
    ),
    "transformer": _entry(
        experiment_id="transformer",
        domain="electronics",
        solver="ideal_transformer",
        engine_module="electronics_sim",
        method="Ideal Coupled-Magnetic Transformer Turns-Ratio Law",
        equations=["V_s / V_p = N_s / N_p", "I_p / I_s = N_s / N_p", "P_p = P_s"],
        parameter_constraints=[
            ParameterConstraint(name="primary_voltage_V", unit="V", dimension="voltage", required=True, positive=True, default=240.0, default_justification="240 V primary", aliases=["Vp"]),
            ParameterConstraint(name="turns_primary", value_type="int", required=True, min_value=1, default=400, default_justification="400 primary turns", aliases=["Np"]),
            ParameterConstraint(name="turns_secondary", value_type="int", required=True, min_value=1, default=100, default_justification="100 secondary turns", aliases=["Ns"]),
            ParameterConstraint(name="load_resistance_ohm", unit="ohm", dimension="resistance", required=False, positive=True, default=12.0, default_justification="12 Ohm resistive load", aliases=["R_load"]),
        ],
        operating_conditions=["Ideal lossless magnetic coupling k=1"],
        assumptions=["Zero winding resistance, zero core loss, infinite magnetizing inductance"],
        limitations=["Real transformer efficiency, hysteresis, and eddy losses omitted"],
        supported_outputs=["turns_ratio", "secondary_voltage_V", "secondary_current_A", "primary_current_A", "power_W", "power_balance_error_W"],
        validation_tests=["transformer_power_conservation"],
        visualization_template="rlc_circuit",
        aliases=["ideal_transformer"],
    ),
    "arduino_led": _entry(
        experiment_id="arduino_led",
        domain="electronics",
        solver="arduino_led",
        engine_module="electronics_sim",
        method="DC LED Forward-Drop Limiting Resistor & Square-Wave Drive",
        equations=["R = (V_supply - V_f) / I_LED", "P_R = I_LED^2 * R"],
        parameter_constraints=[
            ParameterConstraint(name="supply_voltage_V", unit="V", dimension="voltage", required=False, positive=True, default=5.0, default_justification="Arduino Uno 5 V digital output"),
            ParameterConstraint(name="led_forward_voltage_V", unit="V", dimension="voltage", required=False, positive=True, default=2.0, default_justification="Standard red LED Vf = 2.0 V", aliases=["led_vf"]),
            ParameterConstraint(name="led_current_mA", unit="mA", dimension="current", required=False, positive=True, default=20.0, default_justification="20 mA nominal LED current"),
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=False, positive=True),
            ParameterConstraint(name="blink_frequency_Hz", unit="Hz", dimension="frequency", required=False, positive=True, default=1.0, default_justification="1 Hz standard blink"),
        ],
        operating_conditions=["V_supply > V_f"],
        assumptions=["Piecewise-constant LED forward voltage drop"],
        limitations=["Ideal digital pin output impedance ignored"],
        supported_outputs=["resistor_value_ohm", "led_current_mA", "power_resistor_mW", "kvl_residual_V"],
        validation_tests=["kvl_exact"],
        visualization_template="arduino_circuit",
        aliases=["arduino", "arduino_blink", "blink"],
    ),
    "led_resistor": _entry(
        experiment_id="led_resistor",
        domain="electronics",
        solver="led_resistor",
        engine_module="electronics_sim",
        method="Series Battery-Resistor-LED Kirchhoff Loop",
        equations=["I = (V_supply - V_f) / R", "V_R = I * R"],
        parameter_constraints=[
            ParameterConstraint(name="supply_voltage_V", unit="V", dimension="voltage", required=False, positive=True, default=9.0, default_justification="9 V battery supply"),
            ParameterConstraint(name="led_forward_voltage_V", unit="V", dimension="voltage", required=False, positive=True, default=2.0, default_justification="2 V red LED forward drop", aliases=["led_vf"]),
            ParameterConstraint(name="resistance_ohm", unit="ohm", dimension="resistance", required=False, positive=True, default=470.0, default_justification="470 Ohm standard resistor"),
        ],
        operating_conditions=["V_supply > V_f"],
        assumptions=["Constant forward voltage model"],
        limitations=["Shockley exponential diode curve approximated by fixed Vf"],
        supported_outputs=["current_mA", "voltage_across_resistor_V", "power_resistor_mW", "kvl_residual_V"],
        validation_tests=["kvl_exact"],
        visualization_template="arduino_circuit",
        aliases=[],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # CHEMISTRY
    # ═══════════════════════════════════════════════════════════════════════════
    "acid_base_titration": _entry(
        experiment_id="acid_base_titration",
        domain="chemistry",
        solver="acid_base_titration",
        engine_module="chem_sim",
        method="Exact Charge-Balance & Water-Autoprotolysis Cubic Equilibrium Solver (All 4 Regimes)",
        equations=[
            "[H+]^3 + (Ka + Cb_eff)*[H+]^2 + (Ka*(Cb_eff - Ca_eff) - Kw)*[H+] - Ka*Kw = 0",
            "V_eq = (Ca * Va) / Cb",
            "pH = -log10([H+])",
        ],
        parameter_constraints=[
            ParameterConstraint(name="acid_concentration_M", unit="M", dimension="concentration", required=True, positive=True, default=0.1, default_justification="Standard 0.1 M monoprotic weak acid", aliases=["Ca", "acid_M", "initial_concentration_M"]),
            ParameterConstraint(name="acid_volume_mL", unit="mL", dimension="volume", required=True, positive=True, default=25.0, default_justification="Standard 25.0 mL analyte aliquot", aliases=["Va", "Va_mL"]),
            ParameterConstraint(name="base_concentration_M", unit="M", dimension="concentration", required=True, positive=True, default=0.1, default_justification="Standard 0.1 M NaOH titrant", aliases=["Cb", "base_M"]),
            ParameterConstraint(name="pKa", value_type="float", required=False, min_value=-2.0, max_value=14.0, default=4.756, default_justification="Acetic acid pKa = 4.756 at 298.15 K", aliases=["pka"]),
            ParameterConstraint(name="Ka", value_type="float", required=False, positive=True),
            ParameterConstraint(name="max_base_volume_mL", unit="mL", dimension="volume", required=False, positive=True, default=50.0, default_justification="50 mL standard burette capacity"),
            ParameterConstraint(name="strong_acid", value_type="bool", required=False, default=False, default_justification="Weak acid titrated with strong base by default"),
        ],
        operating_conditions=["Monoprotic acid titrated with strong monoprotic base (NaOH) at 298.15 K", "Kw = 1.0e-14"],
        assumptions=["Ideal dilute solution (activity coefficients = 1)", "Isothermal T = 298.15 K", "Additive volumes"],
        limitations=["Debye-Huckel ionic strength corrections and polyprotic species not included"],
        supported_outputs=["initial_pH", "half_equivalence_pH", "equivalence_volume_mL", "equivalence_pH", "final_pH", "titration_curve"],
        validation_tests=["acetic_acid_benchmark_4_regimes", "charge_balance_residual"],
        visualization_template="titration_apparatus",
        aliases=["titration", "weak_acid_titration", "ph_titration"],
    ),
    "reaction_kinetics": _entry(
        experiment_id="reaction_kinetics",
        domain="chemistry",
        solver="reaction_kinetics",
        engine_module="chem_sim",
        method="Arrhenius Rate Law & 0th/1st/2nd Order ODE Integration with Analytical Verification",
        equations=[
            "k(T) = A * exp(-Ea / (R * T))",
            "1st order: d[A]/dt = -k*[A], [A](t) = [A]_0 * exp(-k*t), t_1/2 = ln(2)/k",
            "2nd order: d[A]/dt = -k*[A]^2, t_1/2 = 1/(k*[A]_0)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="temperature_K", unit="K", dimension="temperature", required=True, positive=True, default=298.15, default_justification="Standard laboratory temperature 298.15 K", aliases=["T"]),
            ParameterConstraint(name="activation_energy_kJ", unit="kJ", dimension="energy", required=False, positive=True, default=50.0, default_justification="50 kJ/mol typical activation barrier", aliases=["Ea_kJ"]),
            ParameterConstraint(name="pre_exponential_factor", value_type="float", required=False, positive=True, default=1e7, default_justification="Arrhenius frequency factor A = 1e7 s^-1", aliases=["A"]),
            ParameterConstraint(name="initial_concentration_M", unit="M", dimension="concentration", required=True, positive=True, default=1.0, default_justification="1.0 M initial reactant", aliases=["C0"]),
            ParameterConstraint(name="reaction_time_s", unit="s", dimension="time", required=False, positive=True, default=120.0, default_justification="120 s observation window", aliases=["t_end"]),
            ParameterConstraint(name="reaction_order", value_type="int", required=False, min_value=0, max_value=2, default=1, default_justification="First-order unimolecular reaction"),
        ],
        operating_conditions=["Isothermal well-mixed batch reactor", "Irreversible A -> P"],
        assumptions=["Ideal solution; constant temperature; no reverse reaction"],
        limitations=["Complex multi-step mechanisms require coupled ODE networks"],
        supported_outputs=["rate_constant_k", "half_life_s", "final_concentration_M", "conversion_percent", "mass_balance_error_M"],
        validation_tests=["mass_balance_A_plus_P", "analytical_first_order_match"],
        visualization_template="reaction_kinetics",
        aliases=["kinetics", "arrhenius", "reaction_rate"],
    ),
    "chemical_equilibrium": _entry(
        experiment_id="chemical_equilibrium",
        domain="chemistry",
        solver="chemical_equilibrium",
        engine_module="chem_sim",
        method="Exact Law of Mass Action ICE Solver (A + B <-> C + D or A <-> B)",
        equations=["K_eq = ([C]*[D]) / ([A]*[B])", "Mass balance: [A] + [C] = [A]_0 + [C]_0"],
        parameter_constraints=[
            ParameterConstraint(name="K_eq", value_type="float", required=True, positive=True, default=4.0, default_justification="Reference equilibrium constant K_eq=4.0", aliases=["Keq"]),
            ParameterConstraint(name="A0_M", unit="M", dimension="concentration", required=True, non_negative=True, default=1.0, default_justification="1.0 M initial [A]"),
            ParameterConstraint(name="B0_M", unit="M", dimension="concentration", required=False, non_negative=True, default=1.0, default_justification="1.0 M initial [B]"),
            ParameterConstraint(name="C0_M", unit="M", dimension="concentration", required=False, non_negative=True, default=0.0, default_justification="0.0 M initial [C]"),
            ParameterConstraint(name="D0_M", unit="M", dimension="concentration", required=False, non_negative=True, default=0.0, default_justification="0.0 M initial [D]"),
        ],
        operating_conditions=["Isothermal homogeneous reversible reaction A + B <-> C + D"],
        assumptions=["Ideal activities equal molar concentrations"],
        limitations=["Single equilibrium reaction; no activity coefficients"],
        supported_outputs=["extent_M", "eq_A_M", "eq_B_M", "eq_C_M", "eq_D_M", "reaction_quotient_Q", "mass_balance_error_M"],
        validation_tests=["mass_action_Q_equals_K", "mass_balance_exact"],
        visualization_template="reaction_kinetics",
        aliases=["equilibrium", "ice_table"],
    ),
    "chemical_thermodynamics": _entry(
        experiment_id="chemical_thermodynamics",
        domain="chemistry",
        solver="chemical_thermodynamics",
        engine_module="chem_sim",
        method="Gibbs Free Energy & van 't Hoff Temperature Dependence",
        equations=["Delta_G = Delta_H - T * Delta_S", "K_eq(T) = exp(-Delta_G / (R * T))"],
        parameter_constraints=[
            ParameterConstraint(name="delta_H_kJ_mol", unit="kJ", dimension="energy", required=True, default=-45.0, default_justification="Exothermic reference enthalpy -45 kJ/mol"),
            ParameterConstraint(name="delta_S_J_mol_K", unit="J/(mol*K)", required=True, default=-100.0, default_justification="Entropy change -100 J/(mol*K)"),
            ParameterConstraint(name="temperature_K", unit="K", dimension="temperature", required=False, positive=True, default=298.15, default_justification="Standard 298.15 K", aliases=["T"]),
        ],
        operating_conditions=["Constant Delta_H and Delta_S over temperature range (Ellingham approximation)"],
        assumptions=["Heat capacity difference Delta_Cp = 0"],
        limitations=["Kirchhoff heat-capacity temperature corrections omitted"],
        supported_outputs=["delta_G_kJ_mol", "equilibrium_constant_K", "crossover_temperature_K", "spontaneous"],
        validation_tests=["gibbs_identity_exact"],
        visualization_template="reaction_kinetics",
        aliases=["thermodynamics", "gibbs_free_energy"],
    ),
    "molecular_properties": _entry(
        experiment_id="molecular_properties",
        domain="chemistry",
        solver="molecular_properties",
        engine_module="chem_sim",
        method="Molecular Formula / RDKit Descriptor & 3D Geometry Catalogue",
        equations=["MW = sum(n_i * m_i)"],
        parameter_constraints=[
            ParameterConstraint(name="molecule_name", value_type="str", required=False, default="water", default_justification="Default reference molecule H2O"),
            ParameterConstraint(name="smiles", value_type="str", required=False),
        ],
        operating_conditions=["Supported catalog molecules or valid SMILES when RDKit is installed"],
        assumptions=["Gas-phase reference equilibrium bond lengths and angles"],
        limitations=["Requires RDKit for arbitrary SMILES descriptors"],
        supported_outputs=["molecular_weight_g_mol", "formula", "bond_angle_deg", "bond_length_A"],
        validation_tests=["molecular_weight_exact"],
        visualization_template="molecular_geometry",
        aliases=["molecule", "molecular_geometry"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # BIOLOGY
    # ═══════════════════════════════════════════════════════════════════════════
    "michaelis_menten": _entry(
        experiment_id="michaelis_menten",
        domain="biology",
        solver="michaelis_menten",
        engine_module="bio_sim",
        method="Exact Michaelis-Menten Steady-State Enzyme Kinetics & Inhibition Models",
        equations=[
            "v = (V_max * [S]) / (K_m + [S])",
            "Competitive: K_m_app = K_m * (1 + [I]/K_i)",
            "Non-competitive: V_max_app = V_max / (1 + [I]/K_i)",
        ],
        parameter_constraints=[
            ParameterConstraint(name="Vmax", unit="uM/min", required=True, positive=True, default=100.0, default_justification="Reference maximum velocity 100 uM/min", aliases=["v_max", "V_max", "max_velocity"]),
            ParameterConstraint(name="Km", unit="uM", dimension="concentration", required=True, positive=True, default=5.0, default_justification="Reference Michaelis constant 5.0 uM", aliases=["K_m", "michaelis_constant"]),
            ParameterConstraint(name="Ki", unit="uM", dimension="concentration", required=False, positive=True, default=2.5, default_justification="Reference inhibition constant 2.5 uM", aliases=["K_i", "inhibition_constant"]),
            ParameterConstraint(name="inhibitor_conc", unit="uM", dimension="concentration", required=False, non_negative=True, default=0.0, default_justification="Uninhibited baseline unless inhibitor specified", aliases=["I", "inhibitor_conc_uM"]),
            ParameterConstraint(name="substrate_max", unit="uM", dimension="concentration", required=False, positive=True, default=60.0, default_justification="Substrate sweep upper bound"),
            ParameterConstraint(name="inhibition_type", value_type="str", required=False, default="non_competitive", default_justification="Non-competitive or competitive inhibition"),
        ],
        operating_conditions=["Quasi-steady-state assumption ([S] >> [E]_0)", "Initial reaction velocity (no product inhibition)"],
        assumptions=["Single-substrate irreversible catalysis under Briggs-Haldane QSSA"],
        limitations=["Does not model cooperative Hill kinetics or substrate depletion over long times"],
        supported_outputs=["Vmax_uninhibited", "Km_uM", "velocity_at_Km", "catalytic_efficiency", "Vmax_app", "Km_app"],
        validation_tests=["michaelis_menten_half_max_at_Km", "zero_substrate_zero_rate"],
        visualization_template="enzyme_kinetics",
        aliases=["enzyme_kinetics", "lineweaver_burk"],
    ),
    "logistic_growth": _entry(
        experiment_id="logistic_growth",
        domain="biology",
        solver="logistic_growth",
        engine_module="bio_sim",
        method="Verhulst Logistic Population ODE & Exact Analytical Solution",
        equations=[
            "dN/dt = r * N * (1 - N / K)",
            "N(t) = K / (1 + ((K - N_0)/N_0) * exp(-r * t))",
        ],
        parameter_constraints=[
            ParameterConstraint(name="initial_population", value_type="float", required=True, positive=True, default=100.0, default_justification="100 initial cells", aliases=["N0"]),
            ParameterConstraint(name="carrying_capacity", value_type="float", required=True, positive=True, default=1e6, default_justification="1e6 cells carrying capacity", aliases=["K"]),
            ParameterConstraint(name="growth_rate", unit="1/h", required=True, positive=True, default=0.5, default_justification="0.5 h^-1 intrinsic growth rate", aliases=["r"]),
            ParameterConstraint(name="time_hours", unit="h", dimension="time", required=False, positive=True, default=24.0, default_justification="24 h culture duration", aliases=["t_end"]),
        ],
        operating_conditions=["0 < N_0 < K", "Constant growth rate r and carrying capacity K"],
        assumptions=["Homogeneous well-mixed population with instantaneous density regulation"],
        limitations=["Lag phase, death phase, and stochastic extinction not modeled"],
        supported_outputs=["final_population", "doubling_time_h", "inflection_time_h", "max_growth_rate_cells_per_h"],
        validation_tests=["logistic_analytical_vs_ode_match", "bounded_by_carrying_capacity"],
        visualization_template="population_growth",
        aliases=["growth_curve", "bacterial_growth", "population_growth"],
    ),
    "exponential_growth": _entry(
        experiment_id="exponential_growth",
        domain="biology",
        solver="exponential_growth",
        engine_module="bio_sim",
        method="Malthusian Exponential Population Growth Analytical & ODE Solution",
        equations=["dN/dt = r * N", "N(t) = N_0 * exp(r * t)", "t_double = ln(2) / r"],
        parameter_constraints=[
            ParameterConstraint(name="initial_population", value_type="float", required=True, positive=True, default=100.0, default_justification="100 initial cells", aliases=["N0"]),
            ParameterConstraint(name="growth_rate", unit="1/h", required=True, positive=True, default=0.5, default_justification="0.5 h^-1 intrinsic growth rate", aliases=["r"]),
            ParameterConstraint(name="time_hours", unit="h", dimension="time", required=False, positive=True, default=12.0, default_justification="12 h unbounded exponential phase", aliases=["t_end"]),
        ],
        operating_conditions=["Unlimited resources (early log phase)"],
        assumptions=["Constant per-capita growth rate r"],
        limitations=["Unbounded growth is physically valid only before resource limitation"],
        supported_outputs=["final_population", "doubling_time_h", "growth_rate_r"],
        validation_tests=["exponential_doubling_exact"],
        visualization_template="population_growth",
        aliases=["malthusian_growth"],
    ),
    "gene_expression": _entry(
        experiment_id="gene_expression",
        domain="biology",
        solver="gene_expression",
        engine_module="bio_sim",
        method="Coupled Linear Transcription-Translation ODE System",
        equations=["dm/dt = k_tx - d_m * m", "dp/dt = k_tl * m - d_p * p"],
        parameter_constraints=[
            ParameterConstraint(name="transcription_rate", value_type="float", required=False, positive=True, default=0.8, default_justification="Constitutive transcription rate"),
            ParameterConstraint(name="translation_rate", value_type="float", required=False, positive=True, default=0.5, default_justification="Translation rate constant"),
            ParameterConstraint(name="mRNA_degradation", value_type="float", required=False, positive=True, default=0.3, default_justification="mRNA decay constant"),
            ParameterConstraint(name="protein_degradation", value_type="float", required=False, positive=True, default=0.1, default_justification="Protein decay constant"),
        ],
        operating_conditions=["Constitutive deterministic gene expression"],
        assumptions=["Deterministic mass-action kinetics; no transcriptional burst noise"],
        limitations=["Not a stochastic Gillespie model"],
        supported_outputs=["steady_state_mRNA", "steady_state_protein"],
        validation_tests=["steady_state_exact"],
        visualization_template="population_growth",
        aliases=[],
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPUTER SCIENCE — REAL ALGORITHM EXECUTION + SEPARATE COMPLEXITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    "breadth_first_search": _entry(
        experiment_id="breadth_first_search",
        domain="computer_science",
        solver="bfs",
        engine_module="cs_sim",
        method="Exact Queue-Based Breadth-First Search (FIFO deque) with Step Trace",
        equations=["Time: O(V + E)", "Space: O(V)"],
        parameter_constraints=[
            ParameterConstraint(name="graph", value_type="dict", required=False, default={"A": ["B", "C"], "B": ["D", "E"], "C": ["F"], "D": [], "E": ["F"], "F": []}, default_justification="6-node directed/undirected benchmark graph"),
            ParameterConstraint(name="start_node", value_type="str", required=False, default="A", default_justification="Source vertex A"),
        ],
        operating_conditions=["Finite graph represented as adjacency list"],
        assumptions=["Unweighted shortest hop traversal via FIFO queue"],
        limitations=["Does not handle weighted edge costs (use Dijkstra)"],
        supported_outputs=["traversal_order", "levels", "visited_count", "execution_steps", "operation_count", "time_complexity", "space_complexity"],
        validation_tests=["bfs_fifo_order", "bfs_no_duplicate_visits", "bfs_cycles_and_disconnected"],
        visualization_template="graph_traversal",
        aliases=["bfs"],
    ),
    "depth_first_search": _entry(
        experiment_id="depth_first_search",
        domain="computer_science",
        solver="dfs",
        engine_module="cs_sim",
        method="Exact Stack-Based Depth-First Search with Step Trace",
        equations=["Time: O(V + E)", "Space: O(V)"],
        parameter_constraints=[
            ParameterConstraint(name="graph", value_type="dict", required=False, default={"A": ["B", "C"], "B": ["D", "E"], "C": ["F"], "D": [], "E": ["F"], "F": []}, default_justification="6-node benchmark graph"),
            ParameterConstraint(name="start_node", value_type="str", required=False, default="A", default_justification="Source vertex A"),
        ],
        operating_conditions=["Finite graph adjacency list"],
        assumptions=["Deterministic neighbor ordering"],
        limitations=["Does not guarantee shortest path in unweighted graphs"],
        supported_outputs=["traversal_order", "discovery_order", "execution_steps", "operation_count", "time_complexity", "space_complexity"],
        validation_tests=["dfs_depth_first_order", "dfs_no_duplicate_visits"],
        visualization_template="graph_traversal",
        aliases=["dfs"],
    ),
    "dijkstra_shortest_path": _entry(
        experiment_id="dijkstra_shortest_path",
        domain="computer_science",
        solver="dijkstra",
        engine_module="cs_sim",
        method="Exact Binary-Heap Priority Queue Dijkstra Algorithm with Relaxation Trace",
        equations=["Time: O((V + E) log V)", "Space: O(V)"],
        parameter_constraints=[
            ParameterConstraint(name="graph", value_type="dict", required=False, default={"A": {"B": 4, "C": 2}, "B": {"D": 5, "E": 2}, "C": {"B": 1, "E": 3}, "D": {"F": 2}, "E": {"F": 4}, "F": {}}, default_justification="6-node weighted benchmark graph"),
            ParameterConstraint(name="start_node", value_type="str", required=False, default="A", default_justification="Source vertex A"),
            ParameterConstraint(name="target_node", value_type="str", required=False, default="F", default_justification="Target vertex F"),
        ],
        operating_conditions=["Non-negative edge weights w(u,v) >= 0"],
        assumptions=["Directed or undirected weighted graph with non-negative weights"],
        limitations=["Invalid for negative edge weights (requires Bellman-Ford)"],
        supported_outputs=["distances", "shortest_path", "total_cost", "execution_steps", "operation_count"],
        validation_tests=["dijkstra_optimal_cost", "dijkstra_non_negative_weights"],
        visualization_template="graph_traversal",
        aliases=["dijkstra", "shortest_path"],
    ),
    "connected_components": _entry(
        experiment_id="connected_components",
        domain="computer_science",
        solver="connected_components",
        engine_module="cs_sim",
        method="Exact BFS/DFS Connected Components Decomposition",
        equations=["Time: O(V + E)", "Space: O(V)"],
        parameter_constraints=[
            ParameterConstraint(name="graph", value_type="dict", required=False, default={"A": ["B"], "B": ["A", "C"], "C": ["B"], "D": ["E"], "E": ["D"], "F": []}, default_justification="3-component undirected benchmark graph"),
        ],
        operating_conditions=["Undirected graph"],
        assumptions=["Symmetrizes edges if input adjacency is one-sided"],
        limitations=["Undirected connectivity (not strongly connected components)"],
        supported_outputs=["components", "component_count", "execution_steps", "operation_count"],
        validation_tests=["connected_components_partition"],
        visualization_template="graph_traversal",
        aliases=[],
    ),
    "topological_sort": _entry(
        experiment_id="topological_sort",
        domain="computer_science",
        solver="topological_sort",
        engine_module="cs_sim",
        method="Exact Kahn's Algorithm (In-Degree Queue Topological Sort with Cycle Detection)",
        equations=["Time: O(V + E)", "Space: O(V)"],
        parameter_constraints=[
            ParameterConstraint(name="graph", value_type="dict", required=False, default={"A": ["C"], "B": ["C", "D"], "C": ["E"], "D": ["F"], "E": ["F"], "F": []}, default_justification="6-node DAG benchmark"),
        ],
        operating_conditions=["Directed Acyclic Graph (DAG); detects cycles explicitly"],
        assumptions=["Lexicographical tie-breaking for deterministic output"],
        limitations=["Returns cycle detected failure if graph is not a DAG"],
        supported_outputs=["topological_order", "is_dag", "execution_steps", "operation_count"],
        validation_tests=["topological_edge_precedence"],
        visualization_template="graph_traversal",
        aliases=["topo_sort", "kahn"],
    ),
    "bubble_sort": _entry(
        experiment_id="bubble_sort", domain="computer_science", solver="bubble_sort", engine_module="cs_sim",
        method="Instrumented Bubble Sort Execution", equations=["Time: O(n^2) worst/avg, O(n) best", "Space: O(1)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["In-place comparison sort"], limitations=["Quadratic time for large arrays"],
        supported_outputs=["sorted_array", "comparisons", "swaps", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=[],
    ),
    "selection_sort": _entry(
        experiment_id="selection_sort", domain="computer_science", solver="selection_sort", engine_module="cs_sim",
        method="Instrumented Selection Sort Execution", equations=["Time: O(n^2)", "Space: O(1)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["In-place comparison sort"], limitations=["Always performs n(n-1)/2 comparisons"],
        supported_outputs=["sorted_array", "comparisons", "swaps", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=[],
    ),
    "insertion_sort": _entry(
        experiment_id="insertion_sort", domain="computer_science", solver="insertion_sort", engine_module="cs_sim",
        method="Instrumented Insertion Sort Execution", equations=["Time: O(n^2) worst, O(n) best", "Space: O(1)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["Stable in-place insertion sort"], limitations=["Quadratic worst case"],
        supported_outputs=["sorted_array", "comparisons", "shifts", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=[],
    ),
    "merge_sort": _entry(
        experiment_id="merge_sort", domain="computer_science", solver="merge_sort", engine_module="cs_sim",
        method="Instrumented Divide-and-Conquer Merge Sort Execution", equations=["Time: O(n log n)", "Space: O(n)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["Stable out-of-place merge"], limitations=["Requires O(n) auxiliary space"],
        supported_outputs=["sorted_array", "comparisons", "writes", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=["mergesort"],
    ),
    "quick_sort": _entry(
        experiment_id="quick_sort", domain="computer_science", solver="quick_sort", engine_module="cs_sim",
        method="Instrumented Lomuto-Partition Quick Sort Execution", equations=["Time: O(n log n) avg, O(n^2) worst", "Space: O(log n)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["Deterministic last-element pivot Lomuto partition"], limitations=["Worst-case O(n^2) on already sorted inputs"],
        supported_outputs=["sorted_array", "comparisons", "swaps", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=["quicksort"],
    ),
    "heap_sort": _entry(
        experiment_id="heap_sort", domain="computer_science", solver="heap_sort", engine_module="cs_sim",
        method="Instrumented Max-Heap Heap Sort Execution", equations=["Time: O(n log n)", "Space: O(1)"],
        parameter_constraints=[ParameterConstraint(name="array", value_type="list", required=False, default=[45, 12, 89, 34, 67, 23, 91, 5], default_justification="Deterministic 8-element unsorted array", aliases=["data"])],
        operating_conditions=["Comparable numeric sequence"], assumptions=["In-place binary max-heap"], limitations=["Not stable"],
        supported_outputs=["sorted_array", "comparisons", "swaps", "execution_steps", "operation_count"],
        validation_tests=["sort_sorted_and_permutation"], visualization_template="sorting_array", aliases=["heapsort"],
    ),
    "linear_search": _entry(
        experiment_id="linear_search", domain="computer_science", solver="linear_search", engine_module="cs_sim",
        method="Instrumented Linear Search Execution", equations=["Time: O(n)", "Space: O(1)"],
        parameter_constraints=[
            ParameterConstraint(name="array", value_type="list", required=False, default=[12, 45, 7, 23, 56, 89, 34, 19], default_justification="Deterministic 8-element array", aliases=["data"]),
            ParameterConstraint(name="target", value_type="any", required=False, default=56, default_justification="Target element present in reference array"),
        ],
        operating_conditions=["Finite sequence"], assumptions=["Sequential scan from index 0"], limitations=["Linear time"],
        supported_outputs=["found", "found_index", "comparisons", "execution_steps", "operation_count"],
        validation_tests=["search_index_exact"], visualization_template="sorting_array", aliases=[],
    ),
    "binary_search": _entry(
        experiment_id="binary_search", domain="computer_science", solver="binary_search", engine_module="cs_sim",
        method="Instrumented Binary Search Execution (Requires Sorted Input)", equations=["Time: O(log n)", "Space: O(1)"],
        parameter_constraints=[
            ParameterConstraint(name="array", value_type="list", required=False, default=[5, 12, 23, 34, 45, 56, 67, 78, 89, 91], default_justification="Deterministic sorted 10-element array", aliases=["data"]),
            ParameterConstraint(name="target", value_type="any", required=False, default=67, default_justification="Target element in reference sorted array"),
        ],
        operating_conditions=["Input array must be sorted in ascending order"], assumptions=["Sorts input with warning if unsorted"], limitations=["Requires random-access sorted array"],
        supported_outputs=["found", "found_index", "comparisons", "execution_steps", "operation_count"],
        validation_tests=["search_index_exact", "binary_search_log_bound"], visualization_template="sorting_array", aliases=[],
    ),
    "algorithm_complexity": _entry(
        experiment_id="algorithm_complexity", domain="computer_science", solver="algorithm_complexity", engine_module="cs_sim",
        method="Theoretical Asymptotic Complexity Comparison (Separate from Algorithm Execution)",
        equations=["O(log n), O(n), O(n log n), O(n^2)"],
        parameter_constraints=[ParameterConstraint(name="n_max", value_type="int", required=False, min_value=10, max_value=100000, default=500, default_justification="Input size upper bound n=500")],
        operating_conditions=["Asymptotic growth comparison"], assumptions=["Unit-cost RAM model"], limitations=["Theoretical Big-O curves, not empirical runtime execution"],
        supported_outputs=["complexity_at_n_max"], validation_tests=["monotonic_growth_ordering"], visualization_template="sorting_array", aliases=["big_o", "complexity_analysis"],
    ),
    "model_comparison": _entry(
        experiment_id="model_comparison", domain="computer_science", solver="model_comparison", engine_module="cs_sim",
        method="Parametric Analytical Learning-Curve Model (Illustrative CNN vs ViT Convergence)",
        equations=["acc(t) = A_max * (1 - exp(-k * t))", "loss(t) = L_0 * exp(-alpha * t) + L_inf"],
        parameter_constraints=[ParameterConstraint(name="epochs", value_type="int", required=False, min_value=5, max_value=500, default=50, default_justification="50 training epochs")],
        operating_conditions=["Illustrative parametric learning-curve comparison"], assumptions=["Analytical exponential convergence model (not actual GPU training)"],
        limitations=["Does not train real neural weights on CIFAR-10"], supported_outputs=["cnn_final_accuracy_pct", "transformer_final_accuracy_pct", "winner"],
        validation_tests=["bounded_accuracy"], visualization_template="neural_network_3d", aliases=[],
    ),
    "dropout_effect": _entry(
        experiment_id="dropout_effect", domain="computer_science", solver="dropout_effect", engine_module="cs_sim",
        method="Parametric Dropout Regularization Response Model",
        equations=["acc(p) = A_base * exp(-6 * (p - p_opt)^2)"],
        parameter_constraints=[
            ParameterConstraint(name="base_accuracy", value_type="float", required=False, min_value=10.0, max_value=100.0, default=89.0, default_justification="Baseline CNN accuracy"),
            ParameterConstraint(name="optimal_dropout", value_type="float", required=False, min_value=0.05, max_value=0.65, default=0.3, default_justification="Reference optimal dropout p=0.3"),
        ],
        operating_conditions=["Parametric regularization sweep"], assumptions=["Illustrative Gaussian optimum model"],
        limitations=["Not empirical SGD training"], supported_outputs=["optimal_dropout_rate", "peak_accuracy_pct"],
        validation_tests=["bounded_accuracy"], visualization_template="neural_network_3d", aliases=[],
    ),
    "neural_network_training": _entry(
        experiment_id="neural_network_training", domain="computer_science", solver="neural_network_training", engine_module="cs_sim",
        method="Parametric Neural Network Loss/Accuracy Convergence Model",
        equations=["loss(t) = L_0 * exp(-k * t) + L_inf"],
        parameter_constraints=[
            ParameterConstraint(name="epochs", value_type="int", required=False, min_value=5, max_value=500, default=100, default_justification="100 epochs"),
            ParameterConstraint(name="hidden_units", value_type="int", required=False, min_value=4, max_value=4096, default=128, default_justification="128 hidden units"),
            ParameterConstraint(name="learning_rate", value_type="float", required=False, positive=True, max_value=1.0, default=0.001, default_justification="Adam default 1e-3"),
        ],
        operating_conditions=["Parametric analytical model"], assumptions=["Smooth exponential convergence"],
        limitations=["Not actual backpropagation on dataset"], supported_outputs=["final_val_accuracy_pct", "final_train_loss", "final_val_loss"],
        validation_tests=["bounded_accuracy"], visualization_template="neural_network_3d", aliases=["neural_network", "nn_training"],
    ),
}


# Build alias lookup index
_ALIAS_TO_ID: Dict[str, str] = {}
for _eid, _ent in EXPERIMENT_REGISTRY.items():
    _ALIAS_TO_ID[_eid.lower()] = _eid
    for _al in _ent.aliases:
        _ALIAS_TO_ID[_al.lower()] = _eid


def get_experiment_entry(experiment_id: Optional[str]) -> Optional[ExperimentRegistryEntry]:
    """Look up canonical ExperimentRegistryEntry by ID or registered alias."""
    if not experiment_id:
        return None
    key = str(experiment_id).strip().lower()
    canon_id = _ALIAS_TO_ID.get(key)
    return EXPERIMENT_REGISTRY.get(canon_id) if canon_id else None


def list_experiments_by_domain(domain: str) -> List[ExperimentRegistryEntry]:
    """Return all registered experiments for a canonical domain."""
    canon = normalize_canonical_domain(domain)
    return [e for e in EXPERIMENT_REGISTRY.values() if e.domain == canon]


def _has_kw(src: str, keywords: List[str]) -> bool:
    for kw in keywords:
        if len(kw) <= 4 or " " not in kw:
            if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", src):
                return True
        else:
            if kw in src:
                return True
    return False


def classify_experiment(
    topic: str = "",
    design_text: str = "",
    user_domain: Optional[str] = None,
    explicit_experiment_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str], str]:
    """
    Deterministically classify (canonical_domain, experiment_id, classification_reason).
    NEVER silently maps an unknown experiment to an unrelated solver.
    """
    params = parameters or {}
    topic_l = (topic or "").lower()
    design_l = (design_text or "").lower()
    combined = f"{topic_l} {design_l}".strip()
    exp_raw = str(explicit_experiment_type or "").strip().lower()

    # 1. Determine canonical domain (explicit user_domain takes precedence)
    domain = normalize_canonical_domain(user_domain) if user_domain else "general"

    # Special case: explicit experiment_type that directly resolves in the registry
    if exp_raw and exp_raw not in ("", "general", "dynamic_custom", "scientific_simulation", "experiment"):
        # Special civil disambiguation: legacy "beam_analysis" with point_load_kN must go to point_load!
        if exp_raw in ("beam_analysis", "beam", "simply_supported_beam"):
            if "point_loads" in params:
                return "civil", "simply_supported_beam_multiple_loads", "Resolved beam_analysis with multiple point loads"
            if "applied_moment_kNm" in params or _has_kw(combined, ["applied moment", "couple moment", "bending moment applied"]):
                return "civil", "simply_supported_beam_moment", "Resolved beam_analysis with applied moment"
            if (
                "point_load_kN" in params or "P_kN" in params or "P" in params
                or _has_kw(combined, ["point load", "central load", "concentrated load", "midspan load", "center load"])
            ) and not _has_kw(combined, ["uniformly distributed", "udl", "kn/m", "n/m"]):
                if "load_position_m" in params or "a_m" in params or _has_kw(combined, ["eccentric", "off-center", "at x="]):
                    return "civil", "simply_supported_beam_eccentric_point_load", "Resolved eccentric point-load beam"
                return "civil", "simply_supported_beam_point_load", "Resolved central point-load beam"
            return "civil", "simply_supported_beam_udl", "Resolved UDL simply supported beam"

        if exp_raw in ("cantilever_beam", "cantilever"):
            if (
                "point_load_kN" in params or "P_kN" in params
                or _has_kw(combined, ["point load", "tip load", "end load", "concentrated load"])
            ) and not _has_kw(combined, ["uniformly distributed", "udl", "kn/m"]):
                return "civil", "cantilever_beam_point_load", "Resolved cantilever point-load beam"
            return "civil", "cantilever_beam_udl", "Resolved cantilever UDL beam"

        if exp_raw == "thermo_cycle":
            if _has_kw(combined, ["carnot"]):
                return "mechanical", "carnot_cycle", "Resolved Carnot cycle"
            if _has_kw(combined, ["diesel"]):
                return "mechanical", "diesel_cycle", "Resolved Diesel cycle"
            if _has_kw(combined, ["brayton", "gas turbine"]):
                return "mechanical", "brayton_cycle", "Resolved Brayton cycle"
            return "mechanical", "otto_cycle", "Resolved Otto cycle"

        entry = get_experiment_entry(exp_raw)
        if entry:
            # Allow physics_rlc / rlc_circuit regardless of physics vs electronics domain
            if domain == "general" or entry.domain == domain or (entry.experiment_id == "series_rlc" and domain == "physics"):
                return entry.domain, entry.experiment_id, f"Exact registry match for explicit experiment_type '{exp_raw}'"

    # 2. Check exact experiment signatures across all 7 domains (prefer topic first, then combined)
    def _detect_exact(src: str, dom_hint: str) -> Optional[Tuple[str, str, str]]:
        # --- Computer Science (exact algorithm detection BEFORE complexity curves!) ---
        if dom_hint in ("general", "computer_science"):
            if _has_kw(src, ["breadth-first", "breadth first", "bfs"]):
                return ("computer_science", "breadth_first_search", "Detected BFS graph traversal")
            if _has_kw(src, ["depth-first", "depth first", "dfs"]):
                return ("computer_science", "depth_first_search", "Detected DFS graph traversal")
            if _has_kw(src, ["dijkstra", "shortest path"]):
                return ("computer_science", "dijkstra_shortest_path", "Detected Dijkstra shortest path")
            if _has_kw(src, ["connected component", "connected components"]):
                return ("computer_science", "connected_components", "Detected connected components")
            if _has_kw(src, ["topological sort", "topological ordering", "kahn"]):
                return ("computer_science", "topological_sort", "Detected topological sort")
            if _has_kw(src, ["bubble sort", "bubblesort"]):
                return ("computer_science", "bubble_sort", "Detected bubble sort")
            if _has_kw(src, ["selection sort", "selectionsort"]):
                return ("computer_science", "selection_sort", "Detected selection sort")
            if _has_kw(src, ["insertion sort", "insertionsort"]):
                return ("computer_science", "insertion_sort", "Detected insertion sort")
            if _has_kw(src, ["merge sort", "mergesort"]):
                return ("computer_science", "merge_sort", "Detected merge sort")
            if _has_kw(src, ["quick sort", "quicksort"]):
                return ("computer_science", "quick_sort", "Detected quick sort")
            if _has_kw(src, ["heap sort", "heapsort"]):
                return ("computer_science", "heap_sort", "Detected heap sort")
            if _has_kw(src, ["binary search"]):
                return ("computer_science", "binary_search", "Detected binary search")
            if _has_kw(src, ["linear search"]):
                return ("computer_science", "linear_search", "Detected linear search")
            if _has_kw(src, ["cnn", "transformer", "vit", "resnet"]):
                return ("computer_science", "model_comparison", "Detected CNN vs Transformer comparison")
            if _has_kw(src, ["dropout", "regularization"]):
                return ("computer_science", "dropout_effect", "Detected dropout analysis")
            if _has_kw(src, ["neural network", "backpropagation", "epoch"]):
                return ("computer_science", "neural_network_training", "Detected neural network training")
            if _has_kw(src, ["big-o", "big o", "asymptotic complexity", "complexity comparison", "algorithm complexity"]):
                return ("computer_science", "algorithm_complexity", "Detected theoretical complexity analysis")

        # --- Mechanical Engineering ---
        if dom_hint in ("general", "mechanical"):
            if _has_kw(src, ["four-bar", "four bar", "4-bar", "4 bar", "crank-rocker", "crank rocker", "four_bar_linkage", "linkage"]):
                return ("mechanical", "four_bar_linkage", "Detected four-bar linkage kinematics")
            if _has_kw(src, ["spur gear", "gear train", "gear ratio", "pinion", "gear", "gears", "teeth"]):
                return ("mechanical", "gear_train", "Detected spur gear train")
            if _has_kw(src, ["shaft", "torsion", "angle of twist", "polar moment"]):
                return ("mechanical", "shaft_design", "Detected shaft torsion/bending design")
            if _has_kw(src, ["spring-mass", "spring mass", "mass-spring", "mass spring", "harmonic oscillator", "damper"]):
                return ("mechanical", "spring_mass_damper", "Detected spring-mass-damper system")
            if _has_kw(src, ["flywheel", "rotational dynamics", "moment of inertia torque"]):
                return ("mechanical", "rotational_dynamics", "Detected rotational dynamics")
            if _has_kw(src, ["carnot"]):
                return ("mechanical", "carnot_cycle", "Detected Carnot thermodynamic cycle")
            if _has_kw(src, ["diesel cycle", "diesel engine", "cutoff ratio"]):
                return ("mechanical", "diesel_cycle", "Detected Diesel thermodynamic cycle")
            if _has_kw(src, ["brayton", "gas turbine"]):
                return ("mechanical", "brayton_cycle", "Detected Brayton thermodynamic cycle")
            if _has_kw(src, ["otto cycle", "otto"]):
                return ("mechanical", "otto_cycle", "Detected Otto thermodynamic cycle")

        # --- Civil Engineering ---
        if dom_hint in ("general", "civil"):
            if _has_kw(src, ["truss", "pratt truss", "warren truss", "bridge truss"]):
                return ("civil", "truss_analysis", "Detected truss structural analysis")
            if _has_kw(src, ["cantilever", "fixed-free", "fixed beam"]):
                if (
                    "point_load_kN" in params or "P_kN" in params
                    or _has_kw(src, ["point load", "tip load", "end load", "concentrated load"])
                ) and not _has_kw(src, ["uniformly distributed", "udl", "kn/m"]):
                    return ("civil", "cantilever_beam_point_load", "Detected cantilever point-load beam")
                return ("civil", "cantilever_beam_udl", "Detected cantilever UDL beam")
            if _has_kw(src, ["beam", "simply supported", "bending moment", "shear force", "deflection"]):
                if "point_loads" in params or _has_kw(src, ["multiple point load", "two point load"]):
                    return ("civil", "simply_supported_beam_multiple_loads", "Detected multiple point-load beam")
                if "applied_moment_kNm" in params or _has_kw(src, ["applied moment", "couple moment"]):
                    return ("civil", "simply_supported_beam_moment", "Detected applied bending moment beam")
                if (
                    "point_load_kN" in params or "P_kN" in params
                    or _has_kw(src, ["point load", "central load", "concentrated load", "midspan load", "center load"])
                ) and not _has_kw(src, ["uniformly distributed", "udl", "kn/m", "n/m"]):
                    if "load_position_m" in params or _has_kw(src, ["eccentric", "off-center"]):
                        return ("civil", "simply_supported_beam_eccentric_point_load", "Detected eccentric point-load beam")
                    return ("civil", "simply_supported_beam_point_load", "Detected central point-load beam")
                return ("civil", "simply_supported_beam_udl", "Detected simply supported UDL beam")
            if _has_kw(src, ["blueprint", "floor plan", "building plan"]):
                return ("civil", "building_blueprint", "Detected building blueprint")

        # --- Electrical & Electronics ---
        if dom_hint in ("general", "electronics", "physics"):
            if _has_kw(src, ["rlc", "series rlc", "rlc circuit", "resonant circuit"]):
                return ("electronics", "series_rlc", "Detected series RLC circuit")
            if _has_kw(src, ["transformer", "turns ratio", "primary winding", "secondary winding"]):
                return ("electronics", "transformer", "Detected transformer")
            if _has_kw(src, ["voltage divider"]):
                return ("electronics", "voltage_divider", "Detected voltage divider")
            if _has_kw(src, ["current divider"]):
                return ("electronics", "current_divider", "Detected current divider")
            if _has_kw(src, ["rc circuit", "rc charging", "capacitor charging", "time constant rc"]):
                return ("electronics", "rc_circuit", "Detected RC transient circuit")
            if _has_kw(src, ["rl circuit", "inductor charging", "time constant rl"]):
                return ("electronics", "rl_circuit", "Detected RL transient circuit")
            if _has_kw(src, ["ac circuit", "phasor", "impedance", "power factor"]):
                return ("electronics", "ac_circuit", "Detected AC phasor circuit")
            if _has_kw(src, ["series resistor", "parallel resistor", "series and parallel", "resistor network"]):
                return ("electronics", "series_parallel_circuit", "Detected series/parallel resistor circuit")
            if _has_kw(src, ["arduino", "blink", "microcontroller"]):
                return ("electronics", "arduino_led", "Detected Arduino LED circuit")
            if _has_kw(src, ["ohm", "ohm's law", "i-v curve", "conductance"]):
                return ("electronics", "ohms_law", "Detected Ohm's law")
            if _has_kw(src, ["led", "current-limiting resistor"]):
                return ("electronics", "led_resistor", "Detected LED + resistor circuit")

        # --- Chemistry ---
        if dom_hint in ("general", "chemistry"):
            if _has_kw(src, ["titration", "equivalence point", "weak acid", "strong base", "pka", "buffer curve", "acetic acid", "naoh"]):
                return ("chemistry", "acid_base_titration", "Detected acid-base titration")
            if _has_kw(src, ["chemical equilibrium", "equilibrium constant", "ice table", "mass action", "le chatelier"]):
                return ("chemistry", "chemical_equilibrium", "Detected chemical equilibrium")
            if _has_kw(src, ["gibbs", "free energy", "enthalpy", "entropy", "van 't hoff", "vant hoff"]):
                return ("chemistry", "chemical_thermodynamics", "Detected chemical thermodynamics")
            if _has_kw(src, ["arrhenius", "reaction kinetics", "reaction rate", "first-order", "second-order", "half-life", "activation energy"]):
                return ("chemistry", "reaction_kinetics", "Detected reaction kinetics")
            if _has_kw(src, ["molecular weight", "smiles", "molecular geometry", "water molecule", "benzene", "ethanol", "methane", "nickel chloride", "nicl2"]):
                return ("chemistry", "molecular_properties", "Detected molecular properties/geometry")

        # --- Biology ---
        if dom_hint in ("general", "biology"):
            if _has_kw(src, ["michaelis", "menten", "enzyme", "lineweaver", "substrate", "vmax", "allosteric", "inhibitor"]):
                return ("biology", "michaelis_menten", "Detected Michaelis-Menten enzyme kinetics")
            if _has_kw(src, ["exponential growth", "malthusian", "unbounded growth"]):
                return ("biology", "exponential_growth", "Detected exponential population growth")
            if _has_kw(src, ["logistic", "carrying capacity", "bacterial growth", "population growth", "growth curve"]):
                return ("biology", "logistic_growth", "Detected logistic population growth")
            if _has_kw(src, ["gene expression", "transcription", "translation", "mrna"]):
                return ("biology", "gene_expression", "Detected gene expression dynamics")

        # --- Physics ---
        if dom_hint in ("general", "physics"):
            if _has_kw(src, ["projectile", "ballistic", "trajectory", "launch angle"]):
                return ("physics", "projectile_motion", "Detected projectile motion")
            if _has_kw(src, ["pendulum", "simple pendulum", "damped pendulum", "driven pendulum"]):
                return ("physics", "pendulum", "Detected pendulum motion")

        return None

    # Prefer topic-only detection first (avoids false positives from boilerplate in long designs)
    hit = _detect_exact(topic_l, domain)
    if hit:
        return hit

    # Fall back to combined topic + design text
    hit = _detect_exact(combined, domain)
    if hit:
        return hit

    # Infer broad domain if still general, but DO NOT invent an experiment_id!
    if domain == "general":
        if _has_kw(combined, ["biology", "biological", "bacterial", "cell", "enzyme", "organism", "population"]):
            domain = "biology"
        elif _has_kw(combined, ["chemistry", "chemical", "reaction", "acid", "base", "molecule", "molar"]):
            domain = "chemistry"
        elif _has_kw(combined, ["civil", "structural", "beam", "truss", "concrete", "foundation"]):
            domain = "civil"
        elif _has_kw(combined, ["mechanical", "linkage", "cam", "gear", "piston", "turbine", "shaft", "mechanism"]):
            domain = "mechanical"
        elif _has_kw(combined, ["electronics", "electrical", "circuit", "voltage", "resistor", "capacitor", "inductor"]):
            domain = "electronics"
        elif _has_kw(combined, ["computer science", "algorithm", "graph", "sorting", "tree", "machine learning"]):
            domain = "computer_science"
        elif _has_kw(combined, ["physics", "kinematics", "mechanics", "optics", "wave"]):
            domain = "physics"

    return domain, None, f"No registered deterministic solver matches request in domain '{domain}'"
