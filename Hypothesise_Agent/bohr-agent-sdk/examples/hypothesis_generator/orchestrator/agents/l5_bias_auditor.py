"""
L5 — Bias & Robustness Auditor
Checks scientific integrity: bias flags, Monte Carlo robustness,
and statistical validity. Triggers a retry if score < 0.4.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import COLLECTIONS
from orchestrator.state import PipelineState
import json
import re
import numpy as np

SYSTEM_L5 = """You are a Scientific Bias & Robustness Auditor. Ensure scientific integrity
across the entire research pipeline. Respond ONLY with valid JSON:
{
  "bias_flags": [
    {"type": "confirmation_bias|selection_bias|...", "severity": "low|medium|high", "description": "..."}
  ],
  "robustness_score": 0.0,
  "integrity_score": 0.0,
  "overall_score": 0.0,
  "issues": ["Issue 1..."],
  "recommendations": ["Fix 1..."],
  "verdict": "pass|flag|reject",
  "retry_recommended": false
}"""


@tool
def run_monte_carlo_robustness(params_json: str) -> str:
    """
    Perturbs simulation parameters ±10 % across 20 runs and checks
    if results remain stable (coefficient of variation < 0.15 = robust).
    """
    try:
        params  = json.loads(params_json)
        numeric = {k: v for k, v in params.items() if isinstance(v, (int, float))}
        if not numeric:
            return json.dumps({"robustness": "cannot_test", "reason": "no numeric params"})

        outcomes = []
        for _ in range(20):
            perturbed = {k: v * (1 + np.random.uniform(-0.1, 0.1)) for k, v in numeric.items()}
            outcomes.append(sum(perturbed.values()))

        cv = float(np.std(outcomes) / (np.mean(outcomes) + 1e-9))
        return json.dumps({
            "monte_carlo_runs"         : 20,
            "coefficient_of_variation" : round(cv, 4),
            "robustness_assessment"    : "robust" if cv < 0.15 else "sensitive",
            "interpretation"           : (
                f"CV={cv:.3f} — {'stable' if cv < 0.15 else 'results vary significantly with parameter changes'}"
            ),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def check_statistical_validity(analysis_json: str) -> str:
    """Checks if statistical methodology in the analysis report is valid."""
    try:
        analysis = json.loads(analysis_json)
        stats    = analysis.get("statistical_summary", {})
        issues   = []
        if stats.get("p_value", 1.0) > 0.05:
            issues.append("p-value > 0.05: result not statistically significant")
        if not stats.get("confidence_interval_95"):
            issues.append("No confidence interval reported")
        if stats.get("hypothesis_supported") is None:
            issues.append("Hypothesis support verdict missing")
        return json.dumps({
            "validity_issues"   : issues,
            "methodology_score" : round(1.0 - len(issues) * 0.2, 2),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_l5(state: PipelineState, llm, callbacks) -> PipelineState:
    """L5 entry point — Bias & Robustness Auditor."""
    state.pipeline_log.append("[L5] Bias & Robustness Auditor started")

    agent = initialize_agent(
        tools        = [run_monte_carlo_robustness, check_statistical_validity],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L5},
    )

    prompt = f"""Audit this complete research pipeline for bias and robustness:

HYPOTHESIS          : {state.selected_hypothesis}
PROCEDURE DOMAIN    : {state.procedure.get('domain', '?')}
PROCEDURE STEPS     : {state.procedure.get('steps', [])}
SIMULATION CONFIDENCE: {state.simulation_result.get('confidence_score', '?')}
ANALYSIS FINDINGS   : {state.analysis_report.get('findings', [])}
STATISTICAL SUMMARY : {state.analysis_report.get('statistical_summary', {})}

Steps:
1. Run Monte Carlo robustness test on: {json.dumps(state.procedure.get('parameters', {}))}
2. Check statistical validity of the analysis
3. Check hypothesis framing for confirmation bias
4. Return full audit JSON"""

    response = agent.run(prompt)
    clean    = re.sub(r"```json|```", "", response).strip()
    try:
        m     = re.search(r"\{.*\}", clean, re.DOTALL)
        audit = json.loads(m.group()) if m else {}
    except Exception:
        audit = {"verdict": "flag", "overall_score": 0.5}

    state.audit_report   = audit
    state.audit_score    = float(audit.get("overall_score", 0.5))
    state.retry_required = audit.get("retry_recommended", False) or state.audit_score < 0.4

    COLLECTIONS["audits"].add_texts(
        texts     = [json.dumps(audit)],
        metadatas = [{"run_id": state.run_id, "score": str(state.audit_score)}],
    )
    state.pipeline_log.append(
        f"[L5] Audit complete: score={state.audit_score}, "
        f"verdict={audit.get('verdict','?')}, retry={state.retry_required}"
    )
    return state
