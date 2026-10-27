"""
Electronics / Circuit Simulation Engine
========================================
Handles: Arduino circuits, LED circuits, RLC circuits, voltage dividers.

Returns both numerical data + plot data + visual_data (circuit diagram layout)
for interactive SVG rendering in the frontend (like Tinkercad).
"""

import numpy as np
from scipy.integrate import solve_ivp


# ─── Circuit builders ────────────────────────────────────────────────────────

def _arduino_led_circuit(params):
    """Arduino Uno blink circuit: Pin13 → R1 → LED → GND"""
    supply_v    = params.get("supply_voltage_V", 5.0)
    led_vf      = params.get("led_forward_voltage_V", 2.0)
    led_max_mA  = params.get("led_current_mA", 20)
    resistance  = params.get("resistance_ohm", None)
    freq        = params.get("blink_frequency_Hz", 1.0)

    if resistance is None:
        resistance = (supply_v - led_vf) / (led_max_mA / 1000.0)

    actual_i     = (supply_v - led_vf) / resistance
    power_r_mW   = (actual_i ** 2) * resistance * 1000

    # Blink pulse simulation
    t   = np.linspace(0, 10, 1000)
    led = (np.sin(2 * np.pi * freq * t) >= 0).astype(float)

    numerical = {
        "circuit": {
            "supply_voltage_V":     supply_v,
            "resistor_value_ohm":   round(resistance, 1),
            "led_current_mA":       round(actual_i * 1000, 2),
            "led_forward_voltage_V": led_vf,
            "power_resistor_mW":    round(power_r_mW, 2),
            "blink_frequency_Hz":   freq,
        }
    }
    plots = [{
        "plot_type": "line",
        "title": "LED Blink Pattern (Arduino Pin 13)",
        "x_label": "Time (s)",
        "y_label": "LED State  [1=ON, 0=OFF]",
        "x": t.tolist(),
        "y": led.tolist(),
        "series_name": "LED",
    }]

    # ── Circuit layout (700 × 380 canvas) ───────────────────────
    # Arduino rect: x=30,y=70 (w=140,h=210) → right edge x=170
    #   Pin13 at (170,145), GND at (170,263)
    # R1 horizontal centre (335,145): left=(305,145), right=(365,145)
    # LED horizontal centre (510,145): anode=(485,145), cathode=(535,145)
    # GND bus at y=318, x=100..600; Arduino GND drop at x=170; LED GND drop at x=535
    visual_data = {
        "circuit_type": "schematic",
        "title": f"Arduino LED Blink  —  R={round(resistance,0):.0f}Ω  I={round(actual_i*1000,1)}mA",
        "width": 700,
        "height": 380,
        "components": [
            {
                "id": "U1", "type": "arduino_uno",
                "label": "Arduino\nUno",
                "x": 30, "y": 70, "width": 140, "height": 210,
                "orientation": "horizontal",
                "properties": {
                    "pin_13": "Digital Out (5V drive)",
                    "gnd_pin": "Ground",
                    "supply": "5V USB/external",
                    "clock": "16 MHz",
                }
            },
            {
                "id": "R1", "type": "resistor",
                "label": f"R1\n{round(resistance,0):.0f}Ω",
                "x": 335, "y": 145,
                "orientation": "horizontal",
                "properties": {
                    "resistance_ohm": round(resistance, 1),
                    "power_rating": "0.25W",
                    "power_dissipated_mW": round(power_r_mW, 2),
                    "purpose": "Current limiting",
                }
            },
            {
                "id": "D1", "type": "led",
                "label": "LED1\nRed",
                "x": 510, "y": 145,
                "orientation": "horizontal",
                "properties": {
                    "color": "red",
                    "forward_voltage_V": led_vf,
                    "operating_current_mA": round(actual_i * 1000, 2),
                    "max_current_mA": led_max_mA,
                }
            },
        ],
        "wires": [
            # Pin13 → R1.left
            {"id": "w1", "path": [[170, 145], [305, 145]],
             "color": "#f97316", "label": "D13 / 5V"},
            # R1.right → LED anode
            {"id": "w2", "path": [[365, 145], [485, 145]],
             "color": "#f97316", "label": f"{round(actual_i*1000,1)}mA"},
            # LED cathode → down to GND bus
            {"id": "w3", "path": [[535, 145], [535, 318]],
             "color": "#3b82f6", "label": ""},
            # Arduino GND → down to GND bus
            {"id": "w4", "path": [[170, 263], [170, 318]],
             "color": "#3b82f6", "label": ""},
            # GND bus (horizontal)
            {"id": "w5", "path": [[100, 318], [600, 318]],
             "color": "#3b82f6", "label": "GND bus"},
        ],
    }

    observations = [
        f"LED current = {round(actual_i*1000,2)} mA  (safe range: 10–30 mA)",
        f"Current-limiting resistor = {round(resistance,1)} Ω",
        f"Resistor power dissipation = {round(power_r_mW,2)} mW",
        f"Blink rate = {freq} Hz ({round(1/freq,2)} s on/off period)",
    ]
    return numerical, plots, visual_data, observations


