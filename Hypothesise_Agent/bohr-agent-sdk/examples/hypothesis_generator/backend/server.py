#!/usr/bin/env python3
"""
FastAPI Backend for Experimental Design Agent
==============================================
Provides REST API endpoints for React frontend.
Streams Ollama responses in real-time using Server-Sent Events (SSE).
Includes Layer 3 Simulation Agent integration.
"""

import os
import sys
import time
import json
import asyncio
import threading
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Add simulation agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulation_agent.agent import run_simulation, extract_procedure_from_text
from simulation_agent.router import route
from simulation_agent.output_formatter import format_output
from simulation_agent.visualization.scene_generator import generate_scene_specification
from simulation_agent.llm_client import check_llm_health, check_ollama_status, stream_chat_completion, get_llm_config
from simulation_agent.prompt_refiner import refine_prompt_with_ollama_qwen, build_deepseek_messages

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configuration
_llm_cfg = get_llm_config()
OLLAMA_URL = _llm_cfg["ollama_url"]
OLLAMA_MODEL = _llm_cfg["ollama_model"]
LMSTUDIO_URL = _llm_cfg["lmstudio_url"]
LMSTUDIO_MODEL = _llm_cfg["lmstudio_model"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="Experimental Design Agent API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ──────────────────────────────────────────────────────

class ExperimentRequest(BaseModel):
    topic: str
    max_papers: int = 3
    use_mock_data: bool = False
    domain: Optional[str] = None


class SimulationRequest(BaseModel):
    topic: str
    design: str
    domain: Optional[str] = None
    refinement: Optional[Dict[str, Any]] = None


class VisualizationGenerateRequest(BaseModel):
    topic: str
    procedure: Dict[str, Any] = {}
    numerical_results: Dict[str, Any] = {}
    plot_data: List[Dict[str, Any]] = []
    domain: Optional[str] = None


class VisualizationUpdateRequest(BaseModel):
    experiment_id: str
    domain: str
    parameters: Dict[str, Any]
    current_procedure: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    ollama_available: bool
    llm_available: bool = False
    provider: str = "lmstudio"
    active_model: Optional[str] = None
    refiner_available: bool = False
    refiner_model: Optional[str] = None
    models: List[str]


# ─── Mock Data for Testing ───────────────────────────────────────────────

MOCK_PAPERS = [
    {
        "title": "Deep Learning for Image Classification: A Comprehensive Survey",
        "abstract": "This paper surveys recent advances in deep learning for image classification, "
                   "comparing CNNs, Transformers, and hybrid architectures. Results show transformers "
                   "achieve 95% accuracy on ImageNet while CNNs reach 92%.",
        "authors": ["Smith, J.", "Doe, A.", "Johnson, B."],
        "source": "Bohrium",
        "citations": 342,
        "url": "https://example.com/paper1"
    },
    {
        "title": "Transformer Architecture Optimization for Computer Vision",
        "abstract": "We propose an optimized transformer architecture for vision tasks. "
                   "Our approach reduces computational cost by 40% while maintaining accuracy. "
                   "Experiments on CIFAR-10 and ImageNet show promising results.",
        "authors": ["Lee, K.", "Wang, L."],
        "source": "arXiv",
        "citations": 127,
        "url": "https://arxiv.org/abs/2024.12345"
    },
    {
        "title": "Convolutional Neural Networks: Recent Improvements and Applications",
        "abstract": "Recent improvements in CNN architectures including residual connections, "
                   "attention mechanisms, and efficient convolutions. We achieve state-of-the-art "
                   "on multiple benchmarks with reduced parameters.",
        "authors": ["Chen, Y.", "Zhang, H.", "Liu, M."],
        "source": "Bohrium",
        "citations": 256,
        "url": "https://example.com/paper3"
    }
]


# ─── Helper Functions ────────────────────────────────────────────────────

def check_ollama() -> Dict:
    """Check primary local LLM provider health (LM Studio first, Ollama fallback)."""
    return check_llm_health()


def fetch_arxiv_papers(query: str, max_results: int = 3) -> List[Dict]:
    """Fetch real papers from arXiv (free, no API key needed)"""
    papers = []
    try:
        import urllib.parse
        safe_query = urllib.parse.quote(query)
        url = (
            f"http://export.arxiv.org/api/query"
            f"?search_query=all:{safe_query}"
            f"&start=0&max_results={max_results}"
            f"&sortBy=relevance&sortOrder=descending"
        )
        response = requests.get(url, timeout=15,
                                headers={"User-Agent": "ExperimentalDesignAgent/1.0"})
        if response.status_code != 200:
            return papers

        # Parse Atom XML
        import xml.etree.ElementTree as ET
        NS = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(response.text)
        for entry in root.findall("atom:entry", NS)[:max_results]:
            title   = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")[:500]
            link_el = entry.find("atom:id", NS)
            link    = link_el.text.strip() if link_el is not None else ""
            authors = [a.findtext("atom:name", "", NS)
                       for a in entry.findall("atom:author", NS)]
            if title:
                papers.append({
                    "source": "arXiv",
                    "title":    title,
                    "authors":  authors,
                    "abstract": summary,
                    "url":      link,
                    "citations": 0,
                })
    except Exception as e:
        print(f"arXiv fetch error: {e}")
    return papers


def fetch_semantic_scholar_papers(query: str, max_results: int = 3) -> List[Dict]:
    """Fetch real papers from Semantic Scholar (free, no API key needed)"""
    papers = []
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query":  query,
            "limit":  max_results,
            "fields": "title,authors,abstract,year,citationCount,externalIds,openAccessPdf",
        }
        response = requests.get(url, params=params, timeout=15,
                                headers={"User-Agent": "ExperimentalDesignAgent/1.0"})
        if response.status_code != 200:
            return papers
        data = response.json().get("data", [])
        for item in data[:max_results]:
            ext   = item.get("externalIds") or {}
            arxiv = ext.get("ArXiv", "")
            doi   = ext.get("DOI", "")
            link  = (
                f"https://arxiv.org/abs/{arxiv}" if arxiv else
                f"https://doi.org/{doi}"         if doi   else
                f"https://www.semanticscholar.org/paper/{item.get('paperId','')}"
            )
            papers.append({
                "source":    "Semantic Scholar",
                "title":     item.get("title", ""),
                "authors":   [a.get("name", "") for a in item.get("authors", [])],
                "abstract":  (item.get("abstract") or "")[:500],
                "url":       link,
                "citations": item.get("citationCount", 0),
            })
    except Exception as e:
        print(f"Semantic Scholar fetch error: {e}")
    return papers


