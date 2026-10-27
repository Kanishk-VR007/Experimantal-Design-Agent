"""
Pydantic schemas for Simulation Agent I/O
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ── INPUT (from Experiment Architect / Ollama) ──────────────────
class ExperimentProcedure(BaseModel):
    """
    Schema that the Experiment Architect (Ollama/Lemma-3) must output.
    LangChain will pass this as input to the Simulation Agent.
    """
    domain: str = Field(..., description="e.g. chemistry, biology, physics, electronics, computer_science, general")
    hypothesis: str = Field(..., description="The hypothesis being tested")
    steps: List[str] = Field(..., description="Step-by-step procedure")
    reagents: Optional[List[Dict[str, Any]]] = Field(
        default=[], description="[{name, smiles, concentration_M, volume_mL}]"
    )
    parameters: Dict[str, Any] = Field(
        default={}, description="Temperature, pH, time, voltage, etc."
    )
    expected_metrics: List[str] = Field(
        default=[], description="What measurable outcomes are expected"
    )
    experiment_type: Optional[str] = Field(
        default=None, description="Specific sub-type: pendulum, pcr, titration, arduino_led, model_comparison, etc."
    )


# ── OUTPUT (to Analysis Agent / Layer 4) ────────────────────────

class SeriesData(BaseModel):
    """Additional data series for multi-line plots."""
    y: List[Any]
    name: str
    color: Optional[str] = None

class PlotData(BaseModel):
    """Represents a static 2D simulation plot."""
    plot_type: str          # "line", "bar", "scatter", "heatmap" (2D only)
    title: str
    x_label: str
    y_label: str
    x: List[Any]            # 1D array for x-axis. Supports both numeric and string labels
    y: List[Any]            # 1D array for y-axis.
    series_name: Optional[str] = None
    extra_series: Optional[List[SeriesData]] = None   # Multi-series support

class SimulationOutput(BaseModel):
    """
    Normalized output from Simulation Agent → can feed into Analysis Agent.
    """
    status: str                          # "success" | "fallback" | "failed"
    engine_used: str                     # "chem_sim" | "bio_sim" | "physics_sim" | "electronics_sim" | "cs_sim" | "llm_fallback"
    domain: str
    hypothesis: str
    numerical_results: Dict[str, Any]    # All measurable numeric outputs
    plot_data: List[PlotData]            # Ready-to-render graph data
    observations: List[str]              # Qualitative findings
    confidence_score: float              # 0.0 → 1.0
    simulation_log: List[str]            # Step-by-step trace for audit
    visualization_type: str = "graph"   # "graph" | "circuit" | "architecture"
    visual_data: Optional[Dict[str, Any]] = None  # Circuit/architecture layout for interactive rendering