def _led_resistor_battery(params):
    """Simple series circuit: Battery → R → LED → GND"""
    supply_v   = params.get("supply_voltage_V", 9.0)
    led_vf     = params.get("led_forward_voltage_V", 2.0)
    resistance = params.get("resistance_ohm", 470)

    current  = (supply_v - led_vf) / resistance
    power_mW = (current ** 2) * resistance * 1000
    v_r      = current * resistance

    numerical = {
        "circuit": {
            "supply_voltage_V":          supply_v,
            "current_mA":                round(current * 1000, 2),
            "voltage_across_resistor_V": round(v_r, 3),
            "voltage_across_led_V":      led_vf,
            "power_resistor_mW":         round(power_mW, 2),
        }
    }
    plots = [{
        "plot_type": "bar",
        "title": "Voltage Distribution Across Components",
        "x_label": "Component",
        "y_label": "Voltage (V)",
        "x": ["Battery", "Resistor Drop", "LED Forward"],
        "y": [supply_v, round(v_r, 3), led_vf],
        "series_name": "Voltage",
    }]

    # Canvas 660 x 360 — U-shaped schematic
    # Battery left (100,180): pos=(100,130), neg=(100,230)
    # R1 horizontal top centre (330,100)
    # LED horizontal right (530,180): anode=(505,180), cath=(555,180)
    # GND rail at y=270
    visual_data = {
        "circuit_type": "schematic",
        "title": f"LED + Resistor Circuit  ({supply_v}V supply)",
        "width": 660,
        "height": 360,
        "components": [
            {
                "id": "BAT1", "type": "battery",
                "label": f"Battery\n{supply_v}V",
                "x": 75, "y": 140,
                "orientation": "horizontal",
                "properties": {"voltage_V": supply_v, "type": "DC"},
            },
            {
                "id": "R1", "type": "resistor",
                "label": f"R1\n{resistance}Ω",
                "x": 330, "y": 100,
                "orientation": "horizontal",
                "properties": {
                    "resistance_ohm": resistance,
                    "power_mW": round(power_mW, 2),
                    "voltage_drop_V": round(v_r, 3),
                },
            },
            {
                "id": "D1", "type": "led",
                "label": "LED\nRed",
                "x": 530, "y": 190,
                "orientation": "horizontal",
                "properties": {
                    "color": "red",
                    "current_mA": round(current * 1000, 2),
                    "forward_voltage_V": led_vf,
                },
            },
        ],
        "wires": [
            # Battery+ → up → R1.left
            {"id": "w1", "path": [[75, 130], [75, 100], [300, 100]],
             "color": "#ef4444", "label": f"+{supply_v}V"},
            # R1.right → LED.anode
            {"id": "w2", "path": [[360, 100], [530, 100], [530, 178]],
             "color": "#f97316", "label": f"{round(current*1000,1)}mA"},
            # LED.cathode → down → GND rail
            {"id": "w3", "path": [[530, 203], [530, 275], [75, 275]],
             "color": "#3b82f6", "label": "GND"},
            # Battery- → GND rail
            {"id": "w4", "path": [[75, 247], [75, 275]],
             "color": "#3b82f6", "label": ""},
        ],
    }

    observations = [
        f"Circuit current = {round(current*1000,2)} mA",
        f"Voltage across LED = {led_vf} V",
        f"Voltage across resistor = {round(v_r,3)} V  (Kirchhoff: {supply_v} - {led_vf} = {round(v_r,3)} V)",
        f"Power in resistor = {round(power_mW,2)} mW",
    ]
    return numerical, plots, visual_data, observations