def fetch_papers(query: str, max_results: int = 3) -> List[Dict]:
    """
    Fetch real research papers.
    Tries arXiv first (best for CS/Physics/Math), then Semantic Scholar.
    Returns empty list only if both sources fail.
    """
    papers = fetch_arxiv_papers(query, max_results)
    if len(papers) < max_results:
        need = max_results - len(papers)
        fallback = fetch_semantic_scholar_papers(query, need)
        # Deduplicate by title
        existing_titles = {p["title"].lower() for p in papers}
        for p in fallback:
            if p["title"].lower() not in existing_titles:
                papers.append(p)
                existing_titles.add(p["title"].lower())
    print(f"[papers] Found {len(papers)} real papers for: {query!r}")
    return papers[:max_results]


#: Markdown sections every complete experimental design is expected to contain.
REQUIRED_HEADINGS = [
    "## 1. HYPOTHESIS",
    "## 2. VARIABLES",
    "## 3. EXPERIMENTAL DESIGN",
    "## 4. METHODOLOGY",
    "## 5. DATA ANALYSIS",
    "## 6. EXPECTED OUTCOMES",
    "## 7. LIMITATIONS",
]

#: Minimum number of sections required before a design is reported as incomplete.
MIN_REQUIRED_HEADINGS = 5


