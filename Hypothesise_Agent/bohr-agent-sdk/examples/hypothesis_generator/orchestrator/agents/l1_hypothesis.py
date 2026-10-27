"""
L1 — Hypothesis Generation Agent
Wraps Bohrium AI + arXiv to produce 3-5 novel testable hypotheses,
then stores the selected one to ChromaDB.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from langchain_anthropic import ChatAnthropic
from orchestrator.memory import get_memory, COLLECTIONS
from orchestrator.state import PipelineState
import json
import re

SYSTEM_L1 = """You are a Hypothesis Generation Agent in a scientific research pipeline.
Given a research question, generate 3-5 novel, testable scientific hypotheses.
Always respond with valid JSON only:
{
  "hypotheses": [
    {
      "id": 1,
      "statement": "...",
      "domain": "chemistry|biology|physics|cs|general",
      "rationale": "...",
      "testability_score": 0.0,
      "novelty_score": 0.0
    }
  ],
  "selected": 1
}"""


@tool
def search_prior_hypotheses(query: str) -> str:
    """Search ChromaDB for similar past hypotheses to avoid duplication."""
    results = COLLECTIONS["hypotheses"].similarity_search(query, k=3)
    if not results:
        return "No prior hypotheses found."
    return "\n".join([f"- {r.page_content}" for r in results])


def build_l1_agent(llm, callbacks):
    return initialize_agent(
        tools        = [search_prior_hypotheses],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory       = get_memory("hypotheses"),
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L1},
    )


def run_l1(state: PipelineState, llm, callbacks) -> PipelineState:
    """L1 entry point — called by pipeline.py"""
    state.pipeline_log.append("[L1] Hypothesis generation started")

    agent  = build_l1_agent(llm, callbacks)
    prompt = (
        f"Research question: {state.research_question}\n"
        "First search for prior hypotheses, then generate new ones."
    )

    response = agent.run(prompt)

    # Parse JSON from response
    clean = re.sub(r"```json|```", "", response).strip()
    try:
        data = json.loads(clean)
    except Exception:
        m    = re.search(r"\{.*\}", clean, re.DOTALL)
        data = json.loads(m.group()) if m else {"hypotheses": [], "selected": 0}

    state.hypotheses = data.get("hypotheses", [])
    sel_id   = data.get("selected", 1)
    selected = next(
        (h for h in state.hypotheses if h.get("id") == sel_id),
        state.hypotheses[0] if state.hypotheses else {},
    )
    state.selected_hypothesis = selected.get("statement", "")

    # Persist to ChromaDB
    COLLECTIONS["hypotheses"].add_texts(
        texts     = [state.selected_hypothesis],
        metadatas = [{"run_id": state.run_id, "domain": selected.get("domain", "?")}],
    )
    state.pipeline_log.append(f"[L1] Selected hypothesis: {state.selected_hypothesis[:80]}")
    return state
