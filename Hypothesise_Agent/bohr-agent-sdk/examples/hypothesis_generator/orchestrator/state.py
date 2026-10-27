"""
Shared PipelineState — flows through ALL 7 agent layers.
Every agent reads from and writes back into this object.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PipelineState(BaseModel):
    """
    Single state object passed between every agent layer via the orchestrator.
    """
    # ── Meta ─────────────────────────────────────────────────────
    run_id            : str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    research_question : str = ""
    status            : str = "initialized"   # initialized | running | complete | failed

    # ── L1: Hypothesis Agent output ──────────────────────────────
    hypotheses          : List[Dict[str, Any]] = []
    selected_hypothesis : str = ""

    # ── L2: Experiment Architect output ──────────────────────────
    procedure : Dict[str, Any] = {}   # domain, steps, reagents, parameters, expected_metrics

    # ── L3: Simulation Agent output ──────────────────────────────
    simulation_result   : Dict[str, Any] = {}
    html_animation_path : Optional[str] = None

    # ── L4: Analysis Agent output ────────────────────────────────
    analysis_report : Dict[str, Any] = {}

    # ── L5: Bias & Robustness Auditor output ─────────────────────
    audit_report   : Dict[str, Any] = {}
    audit_score    : float = 0.0
    retry_required : bool = False

    # ── L6: Memory Agent output ──────────────────────────────────
    recalled_context : List[str] = []
    memory_written   : bool = False

    # ── L7: Review & Evaluation output ───────────────────────────
    review_verdict : Dict[str, Any] = {}
    pdf_path       : Optional[str] = None
    dashboard_path : Optional[str] = None

    # ── L8: Evaluation Agent output ──────────────────────────────
    eval_report        : Dict[str, Any] = {}
    eval_passed        : bool = False
    eval_overall_score : float = 0.0
    refinement_cycles  : int = 0
    refinement_log     : List[str] = []

    # ── Shared logs ───────────────────────────────────────────────
    pipeline_log : List[str] = []