def _voltage_divider(params):
    """Voltage divider: two resistors in series tapping a fraction of Vin"""
    supply_v = params.get("supply_voltage_V", 5.0)
    r1       = params.get("r1_ohm", 1000)
    r2       = params.get("r2_ohm", 1000)

    v_out   = supply_v * r2 / (r1 + r2)
    current = supply_v / (r1 + r2)

    # Sweep input voltage
    v_in_sweep  = np.linspace(0, 12, 100)
    v_out_sweep = v_in_sweep * r2 / (r1 + r2)

    numerical = {
        "voltage_divider": {
            "supply_V":      supply_v,
            "R1_ohm":        r1,
            "R2_ohm":        r2,
            "Vout_V":        round(v_out, 4),
            "current_mA":    round(current * 1000, 3),
            "division_ratio": round(r2 / (r1 + r2), 4),
        }
    }
    plots = [{
        "plot_type": "line",
        "title": f"Voltage Divider Output  (R1={r1}Ω, R2={r2}Ω)",
        "x_label": "Input Voltage Vin (V)",
        "y_label": "Output Voltage Vout (V)",
        "x": v_in_sweep.tolist(),
        "y": v_out_sweep.tolist(),
        "series_name": "Vout",
    }]

    # Canvas 550 x 430 — vertical resistor stack
    # VCC power symbol at (275, 40)  → connection point (275, 60)
    # R1 vertical centre (275, 150): top=(275,120), bottom=(275,180)
    # Tap junction at (275, 218)
    # R2 vertical centre (275, 265): top=(275,235), bottom=(275,295)
    # GND symbol at (275, 360)        → connection point (275, 350)
    # Vout node at (390, 218)
    visual_data = {
        "circuit_type": "schematic",
        "title": f"Voltage Divider  —  Vout = {round(v_out,2):.2f} V",
        "width": 550,
        "height": 430,
        "components": [
            {
                "id": "VCC", "type": "power",
                "label": f"+{supply_v}V",
                "x": 275, "y": 40,
                "orientation": "horizontal",
                "properties": {"voltage_V": supply_v},
            },
            {
                "id": "R1", "type": "resistor",
                "label": f"R1\n{r1}Ω",
                "x": 275, "y": 150,
                "orientation": "vertical",
                "properties": {
                    "resistance_ohm": r1,
                    "voltage_drop_V": round(supply_v - v_out, 3),
                    "power_mW": round((current**2)*r1*1000, 2),
                },
            },
            {
                "id": "R2", "type": "resistor",
                "label": f"R2\n{r2}Ω",
                "x": 275, "y": 265,
                "orientation": "vertical",
                "properties": {
                    "resistance_ohm": r2,
                    "voltage_drop_V": round(v_out, 3),
                    "power_mW": round((current**2)*r2*1000, 2),
                },
            },
            {
                "id": "GND", "type": "ground",
                "label": "GND",
                "x": 275, "y": 360,
                "orientation": "horizontal",
                "properties": {},
            },
            {
                "id": "VOUT", "type": "output_node",
                "label": f"Vout={round(v_out,2):.2f}V",
                "x": 390, "y": 218,
                "orientation": "horizontal",
                "properties": {
                    "voltage_V": round(v_out, 3),
                    "current_mA": round(current*1000, 3),
                },
            },
        ],
        "wires": [
            # VCC → R1.top
            {"id": "w1", "path": [[275, 60], [275, 120]],
             "color": "#ef4444", "label": ""},
            # R1.bottom → R2.top  (voltage at junction = Vout)
            {"id": "w2", "path": [[275, 180], [275, 235]],
             "color": "#f97316", "label": f"{round(v_out,2):.2f}V"},
            # R2.bottom → GND
            {"id": "w3", "path": [[275, 295], [275, 350]],
             "color": "#3b82f6", "label": ""},
            # Tap → Vout node
            {"id": "w4", "path": [[275, 218], [370, 218]],
             "color": "#10b981", "label": "Vout tap"},
        ],
    }

    observations = [
        f"Output voltage Vout = {round(v_out,4)} V  (ratio = R2/(R1+R2) = {round(r2/(r1+r2),4)})",
        f"Total current through divider = {round(current*1000,3)} mA",
        f"Adjust R1/R2 ratio to scale Vout linearly with Vin",
    ]
    return numerical, plots, visual_data, observations


