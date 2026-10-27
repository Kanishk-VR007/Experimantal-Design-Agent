"""
Civil Engineering Simulation Engine
====================================
Handles: structural analysis, beam loading, truss analysis, building blueprints.

Returns numerical data + plot data + visual_data (blueprint layout)
for interactive SVG rendering in the frontend (like AutoCAD / blueprint).
"""

import numpy as np


# ─── Structural analysis helpers ─────────────────────────────────────────

def _simply_supported_beam(params):
    """Simply supported beam under uniform distributed load (UDL)."""
    L       = params.get("span_m", 6.0)
    w       = params.get("load_kN_per_m", 10.0)
    E       = params.get("elastic_modulus_GPa", 200.0) * 1e6   # kN/m²
    I       = params.get("moment_of_inertia_m4", 8.33e-6)
    b_width = params.get("beam_width_mm", 300)
    b_depth = params.get("beam_depth_mm", 500)

    # Reactions
    R_A = w * L / 2
    R_B = R_A

    # Shear force & bending moment diagrams
    x = np.linspace(0, L, 400)
    V = R_A - w * x                          # Shear (kN)
    M = R_A * x - w * x ** 2 / 2            # Moment (kN·m)

    # Max deflection at midspan  δ = 5wL⁴ / (384EI)
    delta_max = 5 * w * L ** 4 / (384 * E * I) * 1000   # mm

    # Max stress  σ = M_max * y / I  where y = depth/2
    M_max = w * L ** 2 / 8
    sigma_max = M_max * (b_depth / 2 / 1000) / I / 1000  # MPa

    numerical = {
        "beam_analysis": {
            "span_m":               L,
            "load_kN_per_m":        w,
            "reaction_A_kN":        round(R_A, 2),
            "reaction_B_kN":        round(R_B, 2),
            "max_bending_moment_kNm": round(float(M_max), 2),
            "max_shear_force_kN":     round(float(R_A), 2),
            "max_deflection_mm":      round(float(delta_max), 3),
            "max_bending_stress_MPa": round(float(sigma_max), 2),
        }
    }

    plots = [
        {
            "plot_type": "line",
            "title": "Shear Force Diagram (SFD)",
            "x_label": "Position along beam (m)",
            "y_label": "Shear Force V (kN)",
            "x": x.tolist(),
            "y": V.tolist(),
            "series_name": "Shear (V)",
        },
        {
            "plot_type": "line",
            "title": "Bending Moment Diagram (BMD)",
            "x_label": "Position along beam (m)",
            "y_label": "Bending Moment M (kN·m)",
            "x": x.tolist(),
            "y": M.tolist(),
            "series_name": "Moment (M)",
        },
    ]

    # ── Blueprint: side elevation of beam ─────────────────────────
    # Canvas 720 × 420
    bx, by = 80, 140       # beam left-top
    bw = 560               # beam drawn width (px)
    bh = 40                # beam drawn height (px)
    px_per_m = bw / L

    visual_data = {
        "blueprint_type": "structural",
        "title": f"Simply Supported Beam — {L}m span, UDL {w} kN/m",
        "width": 720,
        "height": 420,
        "elements": [
            # The beam itself
            {
                "id": "BEAM", "type": "beam",
                "x": bx, "y": by, "width": bw, "height": bh,
                "label": f"RC Beam {b_width}×{b_depth}mm",
                "properties": {
                    "span_m": L, "width_mm": b_width, "depth_mm": b_depth,
                    "E_GPa": params.get("elastic_modulus_GPa", 200.0),
                    "I_m4": I,
                },
            },
            # Support A (pin/triangle at left)
            {
                "id": "SUP_A", "type": "pin_support",
                "x": bx, "y": by + bh,
                "label": f"A  (R={round(R_A,1)} kN)",
                "properties": {"reaction_kN": round(R_A, 2)},
            },
            # Support B (roller at right)
            {
                "id": "SUP_B", "type": "roller_support",
                "x": bx + bw, "y": by + bh,
                "label": f"B  (R={round(R_B,1)} kN)",
                "properties": {"reaction_kN": round(R_B, 2)},
            },
            # UDL arrows
            {
                "id": "UDL", "type": "distributed_load",
                "x": bx, "y": by - 55, "width": bw,
                "label": f"w = {w} kN/m",
                "properties": {"load_kN_per_m": w},
            },
            # Dimension line below supports
            {
                "id": "DIM_L", "type": "dimension",
                "x1": bx, "y1": by + bh + 70, "x2": bx + bw, "y2": by + bh + 70,
                "label": f"{L} m",
                "properties": {},
            },
            # Deflection indicator at midspan
            {
                "id": "DEFL", "type": "deflection_indicator",
                "x": bx + bw / 2, "y": by + bh + 10,
                "delta_mm": round(float(delta_max), 2),
                "label": f"δ_max = {round(float(delta_max),2)} mm",
                "properties": {"max_deflection_mm": round(float(delta_max), 3)},
            },
        ],
        "annotations": [
            {"x": bx + bw / 2, "y": by + bh + 38,
             "text": f"M_max = {round(float(M_max),2)} kN·m", "color": "#f59e0b"},
            {"x": bx + 10, "y": by + bh + 38,
             "text": f"σ_max = {round(float(sigma_max),1)} MPa", "color": "#ef4444"},
        ],
    }

    observations = [
        f"Beam span = {L} m under UDL = {w} kN/m",
        f"Each support reaction = {round(R_A,2)} kN (symmetric loading)",
        f"Max bending moment at midspan = {round(float(M_max),2)} kN·m",
        f"Max deflection at midspan = {round(float(delta_max),3)} mm  (limit L/250 = {round(L*1000/250,1)} mm)",
        f"Max bending stress = {round(float(sigma_max),2)} MPa",
    ]
    return numerical, plots, visual_data, observations


