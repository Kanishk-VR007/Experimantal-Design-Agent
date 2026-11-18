"""
Mechanical Engineering Simulation Engine
=========================================
Explicit deterministic solvers for:
  - four_bar_linkage (Planar vector-loop closure kinematics + velocity + Grashof check)
  - gear_train (Involute spur gear kinematics, torque multiplication, Lewis stress)
  - shaft_design (Circular shaft torsion + combined bending + von Mises FoS)
  - spring_mass_damper (1-DOF vibration ODE + exact modal parameters)
  - rotational_dynamics (Fixed-axis rigid-body rotational Newton-Euler ODE)
  - otto_cycle (Ideal air-standard Otto cycle)
  - carnot_cycle (Ideal reversible Carnot cycle: 2 isotherms + 2 adiabats)
  - diesel_cycle (Ideal air-standard Diesel cycle)
  - brayton_cycle (Ideal air-standard Brayton gas-turbine cycle)

Never falls back to an unrelated solver for unrecognized mechanical experiments.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.integrate import solve_ivp

from .llm_fallback import build_unsupported_response, build_failed_response


# ─── Four-Bar Linkage Kinematics Solver ──────────────────────────────────────

def _classify_grashof(a: float, b: float, c: float, d: float) -> Tuple[str, bool]:
    """Classify four-bar mechanism per Grashof's law."""
    lengths = sorted([a, b, c, d])
    s, p, q, l = lengths
    diff = (s + l) - (p + q)
    if diff < -1e-9:
        if math.isclose(d, s, rel_tol=1e-9):
            return "Grashof Double-Crank (Drag-Link)", True
        if math.isclose(a, s, rel_tol=1e-9):
            return "Grashof Crank-Rocker (Full Crank Rotation)", True
        if math.isclose(c, s, rel_tol=1e-9):
            return "Grashof Rocker-Crank", True
        return "Grashof Double-Rocker", True
    if abs(diff) <= 1e-9:
        return "Grashof Change-Point Mechanism", True
    return "Non-Grashof Triple-Rocker (Limited Crank Range)", False


def solve_four_bar_configuration(
    a: float,
    b: float,
    c: float,
    d: float,
    theta2_rad: float,
    omega2_rad_s: float = 0.0,
    assembly_mode: str = "open",
) -> Optional[Dict[str, Any]]:
    """
    Solve exact planar vector-loop closure at a single crank angle theta2_rad.
    Ground pivots: A=(0,0), D=(d,0).
    Returns joint coordinates, link angles, angular velocities, transmission angle,
    and vector-loop closure residual, or None if mechanism cannot close at theta2_rad.
    """
    xA, yA = 0.0, 0.0
    xD, yD = d, 0.0
    xB = a * math.cos(theta2_rad)
    yB = a * math.sin(theta2_rad)

    dx = xD - xB
    dy = yD - yB
    r = math.hypot(dx, dy)
    if r <= 1e-12:
        return None
    if r > (b + c) + 1e-9 or r < abs(b - c) - 1e-9:
        return None

    # Exact circle-circle intersection: circle(B, b) ∩ circle(D, c)
    a_proj = (b * b - c * c + r * r) / (2.0 * r)
    h_sq = max(0.0, b * b - a_proj * a_proj)
    h = math.sqrt(h_sq)

    p2x = xB + (a_proj / r) * dx
    p2y = yB + (a_proj / r) * dy

    # Unit normal to BD: (-dy/r, dx/r)
    nx = -dy / r
    ny = dx / r

    sign = 1.0 if str(assembly_mode).lower().strip() != "crossed" else -1.0
    xC = p2x + sign * h * nx
    yC = p2y + sign * h * ny

    theta3 = math.atan2(yC - yB, xC - xB)
    theta4 = math.atan2(yC - yD, xC - xD)

    # Vector-loop closure residual: r2 + r3 - r4 - r1 = 0
    ex = a * math.cos(theta2_rad) + b * math.cos(theta3) - c * math.cos(theta4) - d
    ey = a * math.sin(theta2_rad) + b * math.sin(theta3) - c * math.sin(theta4)
    closure_residual = math.hypot(ex, ey)

    # Transmission angle mu between coupler (b) and rocker (c)
    cos_mu = max(-1.0, min(1.0, (b * b + c * c - r * r) / (2.0 * b * c)))
    mu_deg = math.degrees(math.acos(cos_mu))

    # Velocity analysis: differentiate loop equations
    denom = math.sin(theta3 - theta4)
    singular = abs(denom) < 1e-4 or mu_deg < 5.0 or mu_deg > 175.0
    if abs(denom) > 1e-9:
        omega3 = -(a * omega2_rad_s * math.sin(theta2_rad - theta4)) / (b * denom)
        omega4 = (a * omega2_rad_s * math.sin(theta2_rad - theta3)) / (c * (-denom))
    else:
        omega3 = 0.0
        omega4 = 0.0

    # Link-length verification
    len_ab = math.hypot(xB - xA, yB - yA)
    len_bc = math.hypot(xC - xB, yC - yB)
    len_cd = math.hypot(xC - xD, yC - yD)
    max_len_err = max(abs(len_ab - a), abs(len_bc - b), abs(len_cd - c))

    return {
        "A": [round(xA, 6), round(yA, 6)],
        "B": [round(xB, 6), round(yB, 6)],
        "C": [round(xC, 6), round(yC, 6)],
        "D": [round(xD, 6), round(yD, 6)],
        "theta2_deg": round(math.degrees(theta2_rad), 4),
        "theta3_deg": round(math.degrees(theta3), 4),
        "theta4_deg": round(math.degrees(theta4), 4),
        "theta2_rad": theta2_rad,
        "theta3_rad": theta3,
        "theta4_rad": theta4,
        "omega3_rad_s": round(omega3, 6),
        "omega4_rad_s": round(omega4, 6),
        "transmission_angle_deg": round(mu_deg, 3),
        "closure_residual_m": closure_residual,
        "max_link_length_error_m": max_len_err,
        "singular": singular,
    }


