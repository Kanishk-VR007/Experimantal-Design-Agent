"""
/improve  Router
================
All iterative-improvement and accuracy-tracking endpoints.

Mount this router in main.py:
    app.include_router(improve.router)
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from core.feedback import (
    record_feedback,
    record_run_accuracy,
    get_memory_avg_score,
    get_all_weights,
)
from core.accuracy_tracker import (
    get_accuracy_report,
    get_accuracy_history,
    get_domain_breakdown,
)
from core.improvement_engine import (
    run_improvement_cycle,
    prune_low_quality_memories,
    recompute_retrieval_weights,
    generate_improvement_plan,
)

router = APIRouter(prefix="/improve", tags=["Iterative Improvement"])


# ── Pydantic request / response models ────────────────────────────────────────

class FeedbackRequest(BaseModel):
    memory_id    : str
    memory_type  : str
    score        : float            # 0.0 (useless) → 1.0 (very helpful)
    feedback_type: str              # recall_relevance | hypothesis_quality | ...
    run_id       : Optional[str] = None
    domain       : Optional[str] = None
    comment      : Optional[str] = None


class RunAccuracyRequest(BaseModel):
    run_id           : str
    domain           : str
    hypothesis_score : float        # 0–1
    procedure_score  : float        # 0–1
    simulation_conf  : float        # 0–1
    analysis_depth   : float        # 0–1
    audit_score      : float        # 0–1
    review_score_10  : float        # 0–10  (L7 overall_score)


# ── Feedback endpoints ─────────────────────────────────────────────────────────

@router.post("/feedback", summary="Record memory feedback score")
async def submit_feedback(req: FeedbackRequest):
    """
    Called by any pipeline agent after using a recalled memory.
    Score 0.0 = useless, 1.0 = extremely helpful.
    Feeds into retrieval weight recomputation.

    **Example** — L2 Architect after using recalled procedure:
    ```json
    {
        "memory_id": "abc123",
        "memory_type": "hypothesis_procedure",
        "score": 0.9,
        "feedback_type": "procedure_match",
        "run_id": "20240101_120000"
    }
    ```
    """
    record_feedback(
        memory_id     = req.memory_id,
        memory_type   = req.memory_type,
        score         = max(0.0, min(1.0, req.score)),
        feedback_type = req.feedback_type,
        run_id        = req.run_id,
        domain        = req.domain,
        comment       = req.comment,
    )
    return {
        "success": True,
        "message": f"Feedback recorded: memory {req.memory_id[:8]}… score={req.score}",
    }


@router.post("/record-run-accuracy", summary="Store per-layer accuracy for a completed run")
async def record_accuracy(req: RunAccuracyRequest):
    """
    Called by L7 Review Agent at the END of every pipeline run.
    Records per-layer scores and computes weighted overall accuracy.

    **Example**:
    ```json
    {
        "run_id": "20240101_120000",
        "domain": "chemistry",
        "hypothesis_score": 0.8,
        "procedure_score": 0.75,
        "simulation_conf": 0.88,
        "analysis_depth": 0.7,
        "audit_score": 0.82,
        "review_score_10": 7.5
    }
    ```
    """
    overall = record_run_accuracy(
        run_id           = req.run_id,
        domain           = req.domain,
        hypothesis_score = req.hypothesis_score,
        procedure_score  = req.procedure_score,
        simulation_conf  = req.simulation_conf,
        analysis_depth   = req.analysis_depth,
        audit_score      = req.audit_score,
        review_score_10  = req.review_score_10,
    )
    return {
        "success"         : True,
        "run_id"          : req.run_id,
        "overall_accuracy": overall,
        "message"         : f"Run accuracy recorded: {overall:.2%}",
    }


# ── Accuracy tracking ─────────────────────────────────────────────────────────

@router.get("/accuracy-report", summary="Full accuracy report with trends")
async def accuracy_report(domain: str = None):
    """
    Per-layer trends, best/worst scores, convergence status,
    and auto-generated recommendations.
    """
    return get_accuracy_report(domain)


@router.get("/accuracy-history", summary="Raw accuracy time-series data")
async def accuracy_history(domain: str = None, last_n: int = 50):
    """Returns time-ordered accuracy records for dashboard charts."""
    history = get_accuracy_history(domain=domain, last_n=last_n)
    return {"domain": domain or "all", "count": len(history), "history": history}


@router.get("/domain-breakdown", summary="Per-domain accuracy statistics")
async def domain_breakdown():
    """Accuracy stats grouped by domain across all runs."""
    return get_domain_breakdown()


@router.get("/feedback-scores", summary="Memory feedback scores + retrieval weights")
async def feedback_scores():
    """Average feedback scores per memory type and current retrieval weights."""
    return {
        "feedback_scores"  : get_memory_avg_score(),
        "retrieval_weights": get_all_weights(),
    }


# ── Improvement actions ───────────────────────────────────────────────────────

@router.post("/run-cycle", summary="Trigger a full improvement cycle")
async def run_cycle_endpoint(
    background_tasks: BackgroundTasks,
    domain    : str  = None,
    prune     : bool = False,
    run_async : bool = True,
):
    """
    Runs the full improvement cycle:
    1. Recomputes retrieval weights from feedback.
    2. Generates a per-layer improvement plan (LLM or rule-based).
    3. Optionally prunes low-quality memories.

    `run_async=True` → returns immediately, runs in background (recommended).
    `run_async=False` → blocks until complete.

    Recommended: call every 10 pipeline runs via a scheduler.
    """
    if run_async:
        background_tasks.add_task(run_improvement_cycle, domain=domain, prune=prune)
        return {
            "status" : "started",
            "message": "Improvement cycle running in background",
            "tip"    : "Poll GET /improve/accuracy-report for updated results",
        }
    result = run_improvement_cycle(domain=domain, prune=prune)
    return result


@router.post("/reweight", summary="Manually recompute retrieval weights from feedback")
async def reweight_retrieval():
    """
    Recomputes per-memory-type retrieval weights from accumulated feedback.
    Called automatically inside `/run-cycle`, but available standalone too.
    """
    updates = recompute_retrieval_weights()
    return {
        "success": True,
        "updates": updates,
        "message": "Retrieval weights updated from feedback scores",
    }


@router.get("/improvement-plan", summary="Generate LLM-based improvement plan")
async def get_improvement_plan(domain: str = None):
    """
    Generates a concrete per-layer improvement plan using Claude (or falls back
    to rule-based if langchain_anthropic is not installed).
    Expensive if using LLM — call after collecting 5+ runs.
    """
    return generate_improvement_plan(domain)


@router.post("/prune-memories", summary="Prune low-quality memory items")
async def prune_memories(threshold: float = 0.25, dry_run: bool = True):
    """
    Removes memory items with consistently low feedback scores.

    `dry_run=True`  (default) → preview what WOULD be pruned.
    `dry_run=False`           → actually delete them.

    **Always preview (`dry_run=True`) before executing a real prune.**
    """
    return prune_low_quality_memories(dry_run=dry_run)
