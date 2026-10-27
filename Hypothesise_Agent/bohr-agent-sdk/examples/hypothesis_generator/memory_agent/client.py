"""
MemoryClient
============
HTTP client for the Memory Agent service.
Use this from the orchestrator or any pipeline agent to:
  - Submit feedback after using a recalled memory
  - Record run accuracy at the end of every pipeline run
  - Query accuracy reports and trigger improvement cycles

Usage:
    from memory_agent.client import MemoryClient

    memory = MemoryClient("http://localhost:8001")
    memory.submit_feedback("abc123", "hypothesis_procedure", 0.9, "procedure_match", run_id="run_001")
    memory.record_run_accuracy("run_001", "chemistry", 0.8, 0.75, 0.88, 0.7, 0.82, 7.5)
"""

import httpx
from typing import Optional


class MemoryClient:
    """Synchronous HTTP client for the Memory Agent (port 8001 by default)."""

    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 30.0):
        self.base   = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.client.close()

    def close(self):
        self.client.close()

    # ── Health check ────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Returns True if the Memory Agent is reachable."""
        try:
            r = self.client.get(f"{self.base}/")
            return r.status_code == 200
        except Exception:
            return False

    # ── Feedback ────────────────────────────────────────────────────────────────

    def submit_feedback(
        self,
        memory_id    : str,
        memory_type  : str,
        score        : float,
        feedback_type: str,
        run_id       : Optional[str] = None,
        domain       : Optional[str] = None,
        comment      : Optional[str] = None,
    ) -> dict:
        """
        Record a 0–1 quality score for a recalled memory item.

        feedback_type options:
            'recall_relevance' | 'hypothesis_quality' | 'procedure_match'
            'simulation_accuracy' | 'analysis_relevance' | 'audit_helpfulness'
        """
        return self.client.post(f"{self.base}/improve/feedback", json={
            "memory_id"    : memory_id,
            "memory_type"  : memory_type,
            "score"        : score,
            "feedback_type": feedback_type,
            "run_id"       : run_id,
            "domain"       : domain,
            "comment"      : comment,
        }).json()

    # ── Run accuracy ────────────────────────────────────────────────────────────

    def record_run_accuracy(
        self,
        run_id           : str,
        domain           : str,
        hypothesis_score : float,
        procedure_score  : float,
        simulation_conf  : float,
        analysis_depth   : float,
        audit_score      : float,
        review_score_10  : float,
    ) -> dict:
        """
        Call at the end of every pipeline run (after L7 Review Agent).
        review_score_10 is the /10 score from L7 (e.g. 7.5).
        Returns overall_accuracy (0–1 weighted average).
        """
        return self.client.post(f"{self.base}/improve/record-run-accuracy", json={
            "run_id"           : run_id,
            "domain"           : domain,
            "hypothesis_score" : hypothesis_score,
            "procedure_score"  : procedure_score,
            "simulation_conf"  : simulation_conf,
            "analysis_depth"   : analysis_depth,
            "audit_score"      : audit_score,
            "review_score_10"  : review_score_10,
        }).json()

    # ── Accuracy tracking ───────────────────────────────────────────────────────

    def get_accuracy_report(self, domain: Optional[str] = None) -> dict:
        """Full accuracy report: per-layer trends, recommendations, convergence."""
        params = {"domain": domain} if domain else {}
        return self.client.get(f"{self.base}/improve/accuracy-report", params=params).json()

    def get_accuracy_history(self, domain: Optional[str] = None, last_n: int = 50) -> dict:
        """Raw time-series accuracy records for charting."""
        params = {"last_n": last_n}
        if domain:
            params["domain"] = domain
        return self.client.get(f"{self.base}/improve/accuracy-history", params=params).json()

    def get_domain_breakdown(self) -> dict:
        """Accuracy stats grouped by domain."""
        return self.client.get(f"{self.base}/improve/domain-breakdown").json()

    def get_feedback_scores(self) -> dict:
        """Current feedback scores + retrieval weights."""
        return self.client.get(f"{self.base}/improve/feedback-scores").json()

    # ── Improvement actions ─────────────────────────────────────────────────────

    def trigger_improvement_cycle(
        self,
        domain    : Optional[str] = None,
        prune     : bool          = False,
        run_async : bool          = True,
    ) -> dict:
        """
        Trigger a full improvement cycle (background by default).
        Reweights retrieval, generates plan, optionally prunes bad memories.
        """
        params = {"run_async": run_async, "prune": prune}
        if domain:
            params["domain"] = domain
        return self.client.post(f"{self.base}/improve/run-cycle", params=params).json()

    def reweight(self) -> dict:
        """Manually recompute retrieval weights from current feedback scores."""
        return self.client.post(f"{self.base}/improve/reweight").json()

    def get_improvement_plan(self, domain: Optional[str] = None) -> dict:
        """Generate a per-layer improvement plan (LLM or rule-based fallback)."""
        params = {"domain": domain} if domain else {}
        return self.client.get(f"{self.base}/improve/improvement-plan", params=params).json()

    def preview_prune(self) -> dict:
        """Preview which memories would be pruned (dry_run=True, safe to call)."""
        return self.client.post(
            f"{self.base}/improve/prune-memories",
            params={"dry_run": True},
        ).json()

    def execute_prune(self) -> dict:
        """
        Actually delete low-quality memories.
        Call preview_prune() first to review what will be removed.
        """
        return self.client.post(
            f"{self.base}/improve/prune-memories",
            params={"dry_run": False},
        ).json()
