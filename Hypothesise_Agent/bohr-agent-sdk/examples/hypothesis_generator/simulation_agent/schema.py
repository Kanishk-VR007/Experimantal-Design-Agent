"""
Pydantic schemas for Simulation Agent I/O (v2 Scientific Contract)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── INPUT (from Experiment Architect / Prompt Refiner) ──────────────────────
class ExperimentProcedure(BaseModel):
    """
    Normalized procedure input to the Simulation Agent.
    """
    domain: str = Field(
        ...,
        description="Canonical domain: civil_engineering, mechanical_engineering, physics, chemistry, biology, electronics, computer_science, general",
    )
    hypothesis: str = Field(..., description="The hypothesis being tested")
    steps: List[str] = Field(default_factory=list, description="Step-by-step procedure")
    reagents: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="[{name, smiles, concentration_M, volume_mL}]"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Physical or experimental parameters"
    )
    expected_metrics: List[str] = Field(
        default_factory=list, description="What measurable outcomes are expected"
    )
    experiment_type: Optional[str] = Field(
        default=None,
        description="Canonical experiment_id from EXPERIMENT_REGISTRY or 'dynamic_custom'",
    )
    topic: Optional[str] = Field(default=None, description="Original topic string")


# ── OUTPUT (to Analysis Agent / Backend API / Frontend) ─────────────────────

class SeriesData(BaseModel):
    """Additional data series for multi-line plots."""
    y: List[Any]
    name: str
    color: Optional[str] = None


class PlotData(BaseModel):
    """Represents a static 2D simulation plot."""
    plot_type: str          # "line", "bar", "scatter", "heatmap"
    title: str
    x_label: str
    y_label: str
    x: List[Any]
    y: List[Any]
    series_name: Optional[str] = None
    extra_series: Optional[List[SeriesData]] = None


class SimulationOutput(BaseModel):
    """
    Normalized, scientifically validated output from the Simulation Agent.
    Never fabricates arbitrary confidence scores or statistical CIs over deterministic trajectories.
    """
    status: str                                        # "success" | "partial" | "validation_failed" | "unsupported" | "failed" | "illustrative"
    simulation_status: str = "success"                 # Canonical scientific status matching status
    simulation_type: str = "deterministic"             # "deterministic" | "analytical" | "ode" | "algorithmic" | "parametric_illustrative" | "unsupported"
    engine_used: str                                   # "chem_sim" | "bio_sim" | "physics_sim" | "electronics_sim" | "civil_sim" | "mech_sim" | "cs_sim" | "llm_fallback"
    domain: str
    experiment_id: Optional[str] = None                # Canonical registered experiment_id
    hypothesis: str
    solver: Optional[Dict[str, Any]] = None            # {name, version, method, equations, library}
    numerical_results: Dict[str, Any]                  # All measurable numeric outputs
    plot_data: List[PlotData]                          # Ready-to-render 2D graph data
    observations: List[str]                            # Qualitative & quantitative findings
    validation: Optional[Dict[str, Any]] = None        # ScientificValidator summary & checks
    visualization: Optional[Dict[str, Any]] = None     # VisualizationContract (template, is_simulation_backed, scene_valid, issues)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None           # Explicitly None unless objectively derived; NEVER hardcoded
    simulation_log: List[str] = Field(default_factory=list)
    visualization_type: str = "graph"                  # "graph" | "circuit" | "blueprint" | "algorithm" | "3d_model" | "sample_testing"
    visual_data: Optional[Dict[str, Any]] = None
    visualization_spec: Optional[Dict[str, Any]] = None
