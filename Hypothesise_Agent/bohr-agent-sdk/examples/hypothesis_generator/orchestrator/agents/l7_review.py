"""
L7 — Review & Proposal Evaluation Agent
Acts as a virtual peer reviewer: scores novelty, methodology, reproducibility,
and impact; writes an abstract; optionally generates a PDF report.
"""

from langchain_core.tools import tool
from langchain_classic.agents import initialize_agent, AgentType
from orchestrator.memory import COLLECTIONS
from orchestrator.state import PipelineState
import json
import re
import os

SYSTEM_L7 = """You are the Review & Proposal Evaluation Agent — a virtual peer reviewer.
Evaluate the complete research pipeline and respond ONLY with valid JSON:
{
  "overall_score"         : 0.0,
  "novelty_score"         : 0.0,
  "methodology_score"     : 0.0,
  "reproducibility_score" : 0.0,
  "impact_score"          : 0.0,
  "verdict"               : "accept|minor_revision|major_revision|reject",
  "strengths"             : ["..."],
  "weaknesses"            : ["..."],
  "improvements"          : ["..."],
  "abstract"              : "Research paper abstract in 150 words...",
  "recommendation"        : "Full recommendation paragraph..."
}"""


@tool
def generate_pdf_report(report_json: str) -> str:
    """Generates a PDF research report from the full pipeline results."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        data = json.loads(report_json)
        os.makedirs("./outputs", exist_ok=True)
        path   = f"./outputs/research_report_{data.get('run_id', 'report')}.pdf"
        doc    = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        body   = []

        body.append(Paragraph("Scientific Research Agent — Final Report", styles["Title"]))
        body.append(Spacer(1, 12))
        body.append(Paragraph(f"Run ID: {data.get('run_id', '?')}", styles["Normal"]))
        body.append(Paragraph(f"Research Question: {data.get('research_question', '')}", styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Hypothesis", styles["Heading1"]))
        body.append(Paragraph(data.get("selected_hypothesis", ""), styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Abstract", styles["Heading1"]))
        body.append(Paragraph(data.get("review_verdict", {}).get("abstract", ""), styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Analysis Findings", styles["Heading1"]))
        for f in data.get("analysis_report", {}).get("findings", []):
            body.append(Paragraph(f"• {f}", styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Audit Results", styles["Heading1"]))
        body.append(Paragraph(f"Audit Score: {data.get('audit_score', '?')}", styles["Normal"]))
        for issue in data.get("audit_report", {}).get("issues", []):
            body.append(Paragraph(f"⚠ {issue}", styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Review Verdict", styles["Heading1"]))
        verdict = data.get("review_verdict", {})
        body.append(Paragraph(f"Verdict: {verdict.get('verdict', '?').upper()}", styles["Heading2"]))
        body.append(Paragraph(f"Overall Score: {verdict.get('overall_score', '?')}/10", styles["Normal"]))
        for s in verdict.get("strengths", []):
            body.append(Paragraph(f"✓ {s}", styles["Normal"]))
        body.append(Spacer(1, 12))

        body.append(Paragraph("Pipeline Log", styles["Heading1"]))
        for entry in data.get("pipeline_log", []):
            body.append(Paragraph(entry, styles["Code"]))

        doc.build(body)
        return json.dumps({"success": True, "pdf_path": path})
    except ImportError:
        return json.dumps({"success": False, "error": "reportlab not installed — pip install reportlab"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def run_l7(state: PipelineState, llm, callbacks) -> PipelineState:
    """L7 entry point — Review & Proposal Evaluation Agent."""
    state.pipeline_log.append("[L7] Review & Proposal Evaluation started")

    agent = initialize_agent(
        tools        = [generate_pdf_report],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L7},
    )

    prompt = f"""Evaluate this complete research pipeline as a peer reviewer:

RESEARCH QUESTION   : {state.research_question}
HYPOTHESIS          : {state.selected_hypothesis}
DOMAIN              : {state.procedure.get('domain', '?')}
SIMULATION ENGINE   : {state.simulation_result.get('engine_used', '?')}
SIMULATION CONFIDENCE: {state.simulation_result.get('confidence_score', '?')}
ANALYSIS            : {json.dumps(state.analysis_report)[:800]}
AUDIT SCORE         : {state.audit_score} | VERDICT: {state.audit_report.get('verdict', '?')}
RECALLED INSIGHTS   : {state.recalled_context}
BIAS FLAGS          : {state.audit_report.get('bias_flags', [])}

1. Write the full peer review evaluation JSON.
2. Generate the PDF report with: {json.dumps(state.dict(), default=str)[:2000]}"""

    response = agent.run(prompt)
    clean    = re.sub(r"```json|```", "", response).strip()

    try:
        m       = re.search(r"\{.*\}", clean, re.DOTALL)
        verdict = json.loads(m.group()) if m else {}
    except Exception:
        verdict = {"verdict": "minor_revision", "overall_score": 6.0}

    state.review_verdict = verdict

    # Extract PDF path if generated
    pdf_match    = re.search(r'"pdf_path":\s*"([^"]+)"', response)
    state.pdf_path = pdf_match.group(1) if pdf_match else None

    # Persist to ChromaDB
    COLLECTIONS["reviews"].add_texts(
        texts     = [json.dumps(verdict)],
        metadatas = [{
            "run_id" : state.run_id,
            "verdict": verdict.get("verdict", "?"),
            "score"  : str(verdict.get("overall_score", 0)),
        }],
    )
    state.pipeline_log.append(
        f"[L7] Review complete: verdict={verdict.get('verdict', '?')}, "
        f"score={verdict.get('overall_score', '?')}/10"
    )
    state.status = "complete"
    return state