def _rlc_series(params):
    """Series RLC circuit: step voltage response"""
    R  = params.get("resistance_ohm", 10)
    L  = params.get("inductance_H", 0.1)
    C  = params.get("capacitance_F", 0.001)
    V0 = params.get("voltage_V", 5.0)

    t_end  = 0.5
    t_eval = np.linspace(0, t_end, 600)

    def rlc(t, y):
        q, i = y
        return [i, (V0 - R * i - q / C) / L]

    sol    = solve_ivp(rlc, (0, t_end), [0, 0], t_eval=t_eval)
    omega0 = 1.0 / np.sqrt(L * C)
    zeta   = R / (2.0 * np.sqrt(L / C))

    resp_type = (
        "overdamped"        if zeta > 1  else
        "critically damped" if abs(zeta - 1) < 0.01 else
        "underdamped"
    )

    numerical = {
        "rlc": {
            "resonant_frequency_Hz": round(omega0 / (2 * np.pi), 3),
            "damping_ratio_zeta":    round(zeta, 4),
            "peak_current_A":        round(float(np.max(np.abs(sol.y[1]))), 5),
            "response_type":         resp_type,
        }
    }
    plots = [
        {
            "plot_type": "line",
            "title": "RLC Circuit — Current i(t)",
            "x_label": "Time (s)",
            "y_label": "Current (A)",
            "x": t_eval.tolist(),
            "y": sol.y[1].tolist(),
            "series_name": "i(t)",
        },
        {
            "plot_type": "line",
            "title": "RLC Circuit — Charge q(t)",
            "x_label": "Time (s)",
            "y_label": "Charge (C)",
            "x": t_eval.tolist(),
            "y": sol.y[0].tolist(),
            "series_name": "q(t)",
        },
    ]

    # Canvas 660 × 360 — loop schematic
    # VS  circle at (100, 180): top=(100,150), bot=(100,210)
    # R1  horizontal centre (265, 80)
    # L1  horizontal centre (420, 80)
    # C1  VERTICAL centre (560, 180): top=(560,140), bot=(560,220)
    visual_data = {
        "circuit_type": "schematic",
        "title": f"Series RLC — R={R}Ω  L={L}H  C={C}F  V₀={V0}V  (ζ={round(zeta,3)}, {resp_type})",
        "width": 660,
        "height": 360,
        "components": [
            {
                "id": "VS", "type": "voltage_source",
                "label": f"V₀\n{V0}V",
                "x": 100, "y": 180,
                "orientation": "horizontal",
                "properties": {"voltage_V": V0, "type": "Step / DC"},
            },
            {
                "id": "R1", "type": "resistor",
                "label": f"R\n{R}Ω",
                "x": 265, "y": 80,
                "orientation": "horizontal",
                "properties": {"resistance_ohm": R},
            },
            {
                "id": "L1", "type": "inductor",
                "label": f"L\n{L}H",
                "x": 420, "y": 80,
                "orientation": "horizontal",
                "properties": {
                    "inductance_H": L,
                    "resonant_freq_Hz": round(omega0/(2*np.pi), 3),
                },
            },
            {
                "id": "C1", "type": "capacitor",
                "label": f"C\n{C}F",
                "x": 560, "y": 180,
                "orientation": "vertical",
                "properties": {
                    "capacitance_F": C,
                    "reactance_at_resonance_ohm": round(1/(omega0*C), 3),
                },
            },
        ],
        "wires": [
            # VS.top → top-left corner → R1.left
            {"id": "w1", "path": [[100, 148], [100, 80], [235, 80]],
             "color": "#ef4444", "label": f"+{V0}V"},
            # R1.right → L1.left
            {"id": "w2", "path": [[295, 80], [385, 80]],
             "color": "#f97316", "label": "i(t)"},
            # L1.right → C1.top
            {"id": "w3", "path": [[455, 80], [560, 80], [560, 148]],
             "color": "#a855f7", "label": ""},
            # C1.bottom → bottom-right → bottom-left → VS.bottom
            {"id": "w4", "path": [[560, 212], [560, 280], [100, 280], [100, 212]],
             "color": "#3b82f6", "label": "GND"},
        ],
    }

    observations = [
        f"Resonant frequency f₀ = {round(omega0/(2*np.pi),3)} Hz",
        f"Damping ratio ζ = {round(zeta,4)} → {resp_type} response",
        f"Peak current = {round(float(np.max(np.abs(sol.y[1]))),5)} A",
        "Decrease R or adjust L/C to tune resonant frequency",
    ]
    return numerical, plots, visual_data, observations


