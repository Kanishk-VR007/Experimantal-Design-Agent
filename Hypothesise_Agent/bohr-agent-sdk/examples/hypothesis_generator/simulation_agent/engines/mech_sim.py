"""
Mechanical Engineering Simulation Engine
==========================================
Handles: gear trains, shaft design, thermodynamic cycles, 3D-print-style CAD.

Returns numerical data + plot data + visual_data (3d_model / CAD layout)
for isometric / multi-view SVG rendering in the frontend.
"""

import numpy as np
import math


# ─── Gear-train analysis ─────────────────────────────────────────────────

def _gear_train(params):
    """Spur gear train analysis with 3-view visual data."""
    N1       = params.get("teeth_driver", 20)
    N2       = params.get("teeth_driven", 40)
    module   = params.get("module_mm", 2.5)
    rpm_in   = params.get("rpm_input", 1500)
    power_kW = params.get("power_kW", 5.0)
    pressure_angle = params.get("pressure_angle_deg", 20)

    ratio   = N2 / N1
    rpm_out = rpm_in / ratio

    d1 = N1 * module       # pitch diameter driver (mm)
    d2 = N2 * module       # pitch diameter driven (mm)
    centre_dist = (d1 + d2) / 2

    # Torque
    T_in  = (power_kW * 1000 * 60) / (2 * math.pi * rpm_in)   # N·m
    T_out = T_in * ratio * 0.97   # assuming 97% efficiency

    # Tangential force
    Ft = T_in / (d1 / 2 / 1000)  # N
    Fr = Ft * math.tan(math.radians(pressure_angle))

    # Lewis bending stress (rough)
    b  = params.get("face_width_mm", 25)
    Y  = 0.32   # form factor approx.
    sigma_b = Ft / (b * module * Y)   # MPa

    numerical = {
        "gear_train": {
            "gear_ratio":          f"{N2}:{N1} = {round(ratio,2)}",
            "module_mm":           module,
            "teeth_driver":        N1,
            "teeth_driven":        N2,
            "pitch_dia_driver_mm": round(d1, 1),
            "pitch_dia_driven_mm": round(d2, 1),
            "centre_distance_mm":  round(centre_dist, 1),
            "rpm_input":           rpm_in,
            "rpm_output":          round(rpm_out, 1),
            "torque_input_Nm":     round(T_in, 2),
            "torque_output_Nm":    round(T_out, 2),
            "tangential_force_N":  round(Ft, 1),
            "radial_force_N":      round(Fr, 1),
            "bending_stress_MPa":  round(sigma_b, 1),
        }
    }

    # Torque-speed characteristic
    rpms = np.linspace(100, rpm_in * 1.2, 60)
    torques = (power_kW * 1000 * 60) / (2 * math.pi * rpms)
    plots = [{
        "plot_type": "line",
        "title": "Torque vs Speed (constant power)",
        "x_label": "Speed (RPM)",
        "y_label": "Torque (N·m)",
        "x": rpms.tolist(),
        "y": torques.tolist(),
        "series_name": "Input Shaft",
    }]

    # ── 3D-model visual: top view of gear mesh ──────────────────
    cx1, cy1 = 250, 220   # driver centre
    r1 = d1 / 2 * 1.8     # scale for display
    r2 = d2 / 2 * 1.8
    cx2 = cx1 + r1 + r2
    cy2 = cy1

    visual_data = {
        "model_type": "gear_train",
        "title": f"Spur Gear Train — {N1}T / {N2}T  (m={module}mm)",
        "width": 720,
        "height": 460,
        "views": ["top"],            # which projection views to render
        "parts": [
            {
                "id": "GEAR1", "type": "gear",
                "cx": cx1, "cy": cy1, "r": r1,
                "teeth": N1, "module": module,
                "label": f"Driver  {N1}T  Ø{round(d1,1)}mm",
                "direction": "cw",
                "properties": {
                    "pitch_dia_mm": round(d1, 1), "rpm": rpm_in,
                    "torque_Nm": round(T_in, 2),
                },
            },
            {
                "id": "GEAR2", "type": "gear",
                "cx": cx2, "cy": cy2, "r": r2,
                "teeth": N2, "module": module,
                "label": f"Driven  {N2}T  Ø{round(d2,1)}mm",
                "direction": "ccw",
                "properties": {
                    "pitch_dia_mm": round(d2, 1), "rpm": round(rpm_out, 1),
                    "torque_Nm": round(T_out, 2),
                },
            },
            {
                "id": "SHAFT1", "type": "shaft",
                "cx": cx1, "cy": cy1, "length": 60,
                "label": "Input Shaft",
                "properties": {"rpm": rpm_in, "torque_Nm": round(T_in, 2)},
            },
            {
                "id": "SHAFT2", "type": "shaft",
                "cx": cx2, "cy": cy2, "length": 60,
                "label": "Output Shaft",
                "properties": {"rpm": round(rpm_out, 1), "torque_Nm": round(T_out, 2)},
            },
        ],
        "dimensions": [
            {"id": "DIM_CD", "from_id": "GEAR1", "to_id": "GEAR2",
             "label": f"C/D = {round(centre_dist,1)} mm",
             "x1": cx1, "y1": cy1 + r1 + 50, "x2": cx2, "y2": cy2 + r2 + 50},
        ],
        "annotations": [
            {"x": cx1, "y": cy1 - r1 - 25,
             "text": f"{rpm_in} RPM  →  {round(rpm_out,1)} RPM", "color": "#60a5fa"},
            {"x": (cx1 + cx2) / 2, "y": cy1 + max(r1, r2) + 75,
             "text": f"Ratio {round(ratio,2)}:1 — η 97%", "color": "#a78bfa"},
        ],
    }

    observations = [
        f"Gear ratio = {N2}:{N1} = {round(ratio,2)}:1",
        f"Speed: {rpm_in} → {round(rpm_out,1)} RPM",
        f"Torque: {round(T_in,2)} → {round(T_out,2)} N·m (97% efficiency)",
        f"Centre distance = {round(centre_dist,1)} mm",
        f"Bending stress ≈ {round(sigma_b,1)} MPa (Lewis equation)",
    ]
    return numerical, plots, visual_data, observations


