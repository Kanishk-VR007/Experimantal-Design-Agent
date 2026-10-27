"""
ImprovementEngine
=================
1. Reweights ChromaDB retrieval based on feedback scores
   → good memories are surfaced more, bad ones less.
2. Auto-generates improvement prompts for each weak layer.
3. Prunes low-quality memories below a score threshold.

Depends only on: core.feedback, core.accuracy_tracker, stdlib.
The LLM improvement plan gracefully degrades if anthropic/langchain is absent.
"""

import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from .feedback import (  # type: ignore
    get_memory_avg_score,
    update_retrieval_weight,
    get_all_weights,
    _conn,
)

from .accuracy_tracker import get_accuracy_report  # type: ignore

PRUNE_THRESHOLD    = 0.25   # memories with avg feedback below this are candidates
MIN_FEEDBACK_COUNT = 3      # only consider items with at least this many feedbacks

# ── Retrieval weight recomputation ────────────────────────────────────────────

def recompute_retrieval_weights() -> dict:
    """
    Reads average feedback scores per memory type and recomputes
    retrieval weights using an exponential moving average.

    Formula: new_weight = 0.6 * old_weight + 0.4 * (0.2 + avg_score * 1.8)
    Maps avg_score 0→1 to weight range 0.2→2.0 smoothly.
    """
    avg_scores  = get_memory_avg_score()
    old_weights = get_all_weights()
    new_weights = {}

    memory_types = [
        "chat_history", "experiment_result", "hypothesis_procedure",
        "agent_conversation", "model_learning",
    ]

    for mtype in memory_types:
        old_w = old_weights.get(mtype, 1.0)

        if mtype in avg_scores and avg_scores[mtype]["count"] >= MIN_FEEDBACK_COUNT:
            avg_s    = avg_scores[mtype]["avg_score"]
            target_w = 0.2 + avg_s * 1.8
            new_w    = round(0.6 * old_w + 0.4 * target_w, 4)
        else:
            new_w = old_w   # not enough data — leave unchanged

        update_retrieval_weight(mtype, new_w)
        new_weights[mtype] = {"old": old_w, "new": new_w}

    return new_weights


# ── Memory pruning ─────────────────────────────────────────────────────────────

def prune_low_quality_memories(dry_run: bool = True) -> dict:
    """
    Identifies memory items with consistently low feedback scores.

    dry_run=True  → returns what WOULD be pruned (safe preview).
    dry_run=False → deletes them via chromadb_store if available.
    """
    with _conn() as db:
        rows = db.execute("""
            SELECT memory_id, memory_type, AVG(score) AS avg_score, COUNT(*) AS cnt
            FROM memory_feedback
            GROUP BY memory_id
            HAVING avg_score < ? AND cnt >= ?
        """, (PRUNE_THRESHOLD, MIN_FEEDBACK_COUNT)).fetchall()

    pruned = []
    for row in rows:
        entry = {
            "memory_id"   : row["memory_id"],
            "memory_type" : row["memory_type"],
            "avg_score"   : round(row["avg_score"], 4),
            "feedback_cnt": row["cnt"],
        }

        if not dry_run:
            try:
                from . import chromadb_store as local_db  # type: ignore
                col = local_db._get_collection(
                    local_db.COLLECTIONS.get(row["memory_type"], row["memory_type"])
                )
                col.delete(ids=[row["memory_id"]])
                entry["status"] = "deleted"
            except ImportError:
                entry["status"] = "skipped (chromadb_store not configured)"
            except Exception as e:
                entry["status"] = f"error: {e}"
        else:
            entry["status"] = "would_delete"

        pruned.append(entry)

    return {
        "dry_run"     : dry_run,
        "pruned_count": len(pruned),
        "items"       : pruned,
    }


# ── LLM improvement plan ───────────────────────────────────────────────────────

