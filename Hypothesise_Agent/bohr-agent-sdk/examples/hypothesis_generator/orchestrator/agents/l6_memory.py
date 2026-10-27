"""
L6 — Memory & Knowledge Agent
Stores the complete pipeline run to ChromaDB global knowledge base
and retrieves relevant context from past runs for comparison.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import COLLECTIONS
from orchestrator.state import PipelineState
import json
import re

SYSTEM_L6 = """You are the Memory & Knowledge Agent. Your job is to:
1. Store the complete run results to ChromaDB
2. Retrieve relevant context from past runs
3. Identify patterns across experiments
Respond with JSON: {"stored": true, "recalled_insights": ["..."], "patterns_identified": ["..."]}"""


@tool
def store_full_run(run_json: str) -> str:
    """Stores the complete pipeline run to the global knowledge base."""
    try:
        run     = json.loads(run_json)
        summary = (
            f"Run {run.get('run_id')}\n"
            f"Hypothesis : {run.get('selected_hypothesis', '')}\n"
            f"Domain     : {run.get('procedure', {}).get('domain', '')}\n"
            f"Confidence : {run.get('simulation_result', {}).get('confidence_score', '')}\n"
            f"Audit Score: {run.get('audit_score', '')}\n"
            f"Verdict    : {run.get('audit_report', {}).get('verdict', '')}"
        )
        COLLECTIONS["global"].add_texts(
            texts     = [summary],
            metadatas = [{
                "run_id"     : run.get("run_id", "?"),
                "domain"     : run.get("procedure", {}).get("domain", "?"),
                "audit_score": str(run.get("audit_score", 0)),
            }],
        )
        return json.dumps({"stored": True, "summary": summary})
    except Exception as e:
        return json.dumps({"stored": False, "error": str(e)})


@tool
def recall_relevant_knowledge(query: str) -> str:
    """Searches global knowledge base for relevant past experiments."""
    results = COLLECTIONS["global"].similarity_search(query, k=5)
    if not results:
        return "No relevant past knowledge found."
    return "\n\n".join([f"Past run:\n{r.page_content}" for r in results])


def run_l6(state: PipelineState, llm, callbacks) -> PipelineState:
    """L6 entry point — Memory & Knowledge Agent."""
    state.pipeline_log.append("[L6] Memory & Knowledge Agent started")

    agent = initialize_agent(
        tools        = [store_full_run, recall_relevant_knowledge],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L6},
    )

    # Trim large fields to keep prompt manageable
    state_dict = state.dict()
    state_dict.pop("html_animation_path", None)

    prompt = (
        f"1. Store this complete run to memory: {json.dumps(state_dict, default=str)[:3000]}\n"
        f'2. Recall any relevant past knowledge for: "{state.selected_hypothesis}"\n'
        "3. Identify any patterns across similar experiments."
    )

    response = agent.run(prompt)

    try:
        m          = re.search(r"\{.*\}", response, re.DOTALL)
        mem_result = json.loads(m.group()) if m else {}
    except Exception:
        mem_result = {}

    state.recalled_context = mem_result.get("recalled_insights", [])
    state.memory_written   = True
    state.pipeline_log.append(f"[L6] Memory written, recalled {len(state.recalled_context)} insights")
    return state