# ─── Shaft design ─────────────────────────────────────────────────────────

def _shaft_design(params):
    """Solid circular shaft under combined loading."""
    T_Nm    = params.get("torque_Nm", 200)
    M_Nm    = params.get("bending_moment_Nm", 150)
    L_mm    = params.get("length_mm", 500)
    d_mm    = params.get("diameter_mm", 40)
    mat     = params.get("material", "AISI 1045 Steel")
    Sut     = params.get("ultimate_strength_MPa", 570)  # AISI 1045
    Sy      = params.get("yield_strength_MPa", 310)

    r  = d_mm / 2
    J  = math.pi * d_mm ** 4 / 32               # mm⁴ polar moment
    I  = math.pi * d_mm ** 4 / 64               # mm⁴ second moment
    A  = math.pi * r ** 2

    tau_max = T_Nm * 1000 * r / J               # MPa
    sigma_b = M_Nm * 1000 * r / I               # MPa
    sigma_eq = math.sqrt(sigma_b ** 2 + 3 * tau_max ** 2)   # von-Mises

    FoS_yield = Sy / sigma_eq if sigma_eq > 0 else float('inf')

    # Twist angle  θ = T·L / (G·J)
    G = params.get("shear_modulus_GPa", 80) * 1e3   # MPa
    theta_rad = T_Nm * 1000 * L_mm / (G * J)
    theta_deg = math.degrees(theta_rad)

    numerical = {
        "shaft_design": {
            "diameter_mm":         d_mm,
            "length_mm":           L_mm,
            "material":            mat,
            "torque_Nm":           T_Nm,
            "bending_moment_Nm":   M_Nm,
            "max_shear_stress_MPa": round(tau_max, 2),
            "max_bending_stress_MPa": round(sigma_b, 2),
            "von_mises_stress_MPa": round(sigma_eq, 2),
            "factor_of_safety":    round(FoS_yield, 2),
            "twist_angle_deg":     round(theta_deg, 3),
        }
    }

    # Stress distribution across cross-section
    radii = np.linspace(0, r, 100)
    tau_r  = tau_max * radii / r
    sig_r  = sigma_b * radii / r

    plots = [
        {
            "plot_type": "line",
            "title": "Stress Distribution Across Shaft Radius",
            "x_label": "Radial Position (mm)",
            "y_label": "Stress (MPa)",
            "x": radii.tolist(),
            "y": tau_r.tolist(),
            "series_name": "Shear Stress τ",
            "extra_series": [{"name": "Bending Stress σ", "y": sig_r.tolist()}],
        },
    ]

    # ── 3D-model visual: shaft cross-section + side view ─────────
    shaft_cx, shaft_cy = 360, 200
    shaft_r_px = 80
    shaft_len_px = 350

    visual_data = {
        "model_type": "shaft",
        "title": f"Shaft Design — Ø{d_mm}mm × {L_mm}mm  ({mat})",
        "width": 720,
        "height": 460,
        "views": ["front", "side"],
        "parts": [
            # Cross-section view (left)
            {
                "id": "XSEC", "type": "cross_section",
                "cx": 160, "cy": 200, "r": shaft_r_px,
                "shape": "circle",
                "label": f"Ø{d_mm}mm",
                "properties": {
                    "area_mm2": round(A, 1),
                    "I_mm4": round(I, 1),
                    "J_mm4": round(J, 1),
                },
            },
            # Side view (right)
            {
                "id": "SIDE", "type": "shaft_side",
                "x": 320, "y": 170, "width": shaft_len_px, "height": 60,
                "label": f"{L_mm} mm",
                "properties": {
                    "torque_Nm": T_Nm, "moment_Nm": M_Nm,
                    "twist_deg": round(theta_deg, 3),
                },
            },
            # Torque arrow
            {
                "id": "TORQ", "type": "torque_arrow",
                "cx": 320, "cy": 200,
                "label": f"T = {T_Nm} N·m",
                "properties": {},
            },
            # Bending arrow
            {
                "id": "BEND", "type": "moment_arrow",
                "cx": 320 + shaft_len_px, "cy": 200,
                "label": f"M = {M_Nm} N·m",
                "properties": {},
            },
        ],
        "dimensions": [
            {"id": "DIM_L", "x1": 320, "y1": 260, "x2": 320 + shaft_len_px, "y2": 260,
             "label": f"{L_mm} mm"},
            {"id": "DIM_D", "x1": 160 - shaft_r_px - 30, "y1": 200 - shaft_r_px,
             "x2": 160 - shaft_r_px - 30, "y2": 200 + shaft_r_px,
             "label": f"Ø{d_mm}"},
        ],
        "annotations": [
            {"x": 360, "y": 350,
             "text": f"σ_eq = {round(sigma_eq,1)} MPa — FoS = {round(FoS_yield,2)}", "color": "#f59e0b"},
            {"x": 360, "y": 380,
             "text": f"Twist = {round(theta_deg,3)}°", "color": "#a78bfa"},
        ],
    }

    observations = [
        f"Shaft: Ø{d_mm}mm × {L_mm}mm — {mat}",
        f"Max shear stress = {round(tau_max,2)} MPa, bending stress = {round(sigma_b,2)} MPa",
        f"Von-Mises equivalent stress = {round(sigma_eq,2)} MPa",
        f"Factor of Safety = {round(FoS_yield,2)} (yield based)",
        f"Angle of twist = {round(theta_deg,3)}° over {L_mm}mm",
    ]
    return numerical, plots, visual_data, observations