def generate_improvement_plan(domain: str = None) -> dict:
    """
    Uses the accuracy report + feedback data to generate a concrete
    improvement plan for each weak pipeline layer via Claude.

    Gracefully returns a text plan if langchain_anthropic is not installed.
    """
    report  = get_accuracy_report(domain)
    weights = get_all_weights()
    scores  = get_memory_avg_score()

    if report.get("status") == "no_data":
        return {"plan": [], "summary": "No run data yet — run the pipeline first."}

    context = (
        f"Pipeline accuracy report:\n"
        f"- Total runs: {report['total_runs']}\n"
        f"- Overall trend: {report['overall_trend'].get('direction','?')} "
        f"(slope={report['overall_trend'].get('slope', 0.0)})\n"
        f"- Weakest layer: {report.get('weakest_layer', '?')}\n"
        f"- Per-layer averages: "
        f"{json.dumps({k: v['average'] for k, v in report['metrics'].items()}, indent=2)}\n"
        f"- Memory retrieval weights: {json.dumps(weights, indent=2)}\n"
        f"- Memory feedback scores: "
        f"{json.dumps({k: v['avg_score'] for k, v in scores.items()}, indent=2)}\n"
        f"- Recommendations: {report['recommendations']}\n"
    )

    prompt = (
        context + "\n"
        "Based on this data, generate a concrete improvement plan.\n"
        "For each underperforming layer, specify EXACTLY what to change.\n"
        "Respond ONLY with valid JSON containing exactly these keys:\n"
        '{\n'
        '  "weakest_layer": "layer_name",\n'
        '  "action": "prompt_improvement | retrieval_tuning | data_augmentation",\n'
        '  "recommendations": ["recommendation 1", "recommendation 2"],\n'
        '  "updated_retrieval_weights": {"memory_type": new_weight_float}\n'
        '}'
    )

    # Try LLM — fall back to rule-based if unavailable
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY or GOOGLE_API_KEY in .env file.")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            api_key=api_key
        )
        
        # Enforce strict JSON output mode via binding where supported
        if hasattr(llm, "bind"):
            llm = llm.bind(response_mime_type="application/json")
            
        response = llm.invoke(prompt)
        clean = re.sub(r"```json|```", "", response.content).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(clean)

    except ImportError:
        # LLM not available — return rule-based recommendations
        return _rule_based_plan(report, weights, scores)
    except Exception as e:
        # Maintain existing rule-based fallback mechanism if API call encounters a network error or rate limit
        return _rule_based_plan(report, weights, scores)


def _rule_based_plan(report: dict, weights: dict, scores: dict) -> dict:
    """Fallback improvement plan when LLM is not available."""
    weakest_layer = report.get("weakest_layer", "unknown")
    
    action = "prompt_improvement"
    recommendations = [f"Rule-based fallback: Review and improve {weakest_layer} logic."]
    
    updated_weights = {}
    for mtype, info in scores.items():
        if info["avg_score"] < PRUNE_THRESHOLD:
            # Decrease weight slightly
            old_w = weights.get(mtype, 1.0)
            updated_weights[mtype] = round(old_w * 0.9, 4)
        elif info["avg_score"] > 0.75:
            # Increase weight slightly
            old_w = weights.get(mtype, 1.0)
            updated_weights[mtype] = round(old_w * 1.1, 4)
        else:
            updated_weights[mtype] = weights.get(mtype, 1.0)

    return {
        "weakest_layer": weakest_layer,
        "action": action,
        "recommendations": recommendations,
        "updated_retrieval_weights": updated_weights,
    }


# ── Full improvement cycle ─────────────────────────────────────────────────────

def run_improvement_cycle(domain: str = None, prune: bool = False) -> dict:
    """
    Full improvement cycle — run after every N pipeline runs or on schedule:
      1. Recompute retrieval weights from feedback scores.
      2. Generate an improvement plan (LLM or rule-based).
      3. Optionally prune low-quality memories (dry_run unless prune=True).
    """
    print("[ImprovementEngine] Starting improvement cycle...")

    weight_updates = recompute_retrieval_weights()
    print(f"[ImprovementEngine] Weight updates: {weight_updates}")

    plan = generate_improvement_plan(domain)
    print(f"[ImprovementEngine] Plan: {len(plan.get('plan', []))} layer action(s)")

    prune_result = prune_low_quality_memories(dry_run=not prune)

    return {
        "cycle_time"      : datetime.utcnow().isoformat(),
        "weight_updates"  : weight_updates,
        "improvement_plan": plan,
        "prune_result"    : prune_result,
    }
