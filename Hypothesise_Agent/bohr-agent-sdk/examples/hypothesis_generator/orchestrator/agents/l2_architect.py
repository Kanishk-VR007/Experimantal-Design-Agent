"""
L2 — Experiment Architect Agent
Uses local Ollama (llama3) to design a complete experimental procedure.
Falls back to Claude if Ollama is unavailable.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import get_memory, COLLECTIONS
from orchestrator.state import PipelineState
import json
import re

SYSTEM_L2 = """You are an Experiment Architect Agent. Given a hypothesis, design a complete
experimental procedure. Respond ONLY with valid JSON:
{
  "domain": "chemistry|biology|physics|computer science|general",
  "experiment_type": "titration|growth_curve|pendulum|bubble_sort|...",
  "steps": ["Step 1...", "Step 2...", "..."],
  "reagents": [{"name": "...", "smiles": "...", "concentration_M": 0.1}],
  "parameters": {"temperature_K": 298, "reaction_time_s": 120},
  "expected_metrics": ["conversion_%", "rate_constant_k"],
  "controls": ["positive_control", "negative_control"],
  "safety_notes": ["..."]
}"""


@tool
def recall_similar_procedures(domain: str) -> str:
    """Recall past experimental procedures from memory for this domain."""
    results = COLLECTIONS["procedures"].similarity_search(domain, k=3)
    return "\n".join([r.page_content for r in results]) if results else "No prior procedures."


def run_l2(state: PipelineState, callbacks) -> PipelineState:
    """L2 entry point — uses local Ollama (llama3), falls back to Claude."""
    state.pipeline_log.append("[L2] Experiment Architect started")

    try:
        from langchain_community.llms import Ollama
        llm = Ollama(model="llama3", temperature=0)
    except Exception:
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0, max_tokens=4096)

    agent = initialize_agent(
        tools        = [recall_similar_procedures],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory       = get_memory("procedures"),
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L2},
    )

    prompt = (
        f'Design an experiment to test this hypothesis:\n"{state.selected_hypothesis}"\n'
        "Recall any similar procedures first, then design the procedure."
    )

    response = agent.run(prompt)
    clean    = re.sub(r"```json|```", "", response).strip()
    try:
        m         = re.search(r"\{.*\}", clean, re.DOTALL)
        procedure = json.loads(m.group()) if m else {}
    except Exception:
        procedure = {}

    # Always inject hypothesis for the Simulation Agent
    procedure["hypothesis"] = state.selected_hypothesis
    state.procedure = procedure

    # Persist to ChromaDB
    COLLECTIONS["procedures"].add_texts(
        texts     = [json.dumps(procedure)],
        metadatas = [{"run_id": state.run_id, "domain": procedure.get("domain", "?")}],
    )
    state.pipeline_log.append(
        f"[L2] Procedure designed: domain={procedure.get('domain','?')}, "
        f"type={procedure.get('experiment_type','?')}"
    )
    return state
