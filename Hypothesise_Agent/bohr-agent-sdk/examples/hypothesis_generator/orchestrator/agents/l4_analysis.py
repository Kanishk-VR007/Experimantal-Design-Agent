"""
L4 — Analysis Agent
Performs statistical analysis + narrative scientific interpretation
of the simulation results.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import COLLECTIONS
from orchestrator.state import PipelineState
import json
import re
import numpy as np
from scipy import stats as scipy_stats

SYSTEM_L4 = """You are a Scientific Analysis Agent. Given simulation results and expected metrics,
analyze the data statistically and scientifically. Respond ONLY with valid JSON:
{
  "statistical_summary": {
    "mean": 0.0,
    "std_dev": 0.0,
    "p_value": 0.0,
    "confidence_interval_95": [0.0, 0.0],
    "hypothesis_supported": true
  },
  "findings": ["Finding 1...", "Finding 2..."],
  "anomalies": ["Anomaly 1..."],
  "narrative": "Full scientific interpretation paragraph...",
  "recommendation": "Next steps for the research..."
}"""


@tool
def run_statistical_tests(data_json: str) -> str:
    """Runs t-test, normality check, and descriptive stats on numerical data."""
    try:
        data   = json.loads(data_json)
        values = []

        def extract_nums(obj):
            if isinstance(obj, (int, float)):
                values.append(float(obj))
            elif isinstance(obj, list):
                [extract_nums(i) for i in obj]
            elif isinstance(obj, dict):
                [extract_nums(v) for v in obj.values()]

        extract_nums(data)

        if len(values) < 3:
            return json.dumps({"error": "insufficient data for stats"})

        arr          = np.array(values)
        _, pnorm     = scipy_stats.normaltest(arr) if len(arr) > 7 else (0, 1.0)
        mean, std    = float(np.mean(arr)), float(np.std(arr))
        ci           = scipy_stats.t.interval(0.95, len(arr) - 1, loc=mean, scale=scipy_stats.sem(arr))
        _, pval      = scipy_stats.ttest_1samp(arr, popmean=mean)

        return json.dumps({
            "n"                     : len(values),
            "mean"                  : round(mean, 4),
            "std_dev"               : round(std, 4),
            "min"                   : round(float(np.min(arr)), 4),
            "max"                   : round(float(np.max(arr)), 4),
            "p_value_normality"     : round(float(pnorm), 4),
            "confidence_interval_95": [round(ci[0], 4), round(ci[1], 4)],
            "is_normal_distribution": bool(pnorm > 0.05),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def recall_similar_analyses(domain: str) -> str:
    """Recall past analysis results for comparison baselines."""
    results = COLLECTIONS["analyses"].similarity_search(domain, k=2)
    return "\n".join([r.page_content for r in results]) if results else "No prior analyses."


def run_l4(state: PipelineState, llm, callbacks) -> PipelineState:
    """L4 entry point — Analysis Agent."""
    state.pipeline_log.append("[L4] Analysis Agent started")

    agent = initialize_agent(
        tools        = [run_statistical_tests, recall_similar_analyses],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L4},
    )

    prompt = f"""Analyze these simulation results:
Hypothesis         : {state.selected_hypothesis}
Expected metrics   : {state.procedure.get('expected_metrics', [])}
Simulation output  : {json.dumps(state.simulation_result.get('numerical_results', {}))}
Observations       : {state.simulation_result.get('observations', [])}

1. Run statistical tests on the numerical results.
2. Recall any similar past analyses for baseline comparison.
3. Write the full analysis JSON."""

    response = agent.run(prompt)
    clean    = re.sub(r"```json|```", "", response).strip()
    try:
        m        = re.search(r"\{.*\}", clean, re.DOTALL)
        analysis = json.loads(m.group()) if m else {}
    except Exception:
        analysis = {"findings": [], "narrative": response}

    state.analysis_report = analysis

    COLLECTIONS["analyses"].add_texts(
        texts     = [json.dumps(analysis)],
        metadatas = [{"run_id": state.run_id, "domain": state.procedure.get("domain", "?")}],
    )
    state.pipeline_log.append(f"[L4] Analysis complete: {len(analysis.get('findings', []))} findings")
    return state
