"""
Electronics & IoT 3D Scene Templates
====================================
Generates 3D virtual electronics simulation scenes based on Wokwi reverse engineering:
- Microcontroller board (PCB, headers, IC chips)
- Breadboard & component placement
- LED with animated emissive glow pulsing
- Current-limiting resistor & jumper wires
- Voltage and current telemetry overlays
"""

import math
from typing import Dict, Any, List
from ..scene_schema import (
    SceneSpecification, SceneObject, MaterialConfig,
    CameraConfig, LightingConfig, ParameterConfig,
    AnimationConfig, AnimationTrack, MeasurementOverlay,
    VectorOverlay, SceneControlsConfig
)


def build_circuit_scene(procedure: Dict[str, Any], numerical_results: Dict[str, Any], plot_data: List[Dict[str, Any]]) -> SceneSpecification:
    """Builds an interactive 3D virtual circuit simulation scene."""
    params = procedure.get("parameters", {})
    v_sup = float(params.get("supply_voltage_V", 5.0))
    v_led = float(params.get("led_forward_voltage_V", 2.0))
    freq = float(params.get("blink_frequency_Hz", 1.0))
    i_ma = float(params.get("led_current_mA", 20.0))

    # Resistance required R = (V_sup - V_led) / (I / 1000)
    i_amp = max(i_ma / 1000.0, 0.001)
    r_calc = max(0.0, (v_sup - v_led) / i_amp)

    objects = [
        # Lab Workbench Mat
        SceneObject(
            id="workbench_mat",
            name="ESD Work Mat",
            type="box",
            position=[0.0, -0.05, 0.0],
            dimensions={"width": 3.2, "height": 0.05, "depth": 2.0},
            material=MaterialConfig(color="#1e293b", metalness=0.2, roughness=0.8)
        ),
        # Microcontroller PCB (Arduino / ESP32 style)
        SceneObject(
            id="mcu_board",
            name="Microcontroller Development Board",
            type="box",
            position=[-0.7, 0.05, 0.0],
            dimensions={"width": 1.2, "height": 0.08, "depth": 0.8},
            material=MaterialConfig(color="#0284c7", metalness=0.4, roughness=0.4)
        ),
        # MCU Main Microchip IC
        SceneObject(
            id="mcu_chip",
            name="ATmega328P / MCU IC",
            type="box",
            position=[-0.7, 0.11, 0.0],
            dimensions={"width": 0.45, "height": 0.04, "depth": 0.25},
            material=MaterialConfig(color="#0f172a", metalness=0.6, roughness=0.3)
        ),
        # USB Type-B Port
        SceneObject(
            id="usb_port",
            name="USB Connector",
            type="box",
            position=[-1.25, 0.11, -0.15],
            dimensions={"width": 0.2, "height": 0.12, "depth": 0.2},
            material=MaterialConfig(color="#94a3b8", metalness=0.9, roughness=0.2)
        ),
        # Breadboard
        SceneObject(
            id="breadboard",
            name="Solderless Breadboard",
            type="box",
            position=[0.6, 0.05, 0.0],
            dimensions={"width": 1.1, "height": 0.08, "depth": 0.75},
            material=MaterialConfig(color="#f8fafc", metalness=0.1, roughness=0.9)
        ),
        # 5mm Through-hole LED
        SceneObject(
            id="led_component",
            name="5mm Indicator LED",
            type="sphere",
            position=[0.6, 0.22, 0.0],
            dimensions={"radius": 0.1},
            material=MaterialConfig(
                color="#22c55e",
                metalness=0.2,
                roughness=0.1,
                transparent=True,
                opacity=0.9,
                emissive="#4ade80",
                emissive_intensity=0.8
            )
        ),
        # LED Base Rim
        SceneObject(
            id="led_base",
            name="LED Flange Base",
            type="cylinder",
            position=[0.6, 0.13, 0.0],
            dimensions={"radius": 0.09, "height": 0.06},
            material=MaterialConfig(color="#16a34a", metalness=0.3, roughness=0.4)
        ),
        # Current-limiting Resistor (Beige Body)
        SceneObject(
            id="resistor_body",
            name=f"Current Limiting Resistor ({int(r_calc)} Ω)",
            type="cylinder",
            position=[0.35, 0.12, 0.15],
            rotation=[0.0, 0.0, math.pi / 2],
            dimensions={"radius": 0.035, "height": 0.25},
            material=MaterialConfig(color="#e2e8f0", metalness=0.1, roughness=0.6)
        ),
        # Jumper Wire (VCC Signal: Digital Pin to Resistor)
        SceneObject(
            id="wire_signal",
            name="VCC Digital Jumper Wire",
            type="cylinder",
            position=[-0.15, 0.14, 0.08],
            rotation=[0.0, -0.4, math.pi / 2],
            dimensions={"radius": 0.012, "height": 0.8},
            material=MaterialConfig(color="#ef4444", metalness=0.3, roughness=0.5)
        ),
        # Jumper Wire (GND Return: LED Cathode to MCU GND)
        SceneObject(
            id="wire_gnd",
            name="GND Return Jumper Wire",
            type="cylinder",
            position=[-0.05, 0.14, -0.1],
            rotation=[0.0, 0.35, math.pi / 2],
            dimensions={"radius": 0.012, "height": 1.0},
            material=MaterialConfig(color="#020617", metalness=0.3, roughness=0.5)
        )
    ]

    # Animation: LED blinking with square / sinusoidal pulse
    frames = 100
    time_array = [round(t * 0.05, 3) for t in range(frames)]
    emissive_track = []
    for t in time_array:
        # Square wave blink based on frequency
        phase = (t * freq) % 1.0
        intensity = 1.0 if phase < 0.5 else 0.05
        emissive_track.append(intensity)

    tracks = {
        "led_component": AnimationTrack(emissive_intensity=emissive_track)
    }

    parameters = [
        ParameterConfig(
            name="supply_voltage_V",
            label="Supply Voltage Vcc",
            type="float",
            value=v_sup,
            min_val=1.8,
            max_val=12.0,
            step=0.1,
            unit="V",
            description="Operating digital rail voltage"
        ),
        ParameterConfig(
            name="blink_frequency_Hz",
            label="Blink Frequency f",
            type="float",
            value=freq,
            min_val=0.2,
            max_val=10.0,
            step=0.2,
            unit="Hz",
            description="Toggle frequency for PWM / digital strobe"
        ),
        ParameterConfig(
            name="led_current_mA",
            label="Forward Current I",
            type="float",
            value=i_ma,
            min_val=5.0,
            max_val=35.0,
            step=1.0,
            unit="mA",
            description="Target forward current through indicator LED"
        )
    ]

    overlays = [
        MeasurementOverlay(
            id="res_meas",
            label="Required Resistor R",
            value=round(r_calc, 1),
            unit="Ω",
            position_3d=[0.35, 0.35, 0.15]
        ),
        MeasurementOverlay(
            id="v_led_meas",
            label="LED Forward Voltage",
            value=v_led,
            unit="V",
            position_3d=[0.6, 0.45, 0.0]
        ),
        MeasurementOverlay(
            id="curr_meas",
            label="Branch Current",
            value=i_ma,
            unit="mA",
            position_3d=[-0.15, 0.35, 0.0]
        )
    ]

    return SceneSpecification(
        domain="electronics",
        experiment_id="arduino_circuit",
        scene_template="arduino_circuit",
        title="Microcontroller Virtual Circuit & LED Blink Simulation",
        description=f"Interactive 3D electronics simulation showing circuit components, Ohm's law calculation R = ({v_sup}V - {v_led}V)/{i_ma}mA = {round(r_calc, 1)}Ω, and real-time LED blinking.",
        is_simulation_backed=True,
        confidence_score=0.96,
        camera=CameraConfig(position=[0.0, 1.8, 2.5], target=[0.0, 0.1, 0.0], fov=45),
        lighting=LightingConfig(ambient_intensity=0.8, directional_position=[3.0, 6.0, 4.0]),
        objects=objects,
        parameters=parameters,
        animation=AnimationConfig(
            has_animation=True,
            duration_s=5.0,
            time_step_s=0.05,
            time_array=time_array,
            tracks=tracks
        ),
        measurement_overlays=overlays,
        controls=SceneControlsConfig(allow_orbit=True, allow_pan=True, allow_zoom=True, show_grid=True)
    )