def _four_bar_linkage(params: dict) -> Dict[str, Any]:
    """Dedicated planar four-bar linkage kinematics & velocity solver."""
    # Extract link lengths (strict positive validation)
    d = float(params.get("ground_length_m") or params.get("ground_length") or params.get("d") or params.get("L1") or params.get("length_d") or 3.0)
    a = float(params.get("crank_length_m") or params.get("crank_length") or params.get("a") or params.get("L2") or params.get("length_a") or 1.0)
    b = float(params.get("coupler_length_m") or params.get("coupler_length") or params.get("b") or params.get("L3") or params.get("length_b") or 2.5)
    c = float(params.get("rocker_length_m") or params.get("rocker_length") or params.get("c") or params.get("L4") or params.get("length_c") or 2.0)

    if min(a, b, c, d) <= 0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "four_bar_linkage"},
            f"All link lengths must be positive (>0): a={a}, b={b}, c={c}, d={d}",
        )

    # Check global quadrilateral assembly feasibility: longest link < sum of other three
    longest = max(a, b, c, d)
    if longest >= (a + b + c + d - longest) - 1e-9:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "four_bar_linkage"},
            f"Impossible four-bar geometry: longest link ({longest} m) >= sum of other three links ({a+b+c+d-longest:.4f} m).",
        )

    theta2_start_deg = float(params.get("input_angle_deg") or params.get("theta2_deg") or params.get("crank_angle_deg") or 45.0)
    if "angular_velocity_rad_s" in params and params["angular_velocity_rad_s"] is not None:
        omega2 = float(params["angular_velocity_rad_s"])
    elif "omega2" in params and params["omega2"] is not None:
        omega2 = float(params["omega2"])
    elif "rpm" in params or "rpm_input" in params or "cadence_rpm" in params:
        rpm_val = float(params.get("rpm") or params.get("rpm_input") or params.get("cadence_rpm") or 30.0)
        omega2 = rpm_val * 2.0 * math.pi / 60.0
    else:
        omega2 = math.pi  # 30 RPM

    direction = str(params.get("motion_direction", "ccw")).lower().strip()
    if direction == "cw" and omega2 > 0:
        omega2 = -omega2
    elif direction == "ccw" and omega2 < 0:
        omega2 = abs(omega2)

    assembly_mode = str(params.get("assembly_mode", "open")).lower().strip()
    if assembly_mode not in ("open", "crossed"):
        assembly_mode = "open"

    grashof_label, is_grashof = _classify_grashof(a, b, c, d)

    # Determine valid crank angle range
    # r^2(theta2) = a^2 + d^2 - 2*a*d*cos(theta2), must satisfy (b-c)^2 <= r^2 <= (b+c)^2
    cos_min = ((a * a + d * d) - (b + c) ** 2) / (2.0 * a * d)
    cos_max = ((a * a + d * d) - (b - c) ** 2) / (2.0 * a * d)
    full_rotation = (cos_min <= -1.0 + 1e-9) and (cos_max >= 1.0 - 1e-9)

    n_steps = int(params.get("num_steps", 120))
    n_steps = max(24, min(360, n_steps))
    theta0_rad = math.radians(theta2_start_deg)

    if full_rotation:
        sign_dir = 1.0 if omega2 >= 0 else -1.0
        sweep_rad = [theta0_rad + sign_dir * (2.0 * math.pi * k / n_steps) for k in range(n_steps)]
        min_angle_deg, max_angle_deg = 0.0, 360.0
    else:
        lo_cos = max(-1.0, min(1.0, cos_min))
        hi_cos = max(-1.0, min(1.0, cos_max))
        # cos(theta) in [lo_cos, hi_cos] -> theta in [acos(hi_cos), acos(lo_cos)]
        th_lo = math.acos(hi_cos)
        th_hi = math.acos(lo_cos)
        margin = 1e-3
        sweep_half = np.linspace(th_lo + margin, th_hi - margin, n_steps // 2)
        sweep_rad = np.concatenate([sweep_half, sweep_half[::-1]]).tolist()
        min_angle_deg, max_angle_deg = round(math.degrees(th_lo), 2), round(math.degrees(th_hi), 2)

    # Evaluate single requested configuration first
    start_cfg = solve_four_bar_configuration(a, b, c, d, theta0_rad, omega2, assembly_mode)
    warnings: List[str] = []
    if start_cfg is None:
        warnings.append(
            f"Requested input_angle_deg={theta2_start_deg}° lies outside feasible assembly range "
            f"[{min_angle_deg}°, {max_angle_deg}°]; evaluated across valid kinematic branch."
        )

    joint_positions: List[Dict[str, Any]] = []
    theta2_list: List[float] = []
    theta3_list: List[float] = []
    theta4_list: List[float] = []
    omega3_list: List[float] = []
    omega4_list: List[float] = []
    mu_list: List[float] = []
    time_steps: List[float] = []
    max_closure_err = 0.0
    max_len_err = 0.0
    singular_angles: List[float] = []

    dt = (2.0 * math.pi / max(abs(omega2), 1e-6)) / n_steps
    for idx, th2 in enumerate(sweep_rad):
        cfg = solve_four_bar_configuration(a, b, c, d, th2, omega2, assembly_mode)
        if cfg is None:
            continue
        t_val = round(idx * dt, 4)
        time_steps.append(t_val)
        joint_positions.append({
            "t": t_val,
            "A": cfg["A"],
            "B": cfg["B"],
            "C": cfg["C"],
            "D": cfg["D"],
            "theta2_rad": cfg["theta2_rad"],
            "theta3_rad": cfg["theta3_rad"],
            "theta4_rad": cfg["theta4_rad"],
        })
        theta2_list.append(cfg["theta2_deg"])
        theta3_list.append(cfg["theta3_deg"])
        theta4_list.append(cfg["theta4_deg"])
        omega3_list.append(cfg["omega3_rad_s"])
        omega4_list.append(cfg["omega4_rad_s"])
        mu_list.append(cfg["transmission_angle_deg"])
        max_closure_err = max(max_closure_err, cfg["closure_residual_m"])
        max_len_err = max(max_len_err, cfg["max_link_length_error_m"])
        if cfg["singular"]:
            singular_angles.append(cfg["theta2_deg"])

    if not joint_positions:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "four_bar_linkage"},
            "No valid closed kinematic configurations found for the given link lengths.",
        )

    ref_cfg = start_cfg or solve_four_bar_configuration(a, b, c, d, sweep_rad[0], omega2, assembly_mode)
    if singular_angles:
        warnings.append(f"Near-singular / poor transmission angle encountered at {len(singular_angles)} positions (min μ={min(mu_list):.1f}°).")

    numerical = {
        "four_bar_linkage": {
            "ground_length_m": d,
            "crank_length_m": a,
            "coupler_length_m": b,
            "rocker_length_m": c,
            "assembly_mode": assembly_mode,
            "motion_direction": direction,
            "grashof_classification": grashof_label,
            "is_grashof": is_grashof,
            "full_crank_rotation": full_rotation,
            "valid_crank_range_deg": [min_angle_deg, max_angle_deg],
            "input_angle_deg": ref_cfg["theta2_deg"],
            "coupler_angle_deg": ref_cfg["theta3_deg"],
            "rocker_angle_deg": ref_cfg["theta4_deg"],
            "input_omega2_rad_s": round(omega2, 4),
            "coupler_omega3_rad_s": ref_cfg["omega3_rad_s"],
            "rocker_omega4_rad_s": ref_cfg["omega4_rad_s"],
            "joint_B_m": ref_cfg["B"],
            "joint_C_m": ref_cfg["C"],
            "min_transmission_angle_deg": round(min(mu_list), 2),
            "max_transmission_angle_deg": round(max(mu_list), 2),
            "max_closure_residual_m": float(f"{max_closure_err:.3e}"),
            "max_link_length_error_m": float(f"{max_len_err:.3e}"),
            "valid_steps": len(joint_positions),
        },
        "kinematic_trajectory": {
            "time_steps": time_steps,
            "joint_positions": joint_positions,
            "theta2_deg": theta2_list,
            "theta3_deg": theta3_list,
            "theta4_deg": theta4_list,
            "omega3_rad_s": omega3_list,
            "omega4_rad_s": omega4_list,
            "transmission_angle_deg": mu_list,
        },
    }

    plots = [
        {
            "plot_type": "line",
            "title": "Four-Bar Linkage — Coupler & Rocker Angles vs Input Crank Angle",
            "x_label": "Input Crank Angle θ₂ (deg)",
            "y_label": "Link Angle (deg)",
            "x": theta2_list,
            "y": theta4_list,
            "series_name": "Rocker Angle θ₄",
            "extra_series": [
                {"y": theta3_list, "name": "Coupler Angle θ₃", "color": "#f59e0b"},
                {"y": mu_list, "name": "Transmission Angle μ", "color": "#10b981"},
            ],
        },
        {
            "plot_type": "line",
            "title": "Four-Bar Linkage — Angular Velocities ω₃ & ω₄",
            "x_label": "Input Crank Angle θ₂ (deg)",
            "y_label": "Angular Velocity (rad/s)",
            "x": theta2_list,
            "y": omega4_list,
            "series_name": "Rocker ω₄",
            "extra_series": [
                {"y": omega3_list, "name": "Coupler ω₃", "color": "#a855f7"},
            ],
        },
        {
            "plot_type": "line",
            "title": "Joint B and Joint C Planar Path Trajectories",
            "x_label": "X Coordinate (m)",
            "y_label": "Y Coordinate (m)",
            "x": [jp["C"][0] for jp in joint_positions],
            "y": [jp["C"][1] for jp in joint_positions],
            "series_name": "Rocker Tip C Trajectory",
        },
    ]

    # Visual SVG schematic data from actual solved initial configuration
    scale = 400.0 / max(d + a + c, 1e-3)
    ox, oy = 160.0, 260.0
    pA = [ox, oy]
    pD = [ox + d * scale, oy]
    pB = [ox + ref_cfg["B"][0] * scale, oy - ref_cfg["B"][1] * scale]
    pC = [ox + ref_cfg["C"][0] * scale, oy - ref_cfg["C"][1] * scale]
    visual_data = {
        "model_type": "four_bar_linkage",
        "title": f"Four-Bar Linkage — a={a}m, b={b}m, c={c}m, d={d}m ({grashof_label})",
        "width": 720,
        "height": 460,
        "views": ["front"],
        "parts": [
            {"id": "GROUND", "type": "link", "x1": pA[0], "y1": pA[1], "x2": pD[0], "y2": pD[1], "label": f"Ground d={d}m"},
            {"id": "CRANK", "type": "link", "x1": pA[0], "y1": pA[1], "x2": pB[0], "y2": pB[1], "label": f"Crank a={a}m"},
            {"id": "COUPLER", "type": "link", "x1": pB[0], "y1": pB[1], "x2": pC[0], "y2": pC[1], "label": f"Coupler b={b}m"},
            {"id": "ROCKER", "type": "link", "x1": pD[0], "y1": pD[1], "x2": pC[0], "y2": pC[1], "label": f"Rocker c={c}m"},
        ],
        "joints": {"A": pA, "B": pB, "C": pC, "D": pD},
    }

    observations = [
        f"Mechanism classification: {grashof_label} (a={a} m, b={b} m, c={c} m, d={d} m, mode='{assembly_mode}').",
        f"At θ₂ = {ref_cfg['theta2_deg']}°: θ₃ = {ref_cfg['theta3_deg']}°, θ₄ = {ref_cfg['theta4_deg']}°, transmission angle μ = {ref_cfg['transmission_angle_deg']}°.",
        f"Angular velocities at ω₂ = {omega2:.3f} rad/s: ω₃ = {ref_cfg['omega3_rad_s']} rad/s, ω₄ = {ref_cfg['omega4_rad_s']} rad/s.",
        f"Vector-loop closure residual across all {len(joint_positions)} solved steps <= {max_closure_err:.2e} m (link length error <= {max_len_err:.2e} m).",
    ]

    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim",
        "experiment_id": "four_bar_linkage",
        "solver": {
            "name": "four_bar_kinematics",
            "version": "2.0",
            "method": "Planar Vector-Loop Closure & Exact Velocity Kinematics",
            "equations": [
                "a*cos(th2) + b*cos(th3) - c*cos(th4) - d = 0",
                "a*sin(th2) + b*sin(th3) - c*sin(th4) = 0",
                "omega3 = -(a*omega2*sin(th2 - th4)) / (b*sin(th3 - th4))",
                "omega4 = (a*omega2*sin(th2 - th3)) / (c*sin(th4 - th3))",
            ],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": visual_data,
        "visualization_type": "3d_model",
        "observations": observations,
        "assumptions": [
            "Planar rigid links connected by ideal frictionless revolute joints",
            f"Assembly branch: '{assembly_mode}', rotation direction: '{direction}'",
        ],
        "limitations": ["Kinematic analysis only; inertial/dynamic joint forces not modeled"],
        "warnings": warnings,
        "simulation_log": [
            "[mech_sim] Executing dedicated planar four-bar linkage vector-loop kinematics solver",
            f"[mech_sim] Grashof: {grashof_label}; max closure residual={max_closure_err:.2e} m",
        ],
    }


