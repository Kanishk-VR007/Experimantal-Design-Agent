"""
Evaluation Agent — Layer 8 (L8)
Scores every layer independently → sends refinement instructions back to the Orchestrator.
"""

import json
import re
import time
from datetime import datetime
from langchain.tools import tool
from langchain.agents import initialize_agent, AgentType
from langchain_anthropic import ChatAnthropic
from orchestrator.state import PipelineState
from orchestrator.memory import COLLECTIONS

# ── Per-layer scoring rubrics ────────────────────────────────
RUBRICS = {
    "L1_hypothesis": {
        "criteria": ["testability", "novelty", "domain_clarity", "specificity"],
        "weights" : [0.30,          0.25,      0.25,             0.20],
    },
    "L2_architect": {
        "criteria": ["step_completeness", "parameter_precision", "safety_notes", "reproducibility"],
        "weights" : [0.35,                0.30,                  0.15,            0.20],
    },
    "L3_simulation": {
        "criteria": ["engine_match", "confidence", "plot_richness", "numerical_completeness"],
        "weights" : [0.25,           0.35,         0.20,            0.20],
    },
    "L4_analysis": {
        "criteria": ["statistical_rigor", "finding_depth", "anomaly_detection", "narrative_clarity"],
        "weights" : [0.35,                0.30,            0.20,                0.15],
    },
    "L5_auditor": {
        "criteria": ["bias_coverage", "monte_carlo_done", "integrity_score", "actionability"],
        "weights" : [0.30,            0.25,               0.25,              0.20],
    },
    "L6_memory": {
        "criteria": ["storage_success", "recall_relevance", "patterns_found", "context_richness"],
        "weights" : [0.30,              0.30,               0.20,             0.20],
    },
    "L7_review": {
        "criteria": ["verdict_justification", "score_spread", "abstract_quality", "pdf_generated"],
        "weights" : [0.35,                    0.25,           0.25,               0.15],
    },
}

SYSTEM_L8 = """You are the Evaluation Agent (L8) in a Scientific Research Pipeline.
Your job is to independently score every layer (L1-L7) and produce a structured
evaluation report. You are strict, objective, and data-driven.

For each layer you receive its output and must score it 0.0-1.0 per criterion.
Respond ONLY with valid JSON matching the exact schema provided."""


@tool
def score_layer(layer_data_json: str) -> str:
    """
    Scores a single pipeline layer against its rubric.
    Input JSON: {layer, output, rubric_criteria, rubric_weights}
    Output JSON: {layer, scores, weighted_score, issues, suggestions}
    """
    try:
        data     = json.loads(layer_data_json)
        layer    = data["layer"]
        output   = data["output"]
        criteria = data["rubric_criteria"]
        weights  = data["rubric_weights"]

        llm = ChatAnthropic(model="claude-sonnet-4-20250514",
                            temperature=0, max_tokens=800)

        prompt = f"""Score this {layer} output strictly against these criteria.

OUTPUT TO EVALUATE:
{json.dumps(output, default=str)[:1500]}

CRITERIA (score each 0.0-1.0):
{json.dumps(dict(zip(criteria, weights)), indent=2)}

Respond ONLY with valid JSON:
{{
  "layer": "{layer}",
  "criterion_scores": {{{", ".join(f'"{c}": 0.0' for c in criteria)}}},
  "issues": ["specific issue 1", "issue 2"],
  "suggestions": ["specific fix 1", "fix 2"],
  "one_line_summary": "..."
}}"""

        resp  = llm.invoke(prompt)
        clean = re.sub(r"```json|```", "", resp.content).strip()
        m     = re.search(r"\{.*\}", clean, re.DOTALL)
        result = json.loads(m.group()) if m else {}

        # Compute weighted score
        cs     = result.get("criterion_scores", {})
        wscore = round(sum(cs.get(c, 0.5) * w
                           for c, w in zip(criteria, weights)), 4)
        result["weighted_score"] = wscore
        return json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e), "weighted_score": 0.5})


