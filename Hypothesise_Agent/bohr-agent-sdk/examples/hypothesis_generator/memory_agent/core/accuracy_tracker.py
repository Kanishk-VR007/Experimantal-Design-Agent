"""
AccuracyTracker
===============
Tracks accuracy metrics across ALL runs over time.
Computes trends (improving / degrading), detects convergence,
and exposes time-series data for dashboard visualisation.

Uses only stdlib — no extra installs required.
"""

import statistics
from typing import List, Dict

# Re-use the DB connection + path from feedback module
from .feedback import _conn  # type: ignore


def get_accuracy_history(domain: str = None, last_n: int = 50) -> List[dict]:
    """
    Returns the last N run_accuracy records, oldest → newest.
    Used to plot improvement curves.
    """
    with _conn() as db:
        if domain:
            rows = db.execute("""
                SELECT * FROM run_accuracy
                WHERE domain = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (domain, last_n)).fetchall()
        else:
            rows = db.execute("""
                SELECT * FROM run_accuracy
                ORDER BY created_at DESC
                LIMIT ?
            """, (last_n,)).fetchall()
        return [dict(r) for r in reversed(rows)]   # oldest first


def compute_trend(values: List[float]) -> dict:
    """
    Given a list of accuracy values over time, compute:
    - direction: 'improving' | 'degrading' | 'stable' | 'converged'
    - slope    : rate of change per run (linear regression)
    - converged: True if last 5 runs vary < 2 %
    """
    if len(values) < 2:
        return {"direction": "insufficient_data", "slope": 0.0, "converged": False, "std_recent": 0.0}

    n      = len(values)
    xs     = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    num    = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den    = sum((x - x_mean) ** 2 for x in xs) or 1e-9
    slope  = num / den

    recent    = values[-5:] if len(values) >= 5 else values
    converged = statistics.stdev(recent) < 0.02 if len(recent) > 1 else False

    if converged:
        direction = "converged"
    elif slope > 0.005:
        direction = "improving"
    elif slope < -0.005:
        direction = "degrading"
    else:
        direction = "stable"

    return {
        "direction" : direction,
        "slope"     : round(slope, 6),
        "converged" : converged,
        "std_recent": round(statistics.stdev(recent), 4) if len(recent) > 1 else 0.0,
    }


def get_accuracy_report(domain: str = None) -> dict:
    """
    Full accuracy report for a domain (or all domains).
    Returns trend, per-layer breakdown, and improvement recommendations.
    """
    history = get_accuracy_history(domain=domain, last_n=100)
    if not history:
        return {"status": "no_data", "message": "No runs recorded yet"}

    metrics = [
        "hypothesis_score", "procedure_score", "simulation_conf",
        "analysis_depth", "audit_score", "review_score", "overall_accuracy",
    ]

    report: dict = {
        "total_runs"     : len(history),
        "domain"         : domain or "all",
        "latest_run"     : history[-1] if history else {},
        "metrics"        : {},
        "overall_trend"  : {},
        "weakest_layer"  : None,
        "strongest_layer": None,
        "recommendations": [],
    }

    avg_scores: dict = {}
    for m in metrics:
        vals = [r[m] for r in history if r.get(m) is not None]
        if not vals:
            continue
        avg = round(sum(vals) / len(vals), 4)
        avg_scores[m] = avg
        report["metrics"][m] = {
            "average"   : avg,
            "latest"    : round(vals[-1], 4),
            "best_ever" : round(max(vals), 4),
            "worst_ever": round(min(vals), 4),
            "trend"     : compute_trend(vals),
            "history"   : [round(v, 4) for v in vals[-20:]],
        }

    # Overall trend
    overall_vals = [r["overall_accuracy"] for r in history if r.get("overall_accuracy") is not None]
    report["overall_trend"] = compute_trend(overall_vals)

    # Weakest / strongest layer (exclude overall_accuracy)
    layer_scores = {k: v for k, v in avg_scores.items() if k != "overall_accuracy"}
    if layer_scores:
        report["weakest_layer"]   = min(layer_scores, key=layer_scores.get)
        report["strongest_layer"] = max(layer_scores, key=layer_scores.get)

    # Auto-recommendations
    recs = []
    for m, data in report["metrics"].items():
        if data["average"] < 0.5:
            layer = m.replace("_score", "").replace("_conf", "").replace("_depth", "")
            recs.append(
                f"⚠ {layer} layer avg={data['average']:.2f} — below threshold, needs improvement"
            )
        if data["trend"]["direction"] == "degrading":
            recs.append(
                f"📉 {m} is degrading (slope={data['trend']['slope']:.4f}) — investigate recent runs"
            )
    if report["overall_trend"].get("converged"):
        recs.append("✓ Model has converged — accuracy is stable")
    elif report["overall_trend"].get("direction") == "improving":
        recs.append("📈 Overall accuracy is improving — pipeline is learning")
    report["recommendations"] = recs

    return report


def get_domain_breakdown() -> dict:
    """Returns accuracy stats grouped by domain."""
    with _conn() as db:
        rows = db.execute("""
            SELECT domain,
                   COUNT(*) AS runs,
                   AVG(overall_accuracy) AS avg_acc,
                   MAX(overall_accuracy) AS best_acc,
                   MIN(overall_accuracy) AS worst_acc
            FROM run_accuracy
            GROUP BY domain
        """).fetchall()
        return {
            r["domain"]: {
                "runs"     : r["runs"],
                "avg_acc"  : round(r["avg_acc"],  4),
                "best_acc" : round(r["best_acc"],  4),
                "worst_acc": round(r["worst_acc"], 4),
            }
            for r in rows
        }