# ─── Thermodynamic cycle ──────────────────────────────────────────────────

def _thermo_cycle(params):
    """Otto or Carnot cycle PV / TS diagrams."""
    cycle_type = params.get("cycle", "otto")
    T_hot      = params.get("T_hot_K", 1200)
    T_cold     = params.get("T_cold_K", 300)
    r          = params.get("compression_ratio", 8)
    gamma      = params.get("gamma", 1.4)    # specific heat ratio
    P1         = params.get("P1_kPa", 101.325)
    V1         = params.get("V1_L", 0.5)     # litres

    V2 = V1 / r
    eta_carnot = 1 - T_cold / T_hot
    eta_otto   = 1 - 1 / r ** (gamma - 1)

    if cycle_type == "carnot":
        eta = eta_carnot
        title = "Carnot Cycle"
    else:
        eta = eta_otto
        title = "Otto Cycle"

    # PV points for Otto cycle (1→2 isentropic comp, 2→3 const-V heat add,
    # 3→4 isentropic exp, 4→1 const-V heat rej)
    P2 = P1 * r ** gamma
    T2 = T_cold * r ** (gamma - 1)
    T3 = T_hot
    P3 = P2 * T3 / T2
    P4 = P3 / r ** gamma

    n_pts = 200
    # Isentropic 1→2
    v_12 = np.linspace(V1, V2, n_pts)
    p_12 = P1 * (V1 / v_12) ** gamma

    # Const-V 2→3
    v_23 = np.full(n_pts, V2)
    p_23 = np.linspace(float(P2), float(P3), n_pts)

    # Isentropic 3→4
    v_34 = np.linspace(V2, V1, n_pts)
    p_34 = P3 * (V2 / v_34) ** gamma

    # Const-V 4→1
    v_41 = np.full(n_pts, V1)
    p_41 = np.linspace(float(P4), float(P1), n_pts)

    v_all = np.concatenate([v_12, v_23, v_34, v_41])
    p_all = np.concatenate([p_12, p_23, p_34, p_41])

    numerical = {
        "thermodynamic_cycle": {
            "cycle":               title,
            "compression_ratio":   r,
            "T_hot_K":             T_hot,
            "T_cold_K":            T_cold,
            "P1_kPa":              P1,
            "P2_kPa":              round(float(P2), 1),
            "P3_kPa":              round(float(P3), 1),
            "P4_kPa":              round(float(P4), 1),
            "efficiency_percent":  round(eta * 100, 2),
            "carnot_efficiency_%": round(eta_carnot * 100, 2),
        }
    }

    plots = [{
        "plot_type": "line",
        "title": f"{title} — PV Diagram",
        "x_label": "Volume (L)",
        "y_label": "Pressure (kPa)",
        "x": v_all.tolist(),
        "y": p_all.tolist(),
        "series_name": title,
    }]

    # ── 3D-model: schematic engine cross-section ──────────────────
    visual_data = {
        "model_type": "thermo_engine",
        "title": f"{title} — r={r}, η={round(eta*100,1)}%",
        "width": 720,
        "height": 460,
        "views": ["schematic"],
        "parts": [
            # Cylinder
            {
                "id": "CYL", "type": "cylinder",
                "x": 240, "y": 80, "width": 120, "height": 240,
                "label": "Cylinder",
                "properties": {"V1_L": V1, "V2_L": round(V2, 3), "r": r},
            },
            # Piston
            {
                "id": "PISTON", "type": "piston",
                "x": 245, "y": 240, "width": 110, "height": 30,
                "label": "Piston",
                "properties": {"stroke_L": round(V1 - V2, 3)},
            },
            # Connecting rod
            {
                "id": "ROD", "type": "connecting_rod",
                "x1": 300, "y1": 270, "x2": 300, "y2": 360,
                "label": "Con Rod",
                "properties": {},
            },
            # Crankshaft
            {
                "id": "CRANK", "type": "crankshaft",
                "cx": 300, "cy": 380, "r": 40,
                "label": "Crankshaft",
                "properties": {},
            },
            # State points
            {
                "id": "ST1", "type": "state_point",
                "x": 500, "y": 100, "label": f"1: {P1:.0f} kPa, {T_cold}K",
                "properties": {"P_kPa": P1, "T_K": T_cold, "V_L": V1},
            },
            {
                "id": "ST2", "type": "state_point",
                "x": 500, "y": 160, "label": f"2: {P2:.0f} kPa, {round(float(T2))}K",
                "properties": {"P_kPa": round(float(P2),1), "T_K": round(float(T2)), "V_L": round(V2,3)},
            },
            {
                "id": "ST3", "type": "state_point",
                "x": 500, "y": 220, "label": f"3: {P3:.0f} kPa, {T_hot}K",
                "properties": {"P_kPa": round(float(P3),1), "T_K": T_hot, "V_L": round(V2,3)},
            },
            {
                "id": "ST4", "type": "state_point",
                "x": 500, "y": 280, "label": f"4: {P4:.0f} kPa",
                "properties": {"P_kPa": round(float(P4),1), "V_L": V1},
            },
        ],
        "dimensions": [],
        "annotations": [
            {"x": 500, "y": 360,
             "text": f"η = {round(eta*100,1)}%", "color": "#4ade80"},
            {"x": 500, "y": 390,
             "text": f"Carnot limit = {round(eta_carnot*100,1)}%", "color": "#94a3b8"},
        ],
    }

    observations = [
        f"{title} with compression ratio r = {r}",
        f"Thermal efficiency = {round(eta*100,2)}%  (Carnot limit {round(eta_carnot*100,2)}%)",
        f"State 1: {P1} kPa, {T_cold} K  →  State 2: {round(float(P2),1)} kPa, {round(float(T2))} K",
        f"State 3: {round(float(P3),1)} kPa, {T_hot} K  →  State 4: {round(float(P4),1)} kPa",
        f"PV diagram area represents net work per cycle",
    ]
    return numerical, plots, visual_data, observations