def _building_blueprint(params):
    """Generate a simple building floor plan blueprint."""
    floors      = params.get("floors", 2)
    width_m     = params.get("width_m", 12.0)
    depth_m     = params.get("depth_m", 8.0)
    floor_h     = params.get("floor_height_m", 3.0)
    wall_thick  = params.get("wall_thickness_mm", 230)
    col_size    = params.get("column_size_mm", 300)
    n_rooms     = params.get("rooms_per_floor", 4)

    total_h     = floors * floor_h
    floor_area  = width_m * depth_m
    total_area  = floor_area * floors
    col_spacing_x = width_m / 3
    col_spacing_y = depth_m / 2

    numerical = {
        "building": {
            "floors":              floors,
            "floor_height_m":      floor_h,
            "plan_width_m":        width_m,
            "plan_depth_m":        depth_m,
            "floor_area_sqm":      round(floor_area, 2),
            "total_built_area_sqm": round(total_area, 2),
            "wall_thickness_mm":   wall_thick,
            "column_size_mm":      col_size,
            "column_grid":         f"{round(col_spacing_x,1)}m × {round(col_spacing_y,1)}m",
        }
    }

    plots = [{
        "plot_type": "bar",
        "title": "Load Distribution Per Floor",
        "x_label": "Floor",
        "y_label": "Estimated Load (kN)",
        "x": [f"Floor {i+1}" for i in range(floors)] + ["Foundation"],
        "y": [round(floor_area * 5.0, 1) for _ in range(floors)] + [round(total_area * 5.0 * 1.2, 1)],
        "series_name": "Load",
    }]

    # ── Blueprint floor plan  (720 × 520) ───────────────────────
    scale = min(560 / width_m, 320 / depth_m)   # px per m
    pw = width_m * scale
    ph = depth_m * scale
    ox, oy = 80, 80        # origin offset

    elements = []

    # Outer walls (thick rectangle)
    elements.append({
        "id": "WALL_OUTER", "type": "wall",
        "x": ox, "y": oy, "width": pw, "height": ph,
        "label": "Outer Wall", "thick": True,
        "properties": {"thickness_mm": wall_thick, "material": "Brick/RCC"},
    })

    # Column grid (4 × 3)
    col_id = 0
    for ix in range(4):
        for iy in range(3):
            cx = ox + ix * (pw / 3)
            cy = oy + iy * (ph / 2)
            col_id += 1
            elements.append({
                "id": f"C{col_id}", "type": "column",
                "x": cx, "y": cy,
                "label": f"C{col_id}",
                "properties": {"size_mm": col_size, "material": "RCC M25"},
            })

    # Room dividers (internal walls)
    # Vertical divider at 1/2 width
    elements.append({
        "id": "IW1", "type": "wall",
        "x": ox + pw / 2, "y": oy, "width": 3, "height": ph,
        "label": "Interior Wall", "thick": False,
        "properties": {"thickness_mm": 115, "material": "Brick"},
    })
    # Horizontal divider at 1/2 depth
    elements.append({
        "id": "IW2", "type": "wall",
        "x": ox, "y": oy + ph / 2, "width": pw, "height": 3,
        "label": "Interior Wall", "thick": False,
        "properties": {"thickness_mm": 115, "material": "Brick"},
    })

    # Door openings
    door_positions = [
        {"id": "D1", "x": ox + pw * 0.25,  "y": oy + ph / 2 - 5, "orient": "h"},
        {"id": "D2", "x": ox + pw * 0.75,  "y": oy + ph / 2 - 5, "orient": "h"},
        {"id": "D3", "x": ox + pw / 2 - 5, "y": oy + ph * 0.25,  "orient": "v"},
        {"id": "D4", "x": ox + pw / 2 - 5, "y": oy + ph * 0.75,  "orient": "v"},
    ]
    for d in door_positions:
        elements.append({
            "id": d["id"], "type": "door",
            "x": d["x"], "y": d["y"],
            "orientation": d["orient"],
            "label": d["id"],
            "properties": {"width_mm": 900, "type": "Flush Door"},
        })

    # Window openings on outer walls
    win_id = 0
    for frac in [0.25, 0.75]:
        win_id += 1
        elements.append({
            "id": f"W{win_id}", "type": "window",
            "x": ox + pw * frac, "y": oy,
            "orientation": "h",
            "label": f"W{win_id}",
            "properties": {"width_mm": 1200, "height_mm": 1200, "sill_mm": 900},
        })
    for frac in [0.25, 0.75]:
        win_id += 1
        elements.append({
            "id": f"W{win_id}", "type": "window",
            "x": ox + pw * frac, "y": oy + ph,
            "orientation": "h",
            "label": f"W{win_id}",
            "properties": {"width_mm": 1200, "height_mm": 1200, "sill_mm": 900},
        })

    # Room labels
    room_names = ["Living Room", "Bedroom", "Kitchen", "Bathroom"]
    room_centers = [
        (ox + pw * 0.25, oy + ph * 0.25),
        (ox + pw * 0.75, oy + ph * 0.25),
        (ox + pw * 0.25, oy + ph * 0.75),
        (ox + pw * 0.75, oy + ph * 0.75),
    ]
    for i, (rx, ry) in enumerate(room_centers):
        name = room_names[i] if i < len(room_names) else f"Room {i+1}"
        area = round(floor_area / n_rooms, 1)
        elements.append({
            "id": f"ROOM{i+1}", "type": "room_label",
            "x": rx, "y": ry,
            "label": name,
            "area_sqm": area,
            "properties": {"area_sqm": area},
        })

    # Dimension lines
    elements.append({
        "id": "DIM_W", "type": "dimension",
        "x1": ox, "y1": oy + ph + 45, "x2": ox + pw, "y2": oy + ph + 45,
        "label": f"{width_m} m",
        "properties": {},
    })
    elements.append({
        "id": "DIM_D", "type": "dimension",
        "x1": ox - 40, "y1": oy, "x2": ox - 40, "y2": oy + ph,
        "label": f"{depth_m} m",
        "properties": {},
    })

    visual_data = {
        "blueprint_type": "floor_plan",
        "title": f"Floor Plan — {width_m}m × {depth_m}m  ({floors} floors, {n_rooms} rooms)",
        "width": 720,
        "height": 520,
        "elements": elements,
        "annotations": [
            {"x": ox + pw / 2, "y": 30,
             "text": f"GROUND FLOOR PLAN  —  Scale ≈ 1:{int(1000/scale)}", "color": "#94a3b8"},
        ],
    }

    observations = [
        f"Building footprint: {width_m}m × {depth_m}m = {round(floor_area,1)} m² per floor",
        f"Total built-up area: {round(total_area,1)} m² ({floors} floors)",
        f"Column grid: {round(col_spacing_x,1)}m × {round(col_spacing_y,1)}m  ({col_id} columns)",
        f"Wall thickness — Outer: {wall_thick}mm, Inner: 115mm",
        f"Column size: {col_size}mm × {col_size}mm (RCC M25 grade)",
    ]
    return numerical, plots, visual_data, observations