@tool
def compare_to_baseline(run_id: str) -> str:
    """
    Compares current run scores to historical average from ChromaDB.
    Returns delta (positive = improved, negative = degraded).
    """
    try:
        results = COLLECTIONS["reviews"].similarity_search(run_id, k=10)
        if len(results) < 2:
            return json.dumps({"status": "insufficient_history",
                               "message": "Need 2+ past runs to compare"})

        past_scores = []
        for r in results[:-1]:   # exclude current run
            try:
                data  = json.loads(r.page_content)
                score = data.get("overall_score", 0)
                past_scores.append(float(score))
            except Exception:
                continue

        if not past_scores:
            return json.dumps({"status": "no_comparable_runs"})

        baseline = sum(past_scores) / len(past_scores)
        return json.dumps({
            "baseline_avg"  : round(baseline, 4),
            "runs_compared" : len(past_scores),
            "trend"         : "improving" if baseline > 0 else "stable",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_l8(state: PipelineState, llm, callbacks) -> PipelineState:
    """
    L8 entry point — Evaluation Agent.
    Scores all 7 layers, builds EvalReport, sets eval_passed flag.
    """
    state.pipeline_log.append("[L8] Evaluation Agent started")
    start = time.time()

    agent = initialize_agent(
        tools        = [score_layer, compare_to_baseline],
        llm          = llm,
        agent        = AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose      = True,
        callbacks    = callbacks,
        agent_kwargs = {"system_message": SYSTEM_L8},
    )

    # Build per-layer output snapshots for scoring
    layer_outputs = {
        "L1_hypothesis": {
            "hypotheses"          : state.hypotheses,
            "selected_hypothesis" : state.selected_hypothesis,
        },
        "L2_architect": {
            "domain"      : state.procedure.get("domain"),
            "steps"       : state.procedure.get("steps", []),
            "parameters"  : state.procedure.get("parameters", {}),
            "safety_notes": state.procedure.get("safety_notes", []),
        },
        "L3_simulation": {
            "engine_used"       : state.simulation_result.get("engine_used"),
            "confidence_score"  : state.simulation_result.get("confidence_score"),
            "plot_count"        : len(state.simulation_result.get("plot_data", [])),
            "numerical_results" : state.simulation_result.get("numerical_results", {}),
        },
        "L4_analysis": {
            "findings"           : state.analysis_report.get("findings", []),
            "statistical_summary": state.analysis_report.get("statistical_summary", {}),
            "anomalies"          : state.analysis_report.get("anomalies", []),
            "narrative"          : state.analysis_report.get("narrative", "")[:300],
        },
        "L5_auditor": {
            "bias_flags"      : state.audit_report.get("bias_flags", []),
            "robustness_score": state.audit_report.get("robustness_score"),
            "integrity_score" : state.audit_report.get("integrity_score"),
            "verdict"         : state.audit_report.get("verdict"),
        },
        "L6_memory": {
            "memory_written"  : state.memory_written,
            "recalled_context": state.recalled_context,
        },
        "L7_review": {
            "verdict"      : state.review_verdict.get("verdict"),
            "overall_score": state.review_verdict.get("overall_score"),
            "abstract"     : state.review_verdict.get("abstract", "")[:200],
            "pdf_generated": bool(state.pdf_path),
        },
    }

    # Score each layer independently
    layer_scores    = {}
    all_issues      = {}
    all_suggestions = {}

    for layer, output in layer_outputs.items():
        rubric = RUBRICS[layer]
        tool_input = json.dumps({
            "layer"           : layer,
            "output"          : output,
            "rubric_criteria" : rubric["criteria"],
            "rubric_weights"  : rubric["weights"],
        })
        raw = score_layer.invoke(tool_input)
        try:
            result = json.loads(raw)
            layer_scores[layer]    = result
            all_issues[layer]      = result.get("issues", [])
            all_suggestions[layer] = result.get("suggestions", [])
        except Exception:
            layer_scores[layer] = {"weighted_score": 0.5, "issues": [], "suggestions": []}

    # Compute overall pipeline score
    scores_list     = [v.get("weighted_score", 0.5) for v in layer_scores.values()]
    overall_score   = round(sum(scores_list) / len(scores_list), 4)
    weakest_layer   = min(layer_scores, key=lambda l: layer_scores[l].get("weighted_score", 0))
    strongest_layer = max(layer_scores, key=lambda l: layer_scores[l].get("weighted_score", 0))
    eval_passed     = overall_score >= 0.70

    # Compare to baseline
    baseline_raw = compare_to_baseline.invoke(state.run_id)
    try:
        baseline = json.loads(baseline_raw)
    except Exception:
        baseline = {}

    # Build structured EvalReport
    eval_report = {
        "run_id"          : state.run_id,
        "evaluated_at"    : datetime.utcnow().isoformat(),
        "eval_duration_s" : round(time.time() - start, 2),
        "overall_score"   : overall_score,
        "eval_passed"     : eval_passed,
        "pass_threshold"  : 0.70,
        "weakest_layer"   : weakest_layer,
        "strongest_layer" : strongest_layer,
        "layer_scores"    : {
            l: {
                "score"      : v.get("weighted_score", 0),
                "grade"      : _grade(v.get("weighted_score", 0)),
                "issues"     : v.get("issues", []),
                "suggestions": v.get("suggestions", []),
                "summary"    : v.get("one_line_summary", ""),
                "criteria"   : v.get("criterion_scores", {}),
            }
            for l, v in layer_scores.items()
        },
        "baseline_comparison": baseline,
        "refinement_needed"  : not eval_passed,
        "refinement_targets" : [
            l for l, v in layer_scores.items()
            if v.get("weighted_score", 1.0) < 0.65
        ],
    }

    # Attach to state
    state.eval_report        = eval_report
    state.eval_passed        = eval_passed
    state.eval_overall_score = overall_score

    # Persist to ChromaDB
    COLLECTIONS["reviews"].add_texts(
        texts     = [json.dumps({"run_id": state.run_id,
                                 "overall_score": overall_score,
                                 "eval_passed": eval_passed})],
        metadatas = [{"run_id": state.run_id, "type": "eval",
                      "score": str(overall_score)}]
    )
    state.pipeline_log.append(
        f"[L8] Eval complete: score={overall_score:.2%}, "
        f"passed={eval_passed}, weakest={weakest_layer}"
    )
    return state


def _grade(score: float) -> str:
    if score >= 0.90: return "A"
    if score >= 0.80: return "B"
    if score >= 0.70: return "C"
    if score >= 0.60: return "D"
    return "F"


def generate_eval_dashboard(eval_report: dict, pipeline_log: list = None) -> str:
    """
    Generates a self-contained HTML dashboard showing
    the full evaluation output for one pipeline run.
    Save to ./outputs/eval_{run_id}.html
    """
    layers    = eval_report.get("layer_scores", {})
    overall   = eval_report.get("overall_score", 0)
    passed    = eval_report.get("eval_passed", False)
    run_id    = eval_report.get("run_id", "?")
    weakest   = eval_report.get("weakest_layer", "?")
    strongest = eval_report.get("strongest_layer", "?")
    targets   = eval_report.get("refinement_targets", [])
    log       = pipeline_log or []

    layer_cards_js = json.dumps([
        {
            "name"       : layer,
            "score"      : round(data["score"], 3),
            "grade"      : data["grade"],
            "summary"    : data.get("summary", ""),
            "issues"     : data.get("issues", []),
            "suggestions": data.get("suggestions", []),
            "criteria"   : data.get("criteria", {}),
            "needsFix"   : layer in targets,
        }
        for layer, data in layers.items()
    ])

    log_js       = json.dumps(log[-30:])
    color        = "#00ffd0" if passed else "#ff6b35"
    verdict_text = "PASSED ✓" if passed else "NEEDS REFINEMENT ↩"

    refinement_banner = "" if passed else f"""
  <div class="refinement-banner">
    <div class="rb-left">
      <h3>Refinement Required</h3>
      <p>The following layers scored below 0.70 and will be rerun by the Orchestrator</p>
    </div>
    <div class="rb-targets">
      {"".join(f'<span class="rb-tag">{t}</span>' for t in targets)}
    </div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evaluation Report — {run_id}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800;900&display=swap');

:root {{
  --bg      : #020509;
  --surface : #070d14;
  --border  : #0f1e2e;
  --text    : #9bb8d0;
  --bright  : #ddeeff;
  --accent  : {color};
  --pass    : #00ffd0;
  --fail    : #ff6b35;
  --warn    : #f7c948;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}

body {{
  background: var(--bg);
  font-family: 'Space Mono', monospace;
  color: var(--text);
  min-height: 100vh;
  padding: 32px 24px;
}}

body::before {{
  content:'';
  position:fixed; inset:0; z-index:0;
  background-image:
    linear-gradient(rgba(0,255,208,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,255,208,.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events:none;
}}

.wrap {{ position:relative; z-index:1; max-width:1100px; margin:0 auto; }}

.header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 36px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}}
.title-block h1 {{
  font-family: 'Syne', sans-serif;
  font-size: 2rem;
  font-weight: 900;
  color: var(--bright);
  letter-spacing: -1px;
  line-height: 1;
}}
.title-block .sub {{
  font-size: .62rem;
  color: #2a4560;
  letter-spacing: 3px;
  margin-top: 6px;
  text-transform: uppercase;
}}
.verdict-badge {{
  background: rgba(0,0,0,.5);
  border: 2px solid var(--accent);
  border-radius: 10px;
  padding: 14px 22px;
  text-align: center;
  box-shadow: 0 0 30px rgba(0,255,208,.08);
}}
.verdict-badge .v-label {{ font-size: .58rem; color: #2a4560; letter-spacing: 3px; text-transform: uppercase; }}
.verdict-badge .v-text  {{ font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 800; color: var(--accent); margin-top: 4px; }}

.score-section {{
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 28px;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 28px;
  margin-bottom: 24px;
}}
.ring-wrap {{ position:relative; width:120px; height:120px; }}
.ring-wrap canvas {{ position:absolute; top:0; left:0; }}
.ring-center {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.ring-pct {{ font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:900; color:var(--bright); }}
.ring-lbl {{ font-size:.55rem; color:#2a4560; letter-spacing:2px; text-transform:uppercase; }}
.score-meta {{ display:flex; flex-direction:column; gap:10px; }}
.meta-row {{ display:flex; gap:24px; flex-wrap:wrap; }}
.meta-item {{ background:#0a131e; border:1px solid var(--border); border-radius:8px; padding:10px 14px; }}
.meta-item .m-val {{ font-family:'Syne',sans-serif; font-size:.95rem; font-weight:700; color:var(--bright); }}
.meta-item .m-lbl {{ font-size:.55rem; color:#2a4560; letter-spacing:2px; margin-top:2px; text-transform:uppercase; }}

.section-title {{ font-size:.6rem; letter-spacing:3px; color:#2a4560; text-transform:uppercase; margin-bottom:14px; margin-top:28px; }}

.layer-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:14px; margin-bottom:28px; }}

.layer-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  transition: border-color .2s, transform .2s;
  cursor: pointer;
}}
.layer-card:hover   {{ border-color: var(--accent); transform: translateY(-2px); }}
.layer-card.fix-needed {{ border-color: var(--fail); }}
.layer-card.best    {{ border-color: var(--pass); }}

.card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
.layer-name  {{ font-family:'Syne',sans-serif; font-size:.8rem; font-weight:800; color:var(--bright); }}
.grade-badge {{ font-family:'Syne',sans-serif; font-size:.75rem; font-weight:900; width:28px; height:28px; border-radius:6px; display:flex; align-items:center; justify-content:center; }}
.grade-A {{ background:rgba(0,255,208,.15); color:var(--pass); }}
.grade-B {{ background:rgba(96,165,250,.15); color:#60a5fa; }}
.grade-C {{ background:rgba(247,201,72,.15); color:var(--warn); }}
.grade-D {{ background:rgba(255,107,53,.15); color:var(--fail); }}
.grade-F {{ background:rgba(255,50,50,.15); color:#ff3232; }}

.score-bar-wrap {{ margin:10px 0; }}
.score-bar-bg {{ height:6px; background:#0a131e; border-radius:3px; overflow:hidden; }}
.score-bar-fill {{ height:100%; border-radius:3px; transition: width 1s cubic-bezier(.4,0,.2,1); }}
.score-val {{ font-size:.65rem; color:var(--bright); font-weight:700; margin-top:4px; text-align:right; }}

.summary-text {{ font-size:.62rem; color:var(--text); line-height:1.7; margin-bottom:10px; }}

.issues-list, .sug-list {{ margin-top:8px; display:none; }}
.layer-card.expanded .issues-list,
.layer-card.expanded .sug-list {{ display:block; }}
.issues-list li, .sug-list li {{ font-size:.6rem; line-height:1.6; margin-bottom:3px; padding-left:14px; position:relative; list-style:none; }}
.issues-list li::before {{ content:'⚠'; position:absolute; left:0; color:var(--fail); }}
.sug-list li::before   {{ content:'→'; position:absolute; left:0; color:var(--pass); }}
.expand-btn {{ font-size:.6rem; color:#2a4560; cursor:pointer; margin-top:10px; border:none; background:none; font-family:'Space Mono',monospace; letter-spacing:1px; text-transform:uppercase; padding:0; transition:color .2s; }}
.expand-btn:hover {{ color:var(--accent); }}

.criteria-grid {{ display:grid; gap:5px; margin-top:10px; display:none; }}
.layer-card.expanded .criteria-grid {{ display:grid; }}
.crit-row  {{ display:flex; align-items:center; gap:8px; }}
.crit-name {{ font-size:.55rem; color:#2a4560; width:130px; flex-shrink:0; text-transform:uppercase; letter-spacing:1px; }}
.crit-bar  {{ flex:1; height:4px; background:#0a131e; border-radius:2px; overflow:hidden; }}
.crit-fill {{ height:100%; border-radius:2px; background:var(--accent); }}
.crit-val  {{ font-size:.55rem; color:var(--bright); width:30px; text-align:right; }}

.log-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top:24px; }}
.log-panel h3 {{ font-size:.6rem; letter-spacing:3px; color:#2a4560; text-transform:uppercase; margin-bottom:12px; }}
.log-scroll {{ max-height: 220px; overflow-y:auto; scrollbar-width: thin; scrollbar-color: #0f1e2e var(--bg); }}
.log-line {{ font-size:.62rem; line-height:1.8; color:#2a4560; border-bottom:1px solid #070d14; padding:2px 0; }}
.log-line.l8  {{ color:#00ffd0; }}
.log-line.err {{ color:var(--fail); }}
.log-line.ref {{ color:var(--warn); }}

.refinement-banner {{ background: rgba(255,107,53,.06); border: 1px solid rgba(255,107,53,.3); border-radius:10px; padding:16px 20px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; }}
.rb-left h3 {{ font-family:'Syne',sans-serif; font-size:.85rem; color:var(--fail); font-weight:800; }}
.rb-left p  {{ font-size:.62rem; color:var(--text); margin-top:4px; }}
.rb-targets {{ display:flex; gap:6px; flex-wrap:wrap; }}
.rb-tag {{ background:rgba(255,107,53,.1); border:1px solid rgba(255,107,53,.3); border-radius:5px; padding:4px 10px; font-size:.6rem; color:var(--fail); }}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div class="title-block">
      <h1>Evaluation Report</h1>
      <div class="sub">Scientific Research Agent · Layer 8 · Run {run_id}</div>
    </div>
    <div class="verdict-badge">
      <div class="v-label">Verdict</div>
      <div class="v-text">{verdict_text}</div>
    </div>
  </div>

  {refinement_banner}

  <div class="score-section">
    <div class="ring-wrap">
      <canvas id="ring" width="120" height="120"></canvas>
      <div class="ring-center">
        <div class="ring-pct" id="ring-pct">0%</div>
        <div class="ring-lbl">Overall</div>
      </div>
    </div>
    <div class="score-meta">
      <div class="meta-row">
        <div class="meta-item">
          <div class="m-val">{overall:.2%}</div>
          <div class="m-lbl">Pipeline Score</div>
        </div>
        <div class="meta-item">
          <div class="m-val" style="color:var(--pass)">{strongest.replace('_',' ')}</div>
          <div class="m-lbl">Strongest Layer</div>
        </div>
        <div class="meta-item">
          <div class="m-val" style="color:var(--fail)">{weakest.replace('_',' ')}</div>
          <div class="m-lbl">Weakest Layer</div>
        </div>
        <div class="meta-item">
          <div class="m-val">{eval_report.get('eval_duration_s', 0)}s</div>
          <div class="m-lbl">Eval Duration</div>
        </div>
        <div class="meta-item">
          <div class="m-val">{len(targets)}</div>
          <div class="m-lbl">Layers to Refine</div>
        </div>
      </div>
    </div>
  </div>

  <div class="section-title">Per-Layer Evaluation</div>
  <div class="layer-grid" id="layer-grid"></div>

  <div class="log-panel">
    <h3>Pipeline Log</h3>
    <div class="log-scroll" id="log-scroll"></div>
  </div>

</div>

<script>
const LAYERS  = {layer_cards_js};
const LOG     = {log_js};
const OVERALL = {overall};
const PASSED  = {'true' if passed else 'false'};

function drawRing(pct) {{
  const c   = document.getElementById('ring');
  const ctx = c.getContext('2d');
  const cx  = 60, cy = 60, r = 50, lw = 8;
  ctx.clearRect(0, 0, 120, 120);
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = '#0a131e'; ctx.lineWidth = lw; ctx.stroke();
  const start = -Math.PI / 2;
  const end   = start + (Math.PI * 2 * pct);
  ctx.beginPath(); ctx.arc(cx, cy, r, start, end);
  ctx.strokeStyle = PASSED ? '#00ffd0' : '#ff6b35';
  ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, r, start, end);
  ctx.strokeStyle = PASSED ? 'rgba(0,255,208,.2)' : 'rgba(255,107,53,.2)';
  ctx.lineWidth = lw + 6; ctx.lineCap = 'round'; ctx.stroke();
}}

let p = 0;
const t = setInterval(() => {{
  p = Math.min(p + OVERALL / 40, OVERALL);
  drawRing(p);
  document.getElementById('ring-pct').textContent = (p * 100).toFixed(1) + '%';
  if (p >= OVERALL) clearInterval(t);
}}, 20);

function barColor(s) {{
  if (s >= .9) return '#00ffd0';
  if (s >= .8) return '#60a5fa';
  if (s >= .7) return '#f7c948';
  if (s >= .6) return '#fb923c';
  return '#ff6b35';
}}

const grid = document.getElementById('layer-grid');
LAYERS.forEach((layer, idx) => {{
  const card = document.createElement('div');
  card.className = 'layer-card' +
    (layer.needsFix ? ' fix-needed' : '') +
    (layer.name === '{strongest}' ? ' best' : '');

  const critRows = Object.entries(layer.criteria).map(([k,v]) => `
    <div class="crit-row">
      <div class="crit-name">${{k.replace(/_/g,' ')}}</div>
      <div class="crit-bar"><div class="crit-fill" style="width:${{(v*100).toFixed(0)}}%"></div></div>
      <div class="crit-val">${{(v*100).toFixed(0)}}%</div>
    </div>`).join('');

  const issueItems = layer.issues.map(i => `<li>${{i}}</li>`).join('');
  const sugItems   = layer.suggestions.map(s => `<li>${{s}}</li>`).join('');

  card.innerHTML = `
    <div class="card-header">
      <div class="layer-name">${{layer.name.replace('_',' ')}}</div>
      <div class="grade-badge grade-${{layer.grade}}">${{layer.grade}}</div>
    </div>
    <div class="score-bar-wrap">
      <div class="score-bar-bg">
        <div class="score-bar-fill" id="bar-${{idx}}"
             style="width:0%; background:${{barColor(layer.score)}}"></div>
      </div>
      <div class="score-val">${{(layer.score*100).toFixed(1)}}%</div>
    </div>
    <div class="summary-text">${{layer.summary || 'No summary available'}}</div>
    ${{issueItems ? `<ul class="issues-list">${{issueItems}}</ul>` : ''}}
    ${{sugItems   ? `<ul class="sug-list">${{sugItems}}</ul>` : ''}}
    <div class="criteria-grid">${{critRows}}</div>
    <button class="expand-btn" onclick="toggleCard(this)">&#9660; details</button>
  `;
  grid.appendChild(card);

  setTimeout(() => {{
    const bar = document.getElementById(`bar-${{idx}}`);
    if (bar) bar.style.width = (layer.score * 100) + '%';
  }}, 100 + idx * 80);
}});

function toggleCard(btn) {{
  const card = btn.closest('.layer-card');
  card.classList.toggle('expanded');
  btn.textContent = card.classList.contains('expanded') ? '&#9650; hide' : '&#9660; details';
}}

const logScroll = document.getElementById('log-scroll');
LOG.forEach(line => {{
  const d = document.createElement('div');
  d.className = 'log-line' +
    (line.includes('[L8]') ? ' l8' : '') +
    (line.includes('ERROR') || line.includes('failed') ? ' err' : '') +
    (line.includes('REFINE') ? ' ref' : '');
  d.textContent = line;
  logScroll.appendChild(d);
}});
logScroll.scrollTop = logScroll.scrollHeight;
</script>
</body>
</html>"""
