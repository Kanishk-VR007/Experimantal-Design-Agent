"""
Refinement Engine — reads EvalReport → sends targeted fix instructions
to each weak layer → reruns only those layers → re-evaluates.
"""

import json
import re
from langchain_anthropic import ChatAnthropic
from orchestrator.state import PipelineState

MAX_REFINEMENT_CYCLES = 3
REFINEMENT_THRESHOLD  = 0.70


def build_refinement_instructions(eval_report: dict) -> dict:
    """
    Reads eval_report and generates specific, actionable
    instruction patches for each failing layer.
    """
    llm = ChatAnthropic(model="claude-sonnet-4-20250514",
                        temperature=0, max_tokens=2000)

    failing = {
        layer: data
        for layer, data in eval_report["layer_scores"].items()
        if data["score"] < REFINEMENT_THRESHOLD
    }

    if not failing:
        return {"instructions": {}, "message": "All layers passed — no refinement needed"}

    prompt = f"""You are the Refinement Orchestrator for a scientific research pipeline.
The Evaluation Agent scored these layers below threshold (< 0.70):

{json.dumps(failing, indent=2)}

Overall pipeline score: {eval_report['overall_score']}
Weakest layer: {eval_report['weakest_layer']}

For EACH failing layer, generate a precise instruction patch that tells the layer
exactly what to fix in its next run. Be specific and actionable.

Respond ONLY with valid JSON:
{{
  "instructions": {{
    "L1_hypothesis": {{
      "fix_prompt_addition": "Add this instruction to L1's system prompt: ...",
      "parameter_changes": {{}},
      "priority": "high|medium|low",
      "expected_score_gain": 0.0
    }},
    "L2_architect": {{ }},
    ...only include layers that are failing...
  }},
  "rerun_order": ["L1_hypothesis", "L2_architect"],
  "expected_overall_gain": 0.0,
  "refinement_summary": "One paragraph explaining what will be fixed"
}}"""

    resp  = llm.invoke(prompt)
    clean = re.sub(r"```json|```", "", resp.content).strip()
    try:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        return json.loads(m.group()) if m else {"instructions": {}}
    except Exception:
        return {"instructions": {}}


def apply_refinement(state: PipelineState, instructions: dict,
                     llm, callbacks) -> PipelineState:
    """
    Applies refinement instructions to failing layers and reruns them.
    Only reruns the layers that need fixing — not the full pipeline.
    """
    from orchestrator.agents import (l1_hypothesis, l2_architect,
                                     l3_simulation, l4_analysis,
                                     l5_bias_auditor, l6_memory, l7_review)

    rerun_order = instructions.get("rerun_order", [])
    layer_map = {
        "L1_hypothesis": lambda s: l1_hypothesis.run_l1(s, llm, callbacks),
        "L2_architect" : lambda s: l2_architect.run_l2(s, callbacks),
        "L3_simulation": lambda s: l3_simulation.run_l3(s, llm, callbacks),
        "L4_analysis"  : lambda s: l4_analysis.run_l4(s, llm, callbacks),
        "L5_auditor"   : lambda s: l5_bias_auditor.run_l5(s, llm, callbacks),
        "L6_memory"    : lambda s: l6_memory.run_l6(s, llm, callbacks),
        "L7_review"    : lambda s: l7_review.run_l7(s, llm, callbacks),
    }

    instr = instructions.get("instructions", {})
    for layer in rerun_order:
        if layer not in layer_map:
            continue
        patch = instr.get(layer, {})

        # Inject fix hint into log before rerunning
        if patch.get("fix_prompt_addition"):
            state.pipeline_log.append(
                f"[REFINE] {layer}: {patch['fix_prompt_addition'][:80]}"
            )
        if patch.get("parameter_changes"):
            for k, v in patch["parameter_changes"].items():
                state.procedure[k] = v

        print(f"[REFINEMENT ENGINE] Rerunning {layer}...")
        try:
            state = layer_map[layer](state)
            state.pipeline_log.append(f"[REFINE] {layer} rerun complete")
        except Exception as e:
            state.pipeline_log.append(f"[REFINE] {layer} rerun failed: {e}")

    return state


def run_refinement_loop(state: PipelineState, llm, callbacks) -> PipelineState:
    """
    Full refinement loop:
      Evaluate → if failed → build instructions → rerun weak layers
                           → re-evaluate → repeat up to MAX_REFINEMENT_CYCLES
    """
    from orchestrator.agents.l8_evaluator import run_l8

    cycle      = 0
    best_state = state
    best_score = state.eval_overall_score

    print(f"\n[REFINEMENT] Starting refinement loop. "
          f"Initial score: {best_score:.2%}")

    while cycle < MAX_REFINEMENT_CYCLES:
        if state.eval_passed:
            print(f"[REFINEMENT] ✓ Passed at cycle {cycle}. Score: {state.eval_overall_score:.2%}")
            break

        cycle += 1
        print(f"\n[REFINEMENT] Cycle {cycle}/{MAX_REFINEMENT_CYCLES} — "
              f"score={state.eval_overall_score:.2%} < threshold={REFINEMENT_THRESHOLD}")

        # Build refinement instructions from eval report
        instructions = build_refinement_instructions(state.eval_report)
        if not instructions.get("instructions"):
            print("[REFINEMENT] No actionable instructions generated — stopping")
            break

        print(f"[REFINEMENT] Targets: {list(instructions['instructions'].keys())}")

        # Apply fixes + rerun weak layers
        state = apply_refinement(state, instructions, llm, callbacks)

        # Re-evaluate after fixes
        state = run_l8(state, llm, callbacks)
        state.refinement_cycles = cycle

        # Track best
        if state.eval_overall_score > best_score:
            best_score = state.eval_overall_score
            best_state = state
            print(f"[REFINEMENT] ↑ New best: {best_score:.2%}")
        else:
            print(f"[REFINEMENT] ↔ No improvement: {state.eval_overall_score:.2%}")

    state.pipeline_log.append(
        f"[REFINEMENT] Completed {cycle} cycles. Final score: {best_score:.2%}"
    )
    return best_state