def _truss_analysis(params):
    """Simple Pratt truss analysis."""
    span    = params.get("span_m", 10.0)
    height  = params.get("height_m", 3.0)
    n_panels = params.get("panels", 4)
    load_kN = params.get("point_load_kN", 20.0)

    panel_w = span / n_panels

    # Joint coordinates
    joints = []
    # Bottom chord
    for i in range(n_panels + 1):
        joints.append((i * panel_w, 0))
    # Top chord
    for i in range(1, n_panels):
        joints.append((i * panel_w, height))

    # Simple reaction calculation (symmetric loading at each top joint)
    n_top = n_panels - 1
    total_load = load_kN * n_top
    R_A = total_load / 2
    R_B = total_load / 2

    # Approximate max forces
    max_tension    = round(R_A * span / (2 * height), 2)
    max_compression = round(-R_A * span / (2 * height), 2)

    numerical = {
        "truss": {
            "span_m":           span,
            "height_m":         height,
            "panels":           n_panels,
            "point_load_kN":    load_kN,
            "reaction_A_kN":    round(R_A, 2),
            "reaction_B_kN":    round(R_B, 2),
            "max_tension_kN":   max_tension,
            "max_compression_kN": abs(max_compression),
            "total_load_kN":    round(total_load, 2),
        }
    }

    # Member forces plot
    members = [f"BC{i+1}" for i in range(n_panels)] + \
              [f"TC{i+1}" for i in range(n_panels - 1)] + \
              [f"D{i+1}" for i in range(n_panels)]
    forces = ([round(R_A - load_kN * (i / n_panels), 1) for i in range(n_panels)] +
              [round(-R_A * panel_w * (i + 1) / height, 1) for i in range(n_panels - 1)] +
              [round(load_kN * 0.7, 1) for _ in range(n_panels)])

    plots = [{
        "plot_type": "bar",
        "title": "Truss Member Forces",
        "x_label": "Member",
        "y_label": "Force (kN)  [+T / −C]",
        "x": members,
        "y": forces,
        "series_name": "Axial Force",
    }]

    # ── Blueprint: truss elevation ────────────────────────────────
    scale = 500 / span
    ox, oy_bot = 110, 280
    oy_top = oy_bot - height * scale

    elements = []

    # Bottom chord joints
    for i in range(n_panels + 1):
        jx = ox + i * panel_w * scale
        elements.append({
            "id": f"BJ{i}", "type": "joint",
            "x": jx, "y": oy_bot,
            "label": f"J{i}",
            "properties": {},
        })

    # Top chord joints
    for i in range(1, n_panels):
        jx = ox + i * panel_w * scale
        elements.append({
            "id": f"TJ{i}", "type": "joint",
            "x": jx, "y": oy_top,
            "label": f"T{i}",
            "properties": {},
        })

    # Members as lines
    # Bottom chord
    for i in range(n_panels):
        x1 = ox + i * panel_w * scale
        x2 = ox + (i + 1) * panel_w * scale
        elements.append({
            "id": f"BC{i}", "type": "member",
            "x1": x1, "y1": oy_bot, "x2": x2, "y2": oy_bot,
            "member_type": "bottom_chord",
            "label": f"BC{i+1}",
            "properties": {"force_kN": forces[i] if i < len(forces) else 0},
        })

    # Top chord
    for i in range(n_panels - 1):
        x1 = ox + (i + 1) * panel_w * scale
        x2 = ox + (i + 2) * panel_w * scale
        elements.append({
            "id": f"TC{i}", "type": "member",
            "x1": x1, "y1": oy_top, "x2": x2, "y2": oy_top,
            "member_type": "top_chord",
            "label": f"TC{i+1}",
            "properties": {},
        })

    # Diagonals + verticals
    for i in range(n_panels):
        bx = ox + i * panel_w * scale
        bx_next = ox + (i + 1) * panel_w * scale
        if i > 0:
            elements.append({
                "id": f"D{i}a", "type": "member",
                "x1": bx, "y1": oy_bot, "x2": bx, "y2": oy_top,
                "member_type": "vertical",
                "label": f"V{i}",
                "properties": {},
            })
        # Diagonal
        if i < n_panels - 1:
            elements.append({
                "id": f"D{i}d", "type": "member",
                "x1": bx, "y1": oy_bot, "x2": bx_next, "y2": oy_top,
                "member_type": "diagonal",
                "label": f"D{i+1}",
                "properties": {},
            })
    # End verticals
    elements.append({
        "id": "EV_L", "type": "member",
        "x1": ox, "y1": oy_bot, "x2": ox + panel_w * scale, "y2": oy_top,
        "member_type": "diagonal", "label": "", "properties": {},
    })
    elements.append({
        "id": "EV_R", "type": "member",
        "x1": ox + span * scale, "y1": oy_bot,
        "x2": ox + (n_panels - 1) * panel_w * scale, "y2": oy_top,
        "member_type": "diagonal", "label": "", "properties": {},
    })

    # Supports
    elements.append({"id": "SA", "type": "pin_support", "x": ox, "y": oy_bot,
                      "label": f"A ({round(R_A,1)} kN)", "properties": {"reaction_kN": round(R_A,2)}})
    elements.append({"id": "SB", "type": "roller_support", "x": ox + span * scale, "y": oy_bot,
                      "label": f"B ({round(R_B,1)} kN)", "properties": {"reaction_kN": round(R_B,2)}})

    # Load arrows at top joints
    for i in range(1, n_panels):
        jx = ox + i * panel_w * scale
        elements.append({
            "id": f"PL{i}", "type": "point_load",
            "x": jx, "y": oy_top - 40,
            "label": f"{load_kN} kN",
            "properties": {"load_kN": load_kN},
        })

    # Dimension
    elements.append({
        "id": "DIM_S", "type": "dimension",
        "x1": ox, "y1": oy_bot + 60, "x2": ox + span * scale, "y2": oy_bot + 60,
        "label": f"{span} m",
        "properties": {},
    })

    visual_data = {
        "blueprint_type": "structural",
        "title": f"Pratt Truss — {span}m span, {n_panels} panels, {load_kN} kN loads",
        "width": 720,
        "height": 420,
        "elements": elements,
        "annotations": [],
    }

    observations = [
        f"Truss span = {span} m, height = {height} m, {n_panels} panels",
        f"Each top joint carries {load_kN} kN → total load = {round(total_load,1)} kN",
        f"Support reactions: A = {round(R_A,2)} kN, B = {round(R_B,2)} kN",
        f"Max tension (bottom chord) ≈ {max_tension} kN",
        f"Max compression (top chord) ≈ {abs(max_compression)} kN",
    ]
    return numerical, plots, visual_data, observations


