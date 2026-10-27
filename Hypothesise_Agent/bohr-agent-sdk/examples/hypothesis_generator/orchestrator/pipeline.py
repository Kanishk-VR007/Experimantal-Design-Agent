"""
Pipeline Orchestrator — wires all 7 agent layers together.
This is the single entry point for end-to-end scientific research automation.
"""

from langchain_anthropic import ChatAnthropic

from orchestrator.state import PipelineState
from orchestrator.callbacks import PipelineCallbackHandler
from orchestrator.agents import (
    l1_hypothesis,
    l2_architect,
    l3_simulation,
    l4_analysis,
    l5_bias_auditor,
    l6_memory,
    l7_review,
)
from orchestrator.agents.l8_evaluator import run_l8, generate_eval_dashboard
from orchestrator.refinement_engine import run_refinement_loop

# ── Shared LLM for Claude-backed agents (L1, L3, L4, L5, L6, L7) ─────────────
# L2 uses Ollama (llama3) internally with a Claude fallback.
SHARED_LLM = ChatAnthropic(
    model       = "claude-sonnet-4-20250514",
    temperature = 0,
    max_tokens  = 4096,
)

MAX_RETRIES = 2   # retry from L2 if audit score < 0.4


def run_pipeline(research_question: str, verbose: bool = True) -> PipelineState:
    """
    Run all 7 layers in sequence.

    Usage:
        from orchestrator.pipeline import run_pipeline
        result = run_pipeline("Does temperature affect enzyme reaction rate?")
        print(result.review_verdict)
        print(result.pdf_path)
    """
    state     = PipelineState(research_question=research_question)
    callbacks = PipelineCallbackHandler(run_id=state.run_id, verbose=verbose)
    cb_list   = [callbacks]

    print(f"\n{'='*60}")
    print(f"  SCIENTIFIC RESEARCH AGENT PIPELINE")
    print(f"  Run ID  : {state.run_id}")
    print(f"  Question: {research_question}")
    print(f"{'='*60}\n")

    retry_count = 0
    while retry_count <= MAX_RETRIES:
        try:
            # ── L1: Hypothesis Generation ───────────────────────
            print("\n[ORCHESTRATOR] → L1: Hypothesis Agent")
            state = l1_hypothesis.run_l1(state, SHARED_LLM, cb_list)

            # ── L2: Experiment Architect ─────────────────────────
            print("\n[ORCHESTRATOR] → L2: Experiment Architect (llama3 / Claude fallback)")
            state = l2_architect.run_l2(state, cb_list)

            # ── L3: Simulation ───────────────────────────────────
            print("\n[ORCHESTRATOR] → L3: Simulation Agent")
            state = l3_simulation.run_l3(state, SHARED_LLM, cb_list)

            # ── L4: Analysis ─────────────────────────────────────
            print("\n[ORCHESTRATOR] → L4: Analysis Agent")
            state = l4_analysis.run_l4(state, SHARED_LLM, cb_list)

            # ── L5: Bias & Robustness Audit ──────────────────────
            print("\n[ORCHESTRATOR] → L5: Bias & Robustness Auditor")
            state = l5_bias_auditor.run_l5(state, SHARED_LLM, cb_list)

            # ── Retry if audit score too low ─────────────────────
            if state.retry_required and retry_count < MAX_RETRIES:
                retry_count += 1
                print(f"\n[ORCHESTRATOR] ⚠ Audit score {state.audit_score:.2f} < 0.4 — Retry {retry_count}/{MAX_RETRIES}")
                print("[ORCHESTRATOR] ↩ Re-running from L2 with audit feedback...")
                state.procedure["audit_feedback"] = state.audit_report.get("recommendations", [])
                state.retry_required = False
                continue

            # ── L6: Memory & Knowledge ───────────────────────────
            print("\n[ORCHESTRATOR] → L6: Memory & Knowledge Agent")
            state = l6_memory.run_l6(state, SHARED_LLM, cb_list)

            # ── L7: Review & Evaluation ──────────────────────────
            print("\n[ORCHESTRATOR] → L7: Review & Evaluation Agent")
            state = l7_review.run_l7(state, SHARED_LLM, cb_list)
            # ── L8: Evaluation Agent ─────────────────────────────────────────────────
            print("\n[ORCHESTRATOR] → L8: Evaluation Agent")
            state = run_l8(state, SHARED_LLM, cb_list)
            print(f"\n[ORCHESTRATOR] Eval score: {state.eval_overall_score:.2%} | "
                  f"Passed: {state.eval_passed}")

            # ── Refinement loop (if eval failed) ─────────────────────────────────────
            if not state.eval_passed:
                print("\n[ORCHESTRATOR] ↩ Eval failed — entering refinement loop")
                state = run_refinement_loop(state, SHARED_LLM, cb_list)

            # ── Save eval dashboard (HTML + JSON) ────────────────────────────────────
            import os, json as _json
            out_dir   = os.path.join(os.path.dirname(__file__), "..", "output")
            os.makedirs(out_dir, exist_ok=True)

            # HTML visual report
            html      = generate_eval_dashboard(state.eval_report, state.pipeline_log)
            eval_path = os.path.join(out_dir, f"eval_{state.run_id}.html")
            with open(eval_path, "w", encoding="utf-8") as f:
                f.write(html)

            # JSON data (consumed by React eval dashboard)
            eval_json_path = os.path.join(out_dir, f"eval_{state.run_id}.json")
            full_report    = dict(state.eval_report)
            full_report["pipeline_log"] = state.pipeline_log
            with open(eval_json_path, "w", encoding="utf-8") as f:
                _json.dump(full_report, f, indent=2, default=str)

            state.dashboard_path = eval_path
            print(f"[ORCHESTRATOR] Eval dashboard saved: {eval_path}")
            print(f"[ORCHESTRATOR] Eval JSON saved:      {eval_json_path}")
            break  # success

        except Exception as e:
            print(f"\n[ORCHESTRATOR] ❌ Pipeline error: {e}")
            state.status = "failed"
            state.pipeline_log.append(f"[ERROR] {str(e)}")
            break

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Status      : {state.status}")
    print(f"  Verdict     : {state.review_verdict.get('verdict', '?')}")
    print(f"  Score       : {state.review_verdict.get('overall_score', '?')}/10")
    print(f"  Eval Score  : {state.eval_overall_score:.2%} ({'PASSED' if state.eval_passed else 'FAILED'})")
    print(f"  Refinements : {state.refinement_cycles} cycle(s)")
    print(f"  PDF         : {state.pdf_path}")
    print(f"  Animation   : {state.html_animation_path}")
    print(f"  Eval Report : {state.dashboard_path}")
    print(f"{'='*60}\n")
    return state