# ─── Main entry point ────────────────────────────────────────────────────────

def run(procedure: dict) -> dict:
    log     = ["[electronics_sim] Starting electronics simulation"]
    params  = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type") or ""
    text    = (procedure.get("hypothesis", "") + " " + exp_type).lower()

    # Auto-detect sub-type from text
    if exp_type in ("", "electronics", None):
        if any(w in text for w in ["arduino", "blink", "microcontroller", "atmega"]):
            exp_type = "arduino_led"
        elif any(w in text for w in ["voltage divider", "divider"]):
            exp_type = "voltage_divider"
        elif any(w in text for w in ["rlc", "inductor", "resonan"]):
            exp_type = "rlc_circuit"
        else:
            exp_type = "arduino_led"

    if exp_type in ("arduino_led", "arduino", "arduino_blink", "blink"):
        numerical, plots, visual_data, observations = _arduino_led_circuit(params)
        log.append("[electronics_sim] Arduino LED blink circuit computed")

    elif exp_type == "led_resistor":
        numerical, plots, visual_data, observations = _led_resistor_battery(params)
        log.append("[electronics_sim] LED + resistor + battery circuit computed")

    elif exp_type == "voltage_divider":
        numerical, plots, visual_data, observations = _voltage_divider(params)
        log.append("[electronics_sim] Voltage divider circuit computed")

    elif exp_type in ("rlc_circuit", "rlc"):
        numerical, plots, visual_data, observations = _rlc_series(params)
        log.append("[electronics_sim] Series RLC circuit computed")

    else:
        numerical, plots, visual_data, observations = _arduino_led_circuit(params)
        log.append(f"[electronics_sim] Unknown type '{exp_type}', defaulted to Arduino LED")

    n_comp = len(visual_data.get("components", []))
    n_wire = len(visual_data.get("wires", []))
    log.append(f"[electronics_sim] Circuit: {n_comp} components, {n_wire} wires")

    return {
        "numerical_results":  numerical,
        "plot_data":          plots,
        "visual_data":        visual_data,
        "visualization_type": "circuit",
        "observations":       observations,
        "confidence_score":   0.97,
        "simulation_log":     log,
    }