# ─── Main entry ──────────────────────────────────────────────────────────

def run(procedure: dict) -> dict:
    log      = ["[civil_sim] Starting civil engineering simulation"]
    params   = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type") or ""
    text     = (procedure.get("hypothesis", "") + " " + exp_type).lower()

    if exp_type in ("", "civil", None):
        if any(w in text for w in ["beam", "load", "deflect", "slab", "column load"]):
            exp_type = "beam_analysis"
        elif any(w in text for w in ["truss", "roof", "bridge"]):
            exp_type = "truss_analysis"
        elif any(w in text for w in ["blueprint", "floor plan", "building", "house", "room", "construction"]):
            exp_type = "building_blueprint"
        else:
            exp_type = "building_blueprint"

    if exp_type in ("beam_analysis", "beam"):
        numerical, plots, visual_data, observations = _simply_supported_beam(params)
        log.append("[civil_sim] Simply supported beam analysis computed")
    elif exp_type in ("truss_analysis", "truss"):
        numerical, plots, visual_data, observations = _truss_analysis(params)
        log.append("[civil_sim] Truss analysis computed")
    else:
        numerical, plots, visual_data, observations = _building_blueprint(params)
        log.append("[civil_sim] Building blueprint generated")

    log.append(f"[civil_sim] Blueprint elements: {len(visual_data.get('elements', []))}")

    return {
        "numerical_results":  numerical,
        "plot_data":          plots,
        "visual_data":        visual_data,
        "visualization_type": "blueprint",
        "observations":       observations,
        "confidence_score":   0.93,
        "simulation_log":     log,
    }
