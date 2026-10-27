"""
L3 — Simulation Agent Bridge
LangChain wrapper that bridges to the existing simulation_agent/ package.
Routes the procedure to the correct engine and returns structured results.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import COLLECTIONS
from orchestrator.state import PipelineState
import json
import re
import sys
import os

# Ensure simulation_agent is importable from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from simulation_agent.agent import run_simulation as sim_run


@tool
def execute_simulation(procedure_json: str) -> str:
    """
    Runs the full simulation.
    Input : JSON string of ExperimentProcedure.
    Output: JSON string of SimulationOutput.
    """
    procedure = json.loads(procedure_json)
    result    = sim_run(procedure)
    return json.dumps(result)


def run_l3(state: PipelineState, llm, callbacks) -> PipelineState:
    """L3 entry point — bridges LangChain to simulation_agent package."""
    state.pipeline_log.append("[L3] Simulation Agent started")

    agent = initialize_agent(
        tools        = [execute_simulation],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {
            "system_message": (
                "You are the Simulation Agent. Call execute_simulation with the procedure JSON. "
                "Return the full result JSON unchanged. Do not summarize or modify it."
            )
        },
    )

    result_json = agent.run(f"Run this simulation: {json.dumps(state.procedure)}")

    try:
        result = json.loads(result_json)
    except Exception:
        m      = re.search(r"\{.*\}", result_json, re.DOTALL)
        result = json.loads(m.group()) if m else {}

    state.simulation_result   = result
    state.html_animation_path = result.get("html_animation_path")

    # Persist to ChromaDB
    COLLECTIONS["simulations"].add_texts(
        texts     = [json.dumps(result.get("numerical_results", {}))],
        metadatas = [{
            "run_id" : state.run_id,
            "engine" : result.get("engine_used", "?"),
        }],
    )
    state.pipeline_log.append(
        f"[L3] Simulation complete: engine={result.get('engine_used')}, "
        f"confidence={result.get('confidence_score')}"
    )
    return state