def _heading_keyword(heading: str) -> str:
    """'## 3. EXPERIMENTAL DESIGN' -> 'EXPERIMENTAL DESIGN'."""
    return heading.split(". ", 1)[-1].strip().upper()


def check_design_completeness(text: str) -> Dict[str, Any]:
    """
    Count how many of the 7 required design sections appear in the generated text.

    Matching is case-insensitive and keyword-based, so numbering/layout drift
    (e.g. "## Hypothesis" instead of "## 1. HYPOTHESIS") still counts.
    Returns a report instead of raising: incomplete designs are flagged, not blocked.
    """
    haystack = (text or "").upper()
    missing = []
    found = 0
    for heading in REQUIRED_HEADINGS:
        keyword = _heading_keyword(heading)
        if keyword and keyword in haystack:
            found += 1
        else:
            missing.append(heading)
    return {
        "found_headings": found,
        "total_required": len(REQUIRED_HEADINGS),
        "missing": missing,
    }


# ─── API Endpoints ───────────────────────────────────────────────────────

@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    return {
        "name": "Experimental Design Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API, LM Studio generator, and Ollama Qwen refiner health"""
    llm_status = check_llm_health()
    refiner_status = check_ollama_status()

    return {
        "status": "healthy" if llm_status["available"] else "llm_unavailable",
        "ollama_available": llm_status["available"],
        "llm_available": llm_status["available"],
        "provider": llm_status.get("provider", "lmstudio"),
        "active_model": llm_status.get("active_model"),
        "refiner_available": refiner_status.get("available", False),
        "refiner_model": refiner_status.get("active_model"),
        "models": llm_status["models"],
    }


@app.post("/api/search-papers")
async def search_papers(request: ExperimentRequest):
    """Search for research papers"""
    
    if request.use_mock_data:
        return {
            "papers": MOCK_PAPERS,
            "count": len(MOCK_PAPERS),
            "source": "mock"
        }
    
    papers = fetch_papers(request.topic[:200], request.max_papers)
    source = "arxiv/semantic_scholar"

    if not papers:
        # Last resort: mock data, but flag it clearly
        papers = MOCK_PAPERS[:request.max_papers]
        source = "mock_fallback"
    
    return {
        "papers": papers,
        "count": len(papers),
        "source": source
    }


@app.post("/api/generate-design")
async def generate_design_stream(request: ExperimentRequest):
    """Generate experimental design with real-time streaming response via LM Studio"""

    async def event_generator():
        """Generate Server-Sent Events stream"""
        try:
            # 1. Start immediately so UI enters Loading Screen before network searches block
            yield f"data: {json.dumps({'type': 'start', 'stage': 'papers', 'message': 'Fetching & analyzing scientific literature...'})}\n\n"

            # 2. Fetch papers off the asyncio event loop
            if request.use_mock_data:
                papers = MOCK_PAPERS[:request.max_papers]
            else:
                papers = await asyncio.to_thread(fetch_papers, request.topic[:200], request.max_papers)
                if not papers:
                    papers = MOCK_PAPERS[:request.max_papers]

            yield f"data: {json.dumps({'type': 'papers', 'papers': papers, 'count': len(papers)})}\n\n"

            # 3. Stage 1 & 2: Token filtering, stop-word removal & Ollama Qwen prompt refinement
            yield f"data: {json.dumps({'type': 'status', 'stage': 'refining', 'message': 'Filtering stop words & refining experimental prompt via Ollama (qwen)...'})}\n\n"
            refinement = await asyncio.to_thread(refine_prompt_with_ollama_qwen, request.topic, papers)
            if request.domain:
                refinement["domain"] = request.domain
            yield f"data: {json.dumps({'type': 'refinement', 'refinement': refinement})}\n\n"

            tf_stats = refinement.get("token_filtering", {})
            raw_toks = tf_stats.get("raw_token_count", 0)
            filt_toks = tf_stats.get("filtered_token_count", 0)
            red_pct = tf_stats.get("reduction_pct", 0.0)
            ref_src = refinement.get("refiner_source", "qwen")

            yield f"data: {json.dumps({'type': 'status', 'stage': 'reasoning', 'message': f'Tokens filtered {raw_toks}→{filt_toks} (-{red_pct}% stop words) via {ref_src} · OREAL DeepSeek-R1 designing experiment...'})}\n\n"

            # 4. Construct high-precision structured context for OREAL DeepSeek-R1-Distill-Qwen-7B
            messages = build_deepseek_messages(request.topic, refinement)

            # 5. Run synchronous streaming HTTP call in worker thread and push events to asyncio.Queue
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def _worker():
                try:
                    for ev in stream_chat_completion(
                        messages=messages,
                        temperature=0.3,
                        max_tokens=2500,
                        timeout=300,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, ("event", ev))
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))

            threading.Thread(target=_worker, daemon=True).start()

            full_text = ""
            reasoning_chunks = 0
            last_status_emit = 0.0
            active_model = LMSTUDIO_MODEL
            active_provider = "lmstudio"

            while True:
                kind, payload_item = await queue.get()
                if kind == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': payload_item})}\n\n"
                    return
                if kind == "done":
                    break

                ev_type = payload_item.get("type")
                if ev_type == "model_info":
                    active_model = payload_item.get("model", active_model)
                    active_provider = payload_item.get("provider", active_provider)
                    yield f"data: {json.dumps({'type': 'status', 'stage': 'reasoning', 'message': f'Model active ({active_provider}: {active_model}) — reasoning through experimental design...'})}\n\n"
                elif ev_type == "reasoning":
                    reasoning_chunks += 1
                    now = time.monotonic()
                    if now - last_status_emit >= 0.6 and not full_text:
                        last_status_emit = now
                        yield f"data: {json.dumps({'type': 'status', 'stage': 'reasoning', 'message': f'OREAL DeepSeek-R1 is reasoning through hypothesis & methodology ({reasoning_chunks} thought tokens)...', 'reasoning_chunks': reasoning_chunks})}\n\n"
                elif ev_type == "content":
                    text_chunk = payload_item.get("text", "")
                    if not full_text:
                        text_chunk = text_chunk.lstrip()
                    if text_chunk:
                        full_text += text_chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'text': text_chunk})}\n\n"

            if not full_text.strip():
                yield f"data: {json.dumps({'type': 'error', 'message': 'The model completed reasoning without producing experimental context text. Please retry with a concise topic or larger context limit.'})}\n\n"
                return

            # 5. Scientific completeness gate: flag missing design sections without blocking.
            design_completeness = check_design_completeness(full_text)
            if design_completeness["found_headings"] < MIN_REQUIRED_HEADINGS:
                print(
                    "[design] Incomplete design output: "
                    f"{design_completeness['found_headings']}/{design_completeness['total_required']} "
                    f"required headings found. Missing: {', '.join(design_completeness['missing'])}"
                )

            # 6. Send completion event (carries the completeness report downstream)
            yield f"data: {json.dumps({'type': 'complete', 'full_text': full_text, 'model': active_model, 'provider': active_provider, 'design_completeness': design_completeness})}\n\n"

            # 7. Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c if c.isalnum() else "_" for c in request.topic)[:50]
            output_file = os.path.join(OUTPUT_DIR, f"design_{safe_topic}_{timestamp}.txt")

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("Experimental Design\n")
                f.write(f"Topic: {request.topic}\n")
                f.write(f"Model: {active_provider}:{active_model}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(
                    "Design completeness: "
                    f"{design_completeness['found_headings']}/{design_completeness['total_required']} "
                    f"(missing: {', '.join(design_completeness['missing']) or 'none'})\n"
                )
                f.write(f"\n{'='*70}\n\n")
                f.write(full_text)

            yield f"data: {json.dumps({'type': 'saved', 'file': output_file})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/run-simulation")