# ─── Main entry ──────────────────────────────────────────────────────────

def run(procedure: dict) -> dict:
    log      = ["[mech_sim] Starting mechanical engineering simulation"]
    params   = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type") or ""
    text     = (procedure.get("hypothesis", "") + " " + exp_type).lower()

    if exp_type in ("", "mechanical", None):
        if any(w in text for w in ["gear", "spur", "mesh", "pinion", "teeth"]):
            exp_type = "gear_train"
        elif any(w in text for w in ["shaft", "torque", "torsion", "twist"]):
            exp_type = "shaft_design"
        elif any(w in text for w in ["thermo", "otto", "carnot", "cycle", "engine", "piston", "heat"]):
            exp_type = "thermo_cycle"
        else:
            exp_type = "gear_train"

    if exp_type in ("gear_train", "gear"):
        numerical, plots, visual_data, observations = _gear_train(params)
        log.append("[mech_sim] Gear train analysis computed")
    elif exp_type in ("shaft_design", "shaft"):
        numerical, plots, visual_data, observations = _shaft_design(params)
        log.append("[mech_sim] Shaft design analysis computed")
    else:
        numerical, plots, visual_data, observations = _thermo_cycle(params)
        log.append("[mech_sim] Thermodynamic cycle computed")

    log.append(f"[mech_sim] Parts: {len(visual_data.get('parts', []))}")

    return {
        "numerical_results":  numerical,
        "plot_data":          plots,
        "visual_data":        visual_data,
        "visualization_type": "3d_model",
        "observations":       observations,
        "confidence_score":   0.91,
        "simulation_log":     log,
    }
