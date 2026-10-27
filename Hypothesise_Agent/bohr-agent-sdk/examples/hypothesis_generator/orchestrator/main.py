"""
Main entry point — run this file to start the full research pipeline.

Setup:
    1. Create a .env file next to this directory with:
         ANTHROPIC_API_KEY=sk-ant-...
    2. Ensure Ollama is running (optional — Claude is used as fallback):
         ollama serve
         ollama pull llama3
    3. Install dependencies:
         pip install langchain langchain-anthropic langchain-community
         pip install langchain-ollama chromadb sentence-transformers
         pip install anthropic scipy numpy reportlab python-dotenv

Run:
    python -m orchestrator.main
    # or
    python orchestrator/main.py
"""

import os
from dotenv import load_dotenv

# Load ANTHROPIC_API_KEY and any other keys from .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from orchestrator.pipeline import run_pipeline  # noqa: E402


if __name__ == "__main__":
    # ── Example 1: Chemistry ──────────────────────────────────────
    result = run_pipeline(
        "Does increasing temperature increase the rate of enzyme-catalyzed reactions?"
    )

    # ── Example 2: Computer Science ───────────────────────────────
    # result = run_pipeline(
    #     "Which sorting algorithm is most efficient for nearly-sorted arrays?"
    # )

    # ── Example 3: Biology ────────────────────────────────────────
    # result = run_pipeline(
    #     "How does antibiotic concentration affect bacterial growth rate?"
    # )

    # ── Print outputs ─────────────────────────────────────────────
    print("\n── RESULTS ──────────────────────────────────────────────")
    print("Hypothesis :", result.selected_hypothesis)
    print("Engine     :", result.simulation_result.get("engine_used"))
    print("Findings   :", result.analysis_report.get("findings"))
    print("Audit Score:", result.audit_score)
    print("Verdict    :", result.review_verdict.get("verdict"))
    print("PDF        :", result.pdf_path)
    print("Animation  :", result.html_animation_path)