async def run_simulation_endpoint(request: SimulationRequest):
    """
    Run Layer 3 Simulation based on experimental design output from Ollama.
    Returns simulation results with plots and numerical data.
    """
    try:
        # Prepare input for simulation agent
        simulation_input = {
            "topic": request.topic,
            "design": request.design,
            "domain": request.domain,
            "refinement": request.refinement,
        }
        
        # Run simulation
        result = run_simulation(simulation_input)
        
        # Save simulation output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in request.topic)[:50]
        output_file = os.path.join(OUTPUT_DIR, f"simulation_{safe_topic}_{timestamp}.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        
        return {
            "success": True,
            "simulation": result,
            "saved_to": output_file
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@app.post("/api/visualization/generate")
async def generate_visualization_endpoint(request: VisualizationGenerateRequest):
    """
    Generates and validates a declarative 3D scene specification.
    """
    try:
        proc = request.procedure or extract_procedure_from_text("", request.topic, user_domain=request.domain)
        if request.domain and proc.get("domain") in ("general", None, ""):
            proc["domain"] = request.domain
        spec = generate_scene_specification(
            procedure=proc,
            numerical_results=request.numerical_results,
            plot_data=request.plot_data
        )
        return {
            "success": True,
            "visualization_spec": spec
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scene generation failed: {str(e)}")


@app.post("/api/visualization/update")
async def update_visualization_endpoint(request: VisualizationUpdateRequest):
    """
    Updates the experiment when a user changes physical parameters,
    rerunning the deterministic numerical simulation and synchronizing the 3D scene.
    """
    try:
        exp_alias_map = {
            "simple_pendulum": "pendulum",
            "projectile_motion": "projectile",
            "beam_deformation": "beam_analysis",
            "arduino_circuit": "arduino_led",
        }
        normalized_exp_type = exp_alias_map.get(request.experiment_id, request.experiment_id)

        proc = request.current_procedure or {
            "domain": request.domain,
            "experiment_type": normalized_exp_type,
            "hypothesis": f"Updated simulation for {request.experiment_id}",
            "parameters": {}
        }
        # Update parameters with incoming user adjustments
        if "parameters" not in proc:
            proc["parameters"] = {}
        proc["parameters"].update(request.parameters)
        proc["domain"] = request.domain
        proc["experiment_type"] = normalized_exp_type

        # Run authoritative deterministic engine
        raw = route(proc)

        # Format output and generate synchronized 3D specification
        output = format_output(raw, proc)

        return {
            "success": True,
            "simulation": output.dict(),
            "updated_parameters": request.parameters
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scene update failed: {str(e)}")



# ─── Eval Report Endpoints ───────────────────────────────────────────────

EVAL_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


@app.get("/api/eval-reports")
async def list_eval_reports():
    """List all saved evaluation reports (summary list for sidebar)."""
    try:
        os.makedirs(EVAL_OUTPUT_DIR, exist_ok=True)
        reports = []
        for fname in sorted(os.listdir(EVAL_OUTPUT_DIR), reverse=True):
            if fname.startswith("eval_") and fname.endswith(".json"):
                fpath = os.path.join(EVAL_OUTPUT_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    reports.append({
                        "run_id"       : data.get("run_id", fname),
                        "overall_score": data.get("overall_score", 0),
                        "eval_passed"  : data.get("eval_passed", False),
                        "evaluated_at" : data.get("evaluated_at", ""),
                    })
                except Exception:
                    continue
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/eval-reports/{run_id}")
async def get_eval_report(run_id: str):
    """Return the full eval report JSON for a given run_id."""
    try:
        # Sanitise run_id to prevent path traversal
        safe_id = "".join(c for c in run_id if c.isalnum() or c in ("_", "-"))
        fpath = os.path.join(EVAL_OUTPUT_DIR, f"eval_{safe_id}.json")
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail=f"Report not found: {run_id}")
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🚀 Starting Experimental Design Agent API")
    print("   with Simulation Agent (Layer 3)")
    print("="*70)
    print(f"Backend: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")
    print(f"LM Studio: {LMSTUDIO_URL} ({LMSTUDIO_MODEL})")
    print(f"Ollama fallback: {OLLAMA_URL}")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
