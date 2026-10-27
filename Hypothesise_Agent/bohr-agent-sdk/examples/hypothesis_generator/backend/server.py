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
import json
import asyncio
import requests
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Add simulation agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulation_agent.agent import run_simulation

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
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


class SimulationRequest(BaseModel):
    topic: str
    design: str
    domain: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    ollama_available: bool
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
    """Check if Ollama is running and get available models"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "unknown") for m in data.get("models", [])]
            return {
                "available": True,
                "models": models
            }
    except:
        pass
    
    return {
        "available": False,
        "models": []
    }


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
    """Check API and Ollama health"""
    ollama_status = check_ollama()
    
    return {
        "status": "healthy" if ollama_status["available"] else "ollama_unavailable",
        "ollama_available": ollama_status["available"],
        "models": ollama_status["models"]
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
    """Generate experimental design with streaming response"""
    
    # Get papers
    if request.use_mock_data:
        papers = MOCK_PAPERS[:request.max_papers]
    else:
        papers = fetch_papers(request.topic[:200], request.max_papers)
        if not papers:
            papers = MOCK_PAPERS[:request.max_papers]
    
    # Create prompt — keep paper summaries short to avoid context overflow
    paper_summaries = []
    for p in papers[:3]:   # max 3 papers
        title   = str(p.get("title",   ""))[:120]
        authors = str(p.get("authors", ""))[:60]
        summary = str(p.get("abstract") or p.get("summary", ""))[:200]
        paper_summaries.append(f"- {title} ({authors}): {summary}")
    papers_text = "\n".join(paper_summaries) if paper_summaries else "No papers found."

    prompt = f"""Design an experiment for: "{request.topic}"

Related research:
{papers_text}

Provide a concise experimental design (250-350 words) with:

## 1. HYPOTHESIS
Clear, testable hypothesis.

## 2. VARIABLES
- Independent, Dependent, Control

## 3. METHODOLOGY
4-5 step procedure

## 4. EXPECTED OUTCOMES
Predicted results

## 5. LIMITATIONS
Key limitations

Be specific and scientific."""

    async def event_generator():
        """Generate Server-Sent Events stream"""
        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting generation...'})}\n\n"
            
            # Send papers info
            yield f"data: {json.dumps({'type': 'papers', 'papers': papers, 'count': len(papers)})}\n\n"
            
            # Call Ollama with streaming
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 600,   # cap tokens to avoid timeout
                    "num_ctx": 2048,
                }
            }
            
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                stream=True,
                timeout=300
            )
            
            if response.status_code != 200:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Ollama error: {response.status_code}'})}\n\n"
                return
            
            full_text = ""
            
            # Stream chunks
            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line)
                        text_chunk = chunk_data.get("response", "")
                        full_text += text_chunk
                        
                        # Send chunk to frontend
                        yield f"data: {json.dumps({'type': 'chunk', 'text': text_chunk})}\n\n"
                        
                        if chunk_data.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'full_text': full_text})}\n\n"
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c if c.isalnum() else "_" for c in request.topic)[:50]
            output_file = os.path.join(OUTPUT_DIR, f"design_{safe_topic}_{timestamp}.txt")
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Experimental Design\n")
                f.write(f"Topic: {request.topic}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
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
            "domain": request.domain
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
    print(f"Ollama: {OLLAMA_URL}")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