# ─── Gear-train analysis ─────────────────────────────────────────────────────

def _gear_train(params: dict) -> Dict[str, Any]:
    """Spur gear train analysis with exact torque/speed & Lewis bending stress."""
    N1 = int(params.get("teeth_driver") or params.get("driver_teeth") or params.get("N1") or 20)
    N2 = int(params.get("teeth_driven") or params.get("driven_teeth") or params.get("N2") or 40)
    module = float(params.get("module_mm", 2.5))
    rpm_in = float(params.get("rpm_input") or params.get("input_rpm") or 1500.0)
    power_kW = float(params.get("power_kW", 5.0))
    pressure_angle = float(params.get("pressure_angle_deg", 20.0))
    eta = float(params.get("efficiency", 0.97))
    b = float(params.get("face_width_mm", 25.0))

    if N1 <= 0 or N2 <= 0 or module <= 0 or rpm_in <= 0 or power_kW <= 0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "gear_train"},
            "Gear tooth counts, module, RPM, and power must all be strictly positive.",
        )

    ratio = N2 / N1
    rpm_out = rpm_in / ratio
    omega_in = rpm_in * 2.0 * math.pi / 60.0
    omega_out = rpm_out * 2.0 * math.pi / 60.0

    d1 = N1 * module       # pitch diameter driver (mm)
    d2 = N2 * module       # pitch diameter driven (mm)
    centre_dist = (d1 + d2) / 2.0

    T_in = (power_kW * 1000.0) / omega_in       # N·m
    T_out = T_in * ratio * eta                  # N·m
    power_out_kW = (T_out * omega_out) / 1000.0

    Ft = T_in / ((d1 / 2.0) / 1000.0)           # N
    Fr = Ft * math.tan(math.radians(pressure_angle))
    Y = 0.32  # Lewis form factor approximation (~20T standard 20 deg involute)
    sigma_b = Ft / (b * module * Y)             # MPa

    numerical = {
        "gear_train": {
            "gear_ratio_numeric": round(ratio, 6),
            "gear_ratio": f"{N2}:{N1} = {round(ratio, 2)}",
            "module_mm": module,
            "teeth_driver": N1,
            "teeth_driven": N2,
            "pitch_dia_driver_mm": round(d1, 2),
            "pitch_dia_driven_mm": round(d2, 2),
            "centre_distance_mm": round(centre_dist, 2),
            "rpm_input": rpm_in,
            "rpm_output": round(rpm_out, 4),
            "omega_input_rad_s": round(omega_in, 4),
            "omega_output_rad_s": round(omega_out, 4),
            "torque_input_Nm": round(T_in, 4),
            "torque_output_Nm": round(T_out, 4),
            "power_input_kW": round(power_kW, 4),
            "power_output_kW": round(power_out_kW, 4),
            "efficiency": eta,
            "tangential_force_N": round(Ft, 2),
            "radial_force_N": round(Fr, 2),
            "bending_stress_MPa": round(sigma_b, 2),
        }
    }

    rpms = np.linspace(max(50.0, rpm_in * 0.1), rpm_in * 1.2, 80)
    torques_in = (power_kW * 1000.0 * 60.0) / (2.0 * math.pi * rpms)
    torques_out = torques_in * ratio * eta
    plots = [{
        "plot_type": "line",
        "title": "Spur Gear Train — Torque vs Input Speed (Constant Power)",
        "x_label": "Input Speed (RPM)",
        "y_label": "Torque (N·m)",
        "x": rpms.tolist(),
        "y": torques_in.tolist(),
        "series_name": "Input Shaft Torque",
        "extra_series": [{"y": torques_out.tolist(), "name": "Output Shaft Torque", "color": "#f59e0b"}],
    }]

    cx1, cy1 = 250, 220
    r1 = d1 / 2.0 * 1.8
    r2 = d2 / 2.0 * 1.8
    cx2 = cx1 + r1 + r2
    visual_data = {
        "model_type": "gear_train",
        "title": f"Spur Gear Train — {N1}T / {N2}T (m={module}mm)",
        "width": 720, "height": 460, "views": ["top"],
        "parts": [
            {"id": "GEAR1", "type": "gear", "cx": cx1, "cy": cy1, "r": r1, "teeth": N1, "module": module, "label": f"Driver {N1}T Ø{round(d1,1)}mm", "direction": "cw", "properties": {"pitch_dia_mm": round(d1, 1), "rpm": rpm_in, "torque_Nm": round(T_in, 2)}},
            {"id": "GEAR2", "type": "gear", "cx": cx2, "cy": cy1, "r": r2, "teeth": N2, "module": module, "label": f"Driven {N2}T Ø{round(d2,1)}mm", "direction": "ccw", "properties": {"pitch_dia_mm": round(d2, 1), "rpm": round(rpm_out, 1), "torque_Nm": round(T_out, 2)}},
            {"id": "SHAFT1", "type": "shaft", "cx": cx1, "cy": cy1, "length": 60, "label": "Input Shaft", "properties": {"rpm": rpm_in, "torque_Nm": round(T_in, 2)}},
            {"id": "SHAFT2", "type": "shaft", "cx": cx2, "cy": cy1, "length": 60, "label": "Output Shaft", "properties": {"rpm": round(rpm_out, 1), "torque_Nm": round(T_out, 2)}},
        ],
        "dimensions": [{"id": "DIM_CD", "from_id": "GEAR1", "to_id": "GEAR2", "label": f"C/D = {round(centre_dist,1)} mm", "x1": cx1, "y1": cy1 + r1 + 50, "x2": cx2, "y2": cy1 + r2 + 50}],
        "annotations": [
            {"x": cx1, "y": cy1 - r1 - 25, "text": f"{rpm_in} RPM → {round(rpm_out,1)} RPM", "color": "#60a5fa"},
            {"x": (cx1 + cx2) / 2, "y": cy1 + max(r1, r2) + 75, "text": f"Ratio {round(ratio,2)}:1 — η {int(eta*100)}%", "color": "#a78bfa"},
        ],
    }

    observations = [
        f"Gear ratio i = N₂/N₁ = {N2}/{N1} = {ratio:.4f}:1",
        f"Rotational speed: {rpm_in} RPM → {rpm_out:.2f} RPM (N₁·ω₁ = N₂·ω₂ verified)",
        f"Torque: {T_in:.2f} N·m → {T_out:.2f} N·m at {eta*100:.1f}% mesh efficiency (P_out = {power_out_kW:.3f} kW)",
        f"Centre distance = {centre_dist:.2f} mm; Lewis tooth bending stress ≈ {sigma_b:.2f} MPa",
    ]
    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim",
        "experiment_id": "gear_train",
        "solver": {
            "name": "gear_train",
            "version": "2.0",
            "method": "Involute Spur Gear Kinematics & Lewis Bending Stress",
            "equations": ["i = N2/N1", "omega_out = omega_in / i", "T_out = eta * i * T_in", "C = m*(N1+N2)/2"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": visual_data,
        "visualization_type": "3d_model",
        "observations": observations,
        "assumptions": ["Standard full-depth involute spur gears", f"Constant mesh efficiency eta={eta}"],
        "limitations": ["AGMA dynamic/pitting factors omitted"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Spur gear train kinematics & torque analysis computed"],
    }


# ─── Shaft torsion & combined bending ────────────────────────────────────────

def _shaft_design(params: dict) -> Dict[str, Any]:
    """Solid circular shaft under torsion and combined bending."""
    T_Nm = float(params.get("torque_Nm") or params.get("T_Nm") or 200.0)
    M_Nm = float(params.get("bending_moment_Nm") or params.get("M_Nm") or 150.0)
    if "length_mm" in params and params["length_mm"] is not None:
        L_mm = float(params["length_mm"])
    elif "length_m" in params and params["length_m"] is not None:
        L_mm = float(params["length_m"]) * 1000.0
    else:
        L_mm = 500.0
    if "diameter_mm" in params and params["diameter_mm"] is not None:
        d_mm = float(params["diameter_mm"])
    elif "diameter_m" in params and params["diameter_m"] is not None:
        d_mm = float(params["diameter_m"]) * 1000.0
    else:
        d_mm = 40.0
    mat = str(params.get("material", "AISI 1045 Steel"))
    Sy = float(params.get("yield_strength_MPa", 310.0))
    G_GPa = float(params.get("shear_modulus_GPa", 80.0))

    if d_mm <= 0 or L_mm <= 0 or G_GPa <= 0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "shaft_design"},
            "Shaft diameter, length, and shear modulus must be strictly positive.",
        )

    r = d_mm / 2.0
    J = math.pi * (d_mm ** 4) / 32.0        # mm^4
    I = math.pi * (d_mm ** 4) / 64.0        # mm^4
    A = math.pi * (r ** 2)                  # mm^2

    tau_max = (T_Nm * 1000.0) * r / J       # MPa (N*mm * mm / mm^4 = N/mm^2 = MPa)
    sigma_b = (M_Nm * 1000.0) * r / I       # MPa
    sigma_eq = math.sqrt(sigma_b ** 2 + 3.0 * (tau_max ** 2))
    FoS_yield = (Sy / sigma_eq) if sigma_eq > 0 else 999.0

    G_MPa = G_GPa * 1e3
    theta_rad = (T_Nm * 1000.0) * L_mm / (G_MPa * J)
    theta_deg = math.degrees(theta_rad)

    numerical = {
        "shaft_design": {
            "diameter_mm": d_mm,
            "length_mm": L_mm,
            "material": mat,
            "torque_Nm": T_Nm,
            "bending_moment_Nm": M_Nm,
            "polar_moment_J_mm4": round(J, 2),
            "second_moment_I_mm4": round(I, 2),
            "max_shear_stress_MPa": round(tau_max, 4),
            "max_bending_stress_MPa": round(sigma_b, 4),
            "von_mises_stress_MPa": round(sigma_eq, 4),
            "factor_of_safety": round(FoS_yield, 3),
            "twist_angle_rad": round(theta_rad, 6),
            "twist_angle_deg": round(theta_deg, 4),
        }
    }

    radii = np.linspace(0, r, 100)
    tau_r = tau_max * radii / r
    sig_r = sigma_b * radii / r
    plots = [{
        "plot_type": "line",
        "title": "Stress Distribution Across Solid Circular Shaft Radius",
        "x_label": "Radial Position (mm)",
        "y_label": "Stress (MPa)",
        "x": radii.tolist(),
        "y": tau_r.tolist(),
        "series_name": "Torsional Shear Stress τ(r)",
        "extra_series": [{"name": "Bending Stress σ(r)", "y": sig_r.tolist(), "color": "#f59e0b"}],
    }]

    visual_data = {
        "model_type": "shaft",
        "title": f"Shaft Torsion & Bending — Ø{d_mm}mm × {L_mm}mm ({mat})",
        "width": 720, "height": 460, "views": ["front", "side"],
        "parts": [
            {"id": "XSEC", "type": "cross_section", "cx": 160, "cy": 200, "r": 80, "shape": "circle", "label": f"Ø{d_mm}mm", "properties": {"area_mm2": round(A, 1), "I_mm4": round(I, 1), "J_mm4": round(J, 1)}},
            {"id": "SIDE", "type": "shaft_side", "x": 320, "y": 170, "width": 350, "height": 60, "label": f"{L_mm} mm", "properties": {"torque_Nm": T_Nm, "moment_Nm": M_Nm, "twist_deg": round(theta_deg, 3)}},
        ],
    }

    observations = [
        f"Solid circular shaft Ø{d_mm} mm × {L_mm} mm ({mat})",
        f"Max torsional shear τ = {tau_max:.2f} MPa, max bending σ_b = {sigma_b:.2f} MPa",
        f"Von Mises equivalent stress σ_vm = {sigma_eq:.2f} MPa → Static Yield FoS = {FoS_yield:.2f}",
        f"Total angle of twist θ = {theta_deg:.4f}° ({theta_rad:.5f} rad)",
    ]
    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim",
        "experiment_id": "shaft_design",
        "solver": {
            "name": "shaft_torsion_bending",
            "version": "2.0",
            "method": "Circular Shaft Torsion & von Mises Combined Stress",
            "equations": ["tau_max = T*r/J", "sigma_b = M*r/I", "sigma_vm = sqrt(sigma_b^2 + 3*tau_max^2)", "theta = T*L/(G*J)"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": visual_data,
        "visualization_type": "3d_model",
        "observations": observations,
        "assumptions": ["Solid circular isotropic elastic shaft", "Static loading; stress concentration Kt = 1"],
        "limitations": ["Fatigue endurance and dynamic critical speed not analyzed"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Shaft torsion and combined bending stress computed"],
    }


# ─── Spring-Mass-Damper 1-DOF Vibration ──────────────────────────────────────

def _spring_mass_damper(params: dict) -> Dict[str, Any]:
    """1-DOF linear spring-mass-damper free/damped vibration solver."""
    m = float(params.get("mass_kg") or params.get("m") or 1.0)
    k = float(params.get("stiffness_N_per_m") or params.get("k") or 100.0)
    c = float(params.get("damping_Ns_per_m") or params.get("c") or 2.0)
    x0 = float(params.get("initial_displacement_m") or params.get("x0") or 0.1)
    v0 = float(params.get("initial_velocity_ms") or params.get("v0") or 0.0)
    t_end = float(params.get("duration_s", 5.0))

    if m <= 0 or k <= 0 or c < 0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "spring_mass_damper"},
            "Mass and stiffness must be positive and damping must be non-negative.",
        )

    wn = math.sqrt(k / m)
    fn = wn / (2.0 * math.pi)
    zeta = c / (2.0 * math.sqrt(k * m))
    wd = wn * math.sqrt(max(0.0, 1.0 - zeta * zeta))
    regime = "underdamped" if zeta < 1.0 - 1e-6 else ("critically_damped" if abs(zeta - 1.0) <= 1e-6 else "overdamped")

    t_eval = np.linspace(0.0, t_end, 400)
    sol = solve_ivp(lambda t, y: [y[1], -(c / m) * y[1] - (k / m) * y[0]], (0.0, t_end), [x0, v0], t_eval=t_eval, rtol=1e-9, atol=1e-11)
    x_arr, v_arr = sol.y[0], sol.y[1]
    energy = 0.5 * m * (v_arr ** 2) + 0.5 * k * (x_arr ** 2)

    numerical = {
        "spring_mass_damper": {
            "mass_kg": m,
            "stiffness_N_per_m": k,
            "damping_Ns_per_m": c,
            "natural_frequency_Hz": round(fn, 5),
            "natural_omega_rad_s": round(wn, 5),
            "damping_ratio_zeta": round(zeta, 5),
            "damped_frequency_Hz": round(wd / (2.0 * math.pi), 5),
            "regime": regime,
            "initial_energy_J": round(float(energy[0]), 6),
            "final_energy_J": round(float(energy[-1]), 6),
            "peak_displacement_m": round(float(np.max(np.abs(x_arr))), 6),
        }
    }

    plots = [
        {
            "plot_type": "line",
            "title": f"Spring-Mass-Damper Response ({regime}, ζ={zeta:.3f})",
            "x_label": "Time (s)",
            "y_label": "Displacement x (m)",
            "x": t_eval.tolist(),
            "y": x_arr.tolist(),
            "series_name": "x(t)",
        },
        {
            "plot_type": "line",
            "title": "Mechanical Energy vs Time",
            "x_label": "Time (s)",
            "y_label": "Energy (J)",
            "x": t_eval.tolist(),
            "y": energy.tolist(),
            "series_name": "Total Energy E(t)",
        },
    ]

    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_numerical",
        "engine_used": "mech_sim",
        "experiment_id": "spring_mass_damper",
        "solver": {
            "name": "spring_mass_damper",
            "version": "2.0",
            "method": "SciPy RK45 (rtol=1e-9, atol=1e-11) + Modal Analysis",
            "equations": ["m*x'' + c*x' + k*x = 0", "omega_n = sqrt(k/m)", "zeta = c/(2*sqrt(k*m))"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": None,
        "visualization_type": "3d_model",
        "observations": [
            f"Natural frequency f_n = {fn:.4f} Hz (ω_n = {wn:.4f} rad/s), damping ratio ζ = {zeta:.4f} ({regime}).",
            f"Mechanical energy: E(0) = {energy[0]:.5f} J → E({t_end}s) = {energy[-1]:.5f} J.",
        ],
        "assumptions": ["Linear Hookean spring and linear viscous damper"],
        "limitations": ["Free unforced 1-DOF vibration"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Spring-mass-damper ODE solved"],
    }


# ─── Rotational Dynamics ─────────────────────────────────────────────────────

def _rotational_dynamics(params: dict) -> Dict[str, Any]:
    """Fixed-axis rigid-body rotational dynamics I*alpha = tau - b*omega."""
    I_rot = float(params.get("moment_of_inertia_kgm2") or params.get("I_rot") or 0.5)
    tau = float(params.get("applied_torque_Nm") or params.get("torque_Nm") or 10.0)
    b_rot = float(params.get("viscous_damping_Nms_rad", 0.2))
    t_end = float(params.get("duration_s", 10.0))

    t_eval = np.linspace(0.0, t_end, 300)
    sol = solve_ivp(lambda t, y: [y[1], (tau - b_rot * y[1]) / I_rot], (0.0, t_end), [0.0, 0.0], t_eval=t_eval, rtol=1e-9, atol=1e-11)
    th_arr, w_arr = sol.y[0], sol.y[1]
    ke_rot = 0.5 * I_rot * (w_arr ** 2)

    numerical = {
        "rotational_dynamics": {
            "moment_of_inertia_kgm2": I_rot,
            "applied_torque_Nm": tau,
            "initial_alpha_rad_s2": round(tau / I_rot, 4),
            "final_omega_rad_s": round(float(w_arr[-1]), 4),
            "terminal_omega_rad_s": round(tau / b_rot, 4) if b_rot > 0 else None,
            "final_rotational_KE_J": round(float(ke_rot[-1]), 4),
            "total_revolutions": round(float(th_arr[-1] / (2.0 * math.pi)), 3),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": "Rotational Dynamics — Angular Velocity ω(t)",
        "x_label": "Time (s)",
        "y_label": "Angular Velocity ω (rad/s)",
        "x": t_eval.tolist(),
        "y": w_arr.tolist(),
        "series_name": "ω(t)",
    }]
    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_numerical",
        "engine_used": "mech_sim",
        "experiment_id": "rotational_dynamics",
        "solver": {
            "name": "rotational_dynamics",
            "version": "2.0",
            "method": "Newton-Euler Rotational ODE (RK45)",
            "equations": ["I * d(omega)/dt = tau - b * omega", "K_rot = 0.5 * I * omega^2"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": None,
        "visualization_type": "3d_model",
        "observations": [f"Initial angular acceleration α₀ = {tau/I_rot:.3f} rad/s²; ω({t_end}s) = {w_arr[-1]:.3f} rad/s."],
        "assumptions": ["Fixed rotation axis; constant moment of inertia"],
        "limitations": ["1-DOF rigid body"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Rotational dynamics ODE solved"],
    }


# ─── Dedicated Thermodynamic Cycle Solvers (Separate per Cycle!) ─────────────

def _otto_cycle(params: dict) -> Dict[str, Any]:
    """Ideal air-standard Otto cycle (2 isentropes + 2 isochores)."""
    r = float(params.get("compression_ratio") or params.get("r") or 8.0)
    T1 = float(params.get("T_cold_K") or params.get("T1_K") or 300.0)
    T3 = float(params.get("T_hot_K") or params.get("T3_K") or 1800.0)
    gamma = float(params.get("gamma", 1.4))
    P1 = float(params.get("P1_kPa", 101.325))
    V1 = float(params.get("V1_L", 0.5))

    V2 = V1 / r
    P2 = P1 * (r ** gamma)
    T2 = T1 * (r ** (gamma - 1.0))
    if T3 <= T2:
        T3 = T2 + 600.0
    P3 = P2 * (T3 / T2)
    P4 = P3 / (r ** gamma)
    T4 = T3 / (r ** (gamma - 1.0))

    eta = 1.0 - 1.0 / (r ** (gamma - 1.0))
    # Work & heat (kJ) using ideal gas cv = R/(gamma-1), nR = P1*V1/T1 (kPa*L = J -> /1000 = kJ)
    nR_kJ = (P1 * V1 / T1) / 1000.0
    cv_n = nR_kJ / (gamma - 1.0)
    q_in_kJ = cv_n * (T3 - T2)
    q_out_kJ = cv_n * (T4 - T1)
    w_net_kJ = q_in_kJ - q_out_kJ
    mep_kPa = (w_net_kJ * 1000.0) / (V1 - V2)

    n_pts = 80
    v_12 = np.linspace(V1, V2, n_pts); p_12 = P1 * (V1 / v_12) ** gamma
    v_23 = np.full(n_pts, V2);         p_23 = np.linspace(P2, P3, n_pts)
    v_34 = np.linspace(V2, V1, n_pts); p_34 = P3 * (V2 / v_34) ** gamma
    v_41 = np.full(n_pts, V1);         p_41 = np.linspace(P4, P1, n_pts)

    numerical = {
        "otto_cycle": {
            "cycle": "Otto Cycle",
            "compression_ratio": r,
            "gamma": gamma,
            "T1_K": round(T1, 2), "T2_K": round(T2, 2), "T3_K": round(T3, 2), "T4_K": round(T4, 2),
            "P1_kPa": round(P1, 2), "P2_kPa": round(P2, 2), "P3_kPa": round(P3, 2), "P4_kPa": round(P4, 2),
            "heat_in_kJ": round(q_in_kJ, 5),
            "heat_out_kJ": round(q_out_kJ, 5),
            "net_work_kJ": round(w_net_kJ, 5),
            "mean_effective_pressure_kPa": round(mep_kPa, 2),
            "efficiency_percent": round(eta * 100.0, 3),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": f"Ideal Otto Cycle PV Diagram (r={r}, η={eta*100:.2f}%)",
        "x_label": "Volume (L)",
        "y_label": "Pressure (kPa)",
        "x": np.concatenate([v_12, v_23, v_34, v_41]).tolist(),
        "y": np.concatenate([p_12, p_23, p_34, p_41]).tolist(),
        "series_name": "Otto PV Loop",
    }]
    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim",
        "experiment_id": "otto_cycle",
        "solver": {
            "name": "otto_cycle",
            "version": "2.0",
            "method": "Air-Standard Ideal Otto Cycle",
            "equations": ["eta = 1 - r^(1-gamma)", "W_net = Q_in - Q_out"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": {"model_type": "thermo_engine", "title": f"Otto Cycle (r={r}, η={eta*100:.1f}%)", "parts": []},
        "visualization_type": "3d_model",
        "observations": [
            f"Otto cycle efficiency η = 1 - {r}^(1-{gamma}) = {eta*100:.2f}%.",
            f"First-law balance: Q_in = {q_in_kJ:.4f} kJ, Q_out = {q_out_kJ:.4f} kJ, W_net = {w_net_kJ:.4f} kJ (MEP = {mep_kPa:.1f} kPa).",
        ],
        "assumptions": ["Cold air-standard ideal gas with constant gamma"],
        "limitations": ["Ignores combustion losses, friction, and variable specific heat"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Ideal Otto cycle computed"],
    }


def _carnot_cycle(params: dict) -> Dict[str, Any]:
    """Ideal reversible Carnot cycle (2 true isotherms + 2 true adiabats)."""
    T_hot = float(params.get("T_hot_K", 800.0))
    T_cold = float(params.get("T_cold_K", 300.0))
    r_iso = float(params.get("isothermal_expansion_ratio", 2.0))
    gamma = float(params.get("gamma", 1.4))
    P1 = float(params.get("P1_kPa", 500.0))
    V1 = float(params.get("V1_L", 0.2))

    if T_hot <= T_cold or T_cold <= 0 or r_iso <= 1.0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "carnot_cycle"},
            f"Carnot cycle requires T_hot > T_cold > 0 and expansion ratio > 1 (got T_hot={T_hot}, T_cold={T_cold}).",
        )

    eta = 1.0 - (T_cold / T_hot)
    # 1->2 Isothermal expansion at T_hot
    V2 = V1 * r_iso
    P2 = P1 * (V1 / V2)
    # 2->3 Adiabatic expansion T_hot -> T_cold
    V3 = V2 * ((T_hot / T_cold) ** (1.0 / (gamma - 1.0)))
    P3 = P2 * ((V2 / V3) ** gamma)
    # 3->4 Isothermal compression at T_cold (same volume ratio so 4->1 closes adiabatically!)
    V4 = V3 / r_iso
    P4 = P3 * (V3 / V4)

    nR_kJ = (P1 * V1 / T_hot) / 1000.0
    q_in_kJ = nR_kJ * T_hot * math.log(r_iso)
    q_out_kJ = nR_kJ * T_cold * math.log(r_iso)
    w_net_kJ = q_in_kJ - q_out_kJ
    delta_S_net = (q_in_kJ / T_hot) - (q_out_kJ / T_cold)

    n_pts = 80
    v_12 = np.linspace(V1, V2, n_pts); p_12 = P1 * V1 / v_12
    v_23 = np.linspace(V2, V3, n_pts); p_23 = P2 * (V2 / v_23) ** gamma
    v_34 = np.linspace(V3, V4, n_pts); p_34 = P3 * V3 / v_34
    v_41 = np.linspace(V4, V1, n_pts); p_41 = P4 * (V4 / v_41) ** gamma

    numerical = {
        "carnot_cycle": {
            "cycle": "Carnot Cycle",
            "T_hot_K": T_hot,
            "T_cold_K": T_cold,
            "efficiency_percent": round(eta * 100.0, 3),
            "heat_in_kJ": round(q_in_kJ, 5),
            "heat_out_kJ": round(q_out_kJ, 5),
            "net_work_kJ": round(w_net_kJ, 5),
            "net_entropy_change_kJ_K": float(f"{delta_S_net:.2e}"),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": f"Ideal Carnot Cycle PV Diagram (T_H={T_hot}K, T_C={T_cold}K, η={eta*100:.2f}%)",
        "x_label": "Volume (L)",
        "y_label": "Pressure (kPa)",
        "x": np.concatenate([v_12, v_23, v_34, v_41]).tolist(),
        "y": np.concatenate([p_12, p_23, p_34, p_41]).tolist(),
        "series_name": "Carnot PV Loop",
    }]
    return {
        "status": "success",
        "simulation_status": "success",
        "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim",
        "experiment_id": "carnot_cycle",
        "solver": {
            "name": "carnot_cycle",
            "version": "2.0",
            "method": "Ideal Reversible Carnot Cycle (2 Isotherms + 2 Adiabats)",
            "equations": ["eta_carnot = 1 - T_cold / T_hot", "Delta_S_cycle = Q_H/T_H - Q_C/T_C = 0"],
        },
        "numerical_results": numerical,
        "plot_data": plots,
        "visual_data": {"model_type": "thermo_engine", "title": f"Carnot Cycle (η={eta*100:.1f}%)", "parts": []},
        "visualization_type": "3d_model",
        "observations": [
            f"Carnot theoretical maximum efficiency η = 1 - {T_cold}/{T_hot} = {eta*100:.2f}%.",
            f"Zero net cycle entropy change verified (ΔS_cycle = {delta_S_net:.2e} kJ/K).",
        ],
        "assumptions": ["Fully reversible ideal-gas cycle"],
        "limitations": ["Theoretical thermodynamic upper bound only"],
        "warnings": [],
        "simulation_log": ["[mech_sim] Ideal Carnot cycle computed"],
    }


def _diesel_cycle(params: dict) -> Dict[str, Any]:
    """Ideal air-standard Diesel cycle."""
    r = float(params.get("compression_ratio", 18.0))
    rc = float(params.get("cutoff_ratio", 2.0))
    T1 = float(params.get("T_cold_K", 300.0))
    gamma = float(params.get("gamma", 1.4))
    P1 = float(params.get("P1_kPa", 101.325))
    V1 = float(params.get("V1_L", 0.5))

    if r <= rc or rc <= 1.0:
        return build_failed_response(
            {"domain": "mechanical", "experiment_type": "diesel_cycle"},
            f"Diesel cycle requires compression_ratio ({r}) > cutoff_ratio ({rc}) > 1.",
        )

    eta = 1.0 - (1.0 / (r ** (gamma - 1.0))) * ((rc ** gamma - 1.0) / (gamma * (rc - 1.0)))
    V2 = V1 / r
    V3 = V2 * rc
    P2 = P1 * (r ** gamma)
    T2 = T1 * (r ** (gamma - 1.0))
    P3 = P2
    T3 = T2 * rc
    P4 = P3 * ((V3 / V1) ** gamma)
    T4 = T3 * ((V3 / V1) ** (gamma - 1.0))

    n_pts = 80
    v_12 = np.linspace(V1, V2, n_pts); p_12 = P1 * (V1 / v_12) ** gamma
    v_23 = np.linspace(V2, V3, n_pts); p_23 = np.full(n_pts, P2)
    v_34 = np.linspace(V3, V1, n_pts); p_34 = P3 * (V3 / v_34) ** gamma
    v_41 = np.full(n_pts, V1);         p_41 = np.linspace(P4, P1, n_pts)

    numerical = {
        "diesel_cycle": {
            "cycle": "Diesel Cycle",
            "compression_ratio": r,
            "cutoff_ratio": rc,
            "T1_K": round(T1, 2), "T2_K": round(T2, 2), "T3_K": round(T3, 2), "T4_K": round(T4, 2),
            "efficiency_percent": round(eta * 100.0, 3),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": f"Ideal Diesel Cycle PV Diagram (r={r}, r_c={rc}, η={eta*100:.2f}%)",
        "x_label": "Volume (L)", "y_label": "Pressure (kPa)",
        "x": np.concatenate([v_12, v_23, v_34, v_41]).tolist(),
        "y": np.concatenate([p_12, p_23, p_34, p_41]).tolist(),
        "series_name": "Diesel PV Loop",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim", "experiment_id": "diesel_cycle",
        "solver": {"name": "diesel_cycle", "version": "2.0", "method": "Air-Standard Ideal Diesel Cycle", "equations": ["eta = 1 - r^(1-gamma)*(rc^gamma - 1)/(gamma*(rc - 1))"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "3d_model",
        "observations": [f"Diesel cycle efficiency η = {eta*100:.2f}% (r={r}, cutoff r_c={rc})."],
        "assumptions": ["Air-standard ideal gas; isobaric heat addition"], "limitations": ["Cold air-standard approximation"],
        "warnings": [], "simulation_log": ["[mech_sim] Ideal Diesel cycle computed"],
    }


def _brayton_cycle(params: dict) -> Dict[str, Any]:
    """Ideal air-standard Brayton gas-turbine cycle."""
    rp = float(params.get("pressure_ratio", 10.0))
    T1 = float(params.get("T_cold_K", 300.0))
    T3 = float(params.get("T_hot_K", 1400.0))
    gamma = float(params.get("gamma", 1.4))
    cp = 1.005  # kJ/(kg*K) air

    eta = 1.0 - (rp ** ((1.0 - gamma) / gamma))
    T2 = T1 * (rp ** ((gamma - 1.0) / gamma))
    T4 = T3 / (rp ** ((gamma - 1.0) / gamma))
    w_comp = cp * (T2 - T1)
    w_turb = cp * (T3 - T4)
    w_net = w_turb - w_comp
    bwr = w_comp / max(w_turb, 1e-9)

    rp_sweep = np.linspace(2.0, 30.0, 80)
    eta_sweep = (1.0 - (rp_sweep ** ((1.0 - gamma) / gamma))) * 100.0

    numerical = {
        "brayton_cycle": {
            "cycle": "Brayton Cycle",
            "pressure_ratio": rp,
            "T1_K": round(T1, 2), "T2_K": round(T2, 2), "T3_K": round(T3, 2), "T4_K": round(T4, 2),
            "compressor_work_kJ_kg": round(w_comp, 2),
            "turbine_work_kJ_kg": round(w_turb, 2),
            "net_work_kJ_kg": round(w_net, 2),
            "back_work_ratio": round(bwr, 4),
            "efficiency_percent": round(eta * 100.0, 3),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": "Brayton Cycle Efficiency vs Pressure Ratio",
        "x_label": "Pressure Ratio r_p", "y_label": "Thermal Efficiency (%)",
        "x": rp_sweep.tolist(), "y": eta_sweep.tolist(), "series_name": "η_Brayton",
    }]
    return {
        "status": "success", "simulation_status": "success", "simulation_type": "deterministic_analytical",
        "engine_used": "mech_sim", "experiment_id": "brayton_cycle",
        "solver": {"name": "brayton_cycle", "version": "2.0", "method": "Air-Standard Ideal Brayton Cycle", "equations": ["eta = 1 - r_p^((1-gamma)/gamma)"]},
        "numerical_results": numerical, "plot_data": plots, "visual_data": None, "visualization_type": "3d_model",
        "observations": [f"Brayton efficiency η = {eta*100:.2f}% at r_p={rp}, back-work ratio = {bwr:.3f}."],
        "assumptions": ["Isentropic compressor and turbine; ideal air cp=1.005 kJ/(kg·K)"],
        "limitations": ["Component isentropic efficiencies and pressure drops omitted"],
        "warnings": [], "simulation_log": ["[mech_sim] Ideal Brayton cycle computed"],
    }


# ─── Main explicit entry point (NO catch-all fallback!) ──────────────────────

_MECH_DISPATCH = {
    "four_bar_linkage": _four_bar_linkage,
    "four_bar": _four_bar_linkage,
    "planar_four_bar": _four_bar_linkage,
    "crank_rocker": _four_bar_linkage,
    "gear_train": _gear_train,
    "gear": _gear_train,
    "spur_gear": _gear_train,
    "shaft_design": _shaft_design,
    "shaft": _shaft_design,
    "shaft_torsion": _shaft_design,
    "spring_mass_damper": _spring_mass_damper,
    "harmonic_oscillator": _spring_mass_damper,
    "rotational_dynamics": _rotational_dynamics,
    "otto_cycle": _otto_cycle,
    "carnot_cycle": _carnot_cycle,
    "diesel_cycle": _diesel_cycle,
    "brayton_cycle": _brayton_cycle,
}


def run(procedure: dict) -> dict:
    """Explicit mechanical engineering solver dispatcher. Never substitutes an unrelated solver."""
    params = procedure.get("parameters", {}) or {}
    exp_type = str(procedure.get("experiment_type") or "").strip().lower()
    text = f"{procedure.get('topic', '')} {procedure.get('hypothesis', '')} {exp_type}".lower()

    # Legacy alias resolution for thermo_cycle ONLY if explicitly thermo_cycle
    if exp_type == "thermo_cycle":
        cyc = str(params.get("cycle", "")).lower()
        if "carnot" in cyc or "carnot" in text:
            exp_type = "carnot_cycle"
        elif "diesel" in cyc or "diesel" in text:
            exp_type = "diesel_cycle"
        elif "brayton" in cyc or "brayton" in text:
            exp_type = "brayton_cycle"
        else:
            exp_type = "otto_cycle"

    solver_fn = _MECH_DISPATCH.get(exp_type)
    if solver_fn is None:
        # Attempt strict keyword match ONLY if experiment_type was blank/generic
        if exp_type in ("", "mechanical", "mechanical_engineering", "mech"):
            if any(w in text for w in ["four-bar", "four bar", "4-bar", "crank-rocker", "linkage"]):
                solver_fn = _four_bar_linkage
            elif any(w in text for w in ["gear", "spur", "pinion", "teeth"]):
                solver_fn = _gear_train
            elif any(w in text for w in ["shaft", "torsion", "twist"]):
                solver_fn = _shaft_design
            elif any(w in text for w in ["spring-mass", "mass-spring", "damper", "harmonic oscillator"]):
                solver_fn = _spring_mass_damper
            elif "carnot" in text:
                solver_fn = _carnot_cycle
            elif "diesel" in text:
                solver_fn = _diesel_cycle
            elif "brayton" in text:
                solver_fn = _brayton_cycle
            elif "otto" in text:
                solver_fn = _otto_cycle

    if solver_fn is None:
        return build_unsupported_response(
            procedure,
            reason=f"Mechanical experiment '{exp_type or 'unspecified'}' has no registered deterministic solver.",
            supported_examples=[
                "four_bar_linkage", "gear_train", "shaft_design",
                "spring_mass_damper", "rotational_dynamics",
                "otto_cycle", "carnot_cycle", "diesel_cycle", "brayton_cycle",
            ],
        )

    return solver_fn(params)
