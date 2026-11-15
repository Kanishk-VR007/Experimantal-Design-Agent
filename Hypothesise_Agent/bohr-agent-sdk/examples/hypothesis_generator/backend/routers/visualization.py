"""
FastAPI Router for Multi-Model Scientific 3D Visualization
===========================================================
Exposes REST and SSE endpoints for:
  - Step-by-step pipeline stages (refine-prompt, search-references, analyze-reference, generate-scene)
  - Full end-to-end pipeline execution with real-time status streaming
  - Real-time model residency telemetry & GPU scheduler status
"""

import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.local_model_manager import model_manager
from backend.services.prompt_refiner_service import prompt_refiner_service
from backend.services.free_web_search_service import free_search_service, CURATED_REFERENCE_CATALOGUE
from backend.services.reference_acquisition_service import reference_acquisition_service
from backend.services.vision_service import vision_service
from backend.visualization.visualization_pipeline import visualization_pipeline
from backend.visualization.prompt_schema import RefinedPromptOutput, ReferenceItem
from backend.visualization.scene_validator import validate_scene_specification
from simulation_agent.visualization.scene_schema import SceneSpecification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


# ── Request / Response Models ──

class PipelineRunRequest(BaseModel):
    topic: str = Field(..., description="Natural language experiment request")
    domain: Optional[str] = Field(default=None, description="Optional domain hint")
    user_reference_url: Optional[str] = Field(default=None, description="Optional user-supplied reference image/diagram URL")


class RefinePromptRequest(BaseModel):
    topic: str
    domain: Optional[str] = None


class SearchReferencesRequest(BaseModel):
    domain: str
    search_queries: List[str] = Field(default_factory=list)
    filtered_search_terms: List[str] = Field(default_factory=list)


class AnalyzeReferenceRequest(BaseModel):
    refined_prompt: Dict[str, Any]
    reference: Dict[str, Any]


class GenerateSceneRequest(BaseModel):
    refined_prompt: Dict[str, Any]
    visual_instructions: Dict[str, Any]
    simulation_results: Optional[Dict[str, Any]] = None


# ── Endpoints ──

@router.get("/model-status")
async def get_model_status():
    """Inspect active local model residency in LM Studio and scheduler telemetry."""
    status = model_manager.query_models_status()
    telemetry = model_manager.get_telemetry()
    return {
        "status": "online" if status["server_online"] else "offline",
        "loaded_instances": status["loaded_instances"],
        "available_models": status["available_models"],
        "telemetry": telemetry,
    }


@router.get("/reference-sources")
async def get_reference_sources():
    """Catalogue of supported open-access scientific diagram repositories."""
    return {
        "providers": [
            {"name": "Wikimedia Commons Open API", "type": "live_search", "license": "CC-BY-SA / Public Domain", "free": True},
            {"name": "SearXNG Meta-Search", "type": "configurable_instance", "license": "Open Web", "free": True},
            {"name": "Curated Open Scientific Catalogue", "type": "deterministic", "license": "MIT / CC / Public Domain", "free": True},
        ],
        "curated_domains": list(CURATED_REFERENCE_CATALOGUE.keys()),
    }


@router.post("/refine-prompt")
async def refine_prompt(req: RefinePromptRequest):
    """Stage 1: Qwen 4B Thinking prompt refinement and search query generation."""
    try:
        refined, search_result = await prompt_refiner_service.refine_prompt_and_search(
            raw_prompt=req.topic,
            domain_hint=req.domain,
        )
        return {
            "refined_prompt": refined.model_dump(),
            "search_result": search_result.model_dump(),
        }
    except Exception as e:
        logger.error("[Router] Refine prompt error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-references")
async def search_references(req: SearchReferencesRequest):
    """Execute free multi-source visual reference search."""
    try:
        items = free_search_service.find_references(
            domain=req.domain,
            search_queries=req.search_queries,
            filtered_search_terms=req.filtered_search_terms,
        )
        return {
            "domain": req.domain,
            "count": len(items),
            "references": [i.model_dump() for i in items],
        }
    except Exception as e:
        logger.error("[Router] Search references error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline-run")
async def run_pipeline_sync(req: PipelineRunRequest):
    """Execute complete 3-Model sequential visualization pipeline (Synchronous JSON)."""
    try:
        result = await visualization_pipeline.run_pipeline(
            raw_prompt=req.topic,
            domain_hint=req.domain,
            user_reference_url=req.user_reference_url,
        )
        return result
    except Exception as e:
        logger.error("[Router] Pipeline run error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline-stream")
async def run_pipeline_stream(req: PipelineRunRequest):
    """
    Execute complete 3-Model pipeline with real-time SSE progress events.
    Permits frontend to animate progress indicators as models switch in LM Studio.
    """
    import asyncio
    queue: asyncio.Queue = asyncio.Queue()

    def _on_progress(stage: str, event: Dict[str, Any]):
        queue.put_nowait(("progress", event))

    async def event_generator():
        pipeline_task = asyncio.create_task(
            visualization_pipeline.run_pipeline(
                raw_prompt=req.topic,
                domain_hint=req.domain,
                user_reference_url=req.user_reference_url,
                progress_callback=_on_progress,
            )
        )

        while not pipeline_task.done():
            try:
                kind, data = await asyncio.wait_for(queue.get(), timeout=0.4)
                yield f"data: {json.dumps({'type': kind, **data})}\n\n"
            except asyncio.TimeoutError:
                continue

        # Drain any remaining progress events
        while not queue.empty():
            kind, data = queue.get_nowait()
            yield f"data: {json.dumps({'type': kind, **data})}\n\n"

        try:
            final_result = await pipeline_task
            yield f"data: {json.dumps({'type': 'complete', 'result': final_result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

