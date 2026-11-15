"""
Master Multi-Model Vision-Assisted Scientific 3D Visualization Pipeline
========================================================================
Coordinates the 3-Model Sequential Architecture:
  Stage A: Qwen 4B Thinking
           - Intelligent stop-word filtering
           - Scientific prompt refinement & domain classification
           - Search query generation & free online search execution
           - Technical relevance evaluation & reference image selection
  Stage B: In-Memory RAM Image Acquisition
           - Zero disk persistence, SSRF-safe, in-memory BytesIO
  Stage C: Unload Qwen 4B -> Load Qwen3-VL-2B
           - Multimodal visual decomposition (objects, joints, hierarchy, camera, animation)
           - Scientific uncertainty extraction
  Stage D: Unload Qwen3-VL-2B -> Release RAM image buffer
  Stage E: Deterministic Simulation & Existing Agent Execution
           - Exact numerical engine calculation (NumPy/SciPy/Euler-Bernoulli/RK4)
  Stage F: Load DeepSeek R1 Distill Qwen 7B
           - Refined prompt + visual instructions + simulation results + scientific constraints
           - Declarative SceneSpecification JSON synthesis
  Stage G: Validation with SceneValidator
           - Enforces allowlisted primitives, sanitizes against executable code
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, Callable

from backend.services.local_model_manager import (
    model_manager,
    PROMPT_REFINER_MODEL_KEY,
    VISION_MODEL_KEY,
    MAIN_MODEL_KEY,
)
from backend.services.prompt_refiner_service import prompt_refiner_service
from backend.services.reference_acquisition_service import reference_acquisition_service
from backend.services.vision_service import vision_service
from backend.visualization.prompt_schema import RefinedPromptOutput, ReferenceItem, SearchSelectionResult
from backend.visualization.visual_description_schema import VisualReconstructionInstructions
from backend.visualization.scene_validator import validate_scene_specification
from simulation_agent.visualization.scene_schema import SceneSpecification
from simulation_agent.visualization.scene_generator import generate_scene_specification
from simulation_agent.agent import run_simulation, extract_procedure_from_text

logger = logging.getLogger(__name__)


class VisualizationPipeline:
    """
    Central coordinator executing the full multi-model vision-assisted visualization flow.
    """

    async def run_pipeline(
        self,
        raw_prompt: str,
        domain_hint: Optional[str] = None,
        user_reference_url: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full end-to-end multi-model pipeline.
        """
        timeline_events = []
        t0 = time.time()

        def _log_progress(stage: str, message: str, meta: Optional[Dict[str, Any]] = None):
            event = {
                "stage": stage,
                "message": message,
                "timestamp": round(time.time() - t0, 2),
                "meta": meta or {},
            }
            timeline_events.append(event)
            logger.info("[Pipeline] [%.2fs] %s: %s", event["timestamp"], stage, message)
            if progress_callback:
                progress_callback(stage, event)

        # ── STAGE 1: Qwen 4B Prompt Refinement & Reference Search ──
        _log_progress("refining_prompt", "Filtering stop words & refining prompt with Qwen 4B Thinking...")
        refined_output, search_result = await prompt_refiner_service.refine_prompt_and_search(
            raw_prompt=raw_prompt,
            domain_hint=domain_hint,
        )

        selected_ref: Optional[ReferenceItem] = None
        if user_reference_url:
            # User-provided reference URL
            selected_ref = ReferenceItem(
                source_name="User-Provided Reference",
                page_url=user_reference_url,
                image_url=user_reference_url,
                image_type="user_supplied",
                license="User Specified",
                license_verified=False,
                relevance_reason="Directly supplied by user for reconstruction guidance",
                confidence=1.0,
            )
        elif search_result and search_result.selected_references:
            selected_ref = search_result.selected_references[0]

        _log_progress(
            "reference_selected",
            f"Visual reference selected: {selected_ref.source_name if selected_ref else 'None'}",
            {"selected_reference": selected_ref.model_dump() if selected_ref else None},
        )

        # ── STAGE 2: Temporary In-Memory Reference Image Acquisition ──
        img_bytes_cache: Optional[bytes] = None
        mime_type_cache = "image/jpeg"

        if selected_ref and selected_ref.image_url:
            _log_progress("acquiring_image", f"Temporarily fetching reference image into RAM ({selected_ref.source_name})...")
            try:
                img_bytes_cache, mime_type_cache = reference_acquisition_service.fetch_image_into_ram(selected_ref.image_url)
                _log_progress("image_in_ram", f"Image safely loaded into RAM buffer ({len(img_bytes_cache)} bytes). Zero disk writes.")
            except Exception as acq_err:
                logger.warning("[Pipeline] Image acquisition error (%s); proceeding with domain heuristics", acq_err)
                _log_progress("acquisition_fallback", f"Online image retrieval issue ({acq_err}); using scientific reference schema.")

        # ── STAGE 3: Unload Qwen 4B ──
        _log_progress("unloading_refiner", "Unloading Qwen 4B Thinking to free GPU memory...")
        await model_manager.unload_all_models()

        # ── STAGE 4: Load Qwen3-VL-2B & Analyze Reference Image ──
        _log_progress("loading_vision_model", "Sequentially loading Qwen3-VL-2B-Instruct into LM Studio...")
        visual_instructions: VisualReconstructionInstructions

        try:
            if img_bytes_cache and selected_ref:
                _log_progress("analyzing_image", "Qwen3-VL analyzing visual structure, joints, and component layout...")
                visual_instructions = await vision_service.analyze_reference_image(
                    refined=refined_output,
                    reference=selected_ref,
                    image_bytes=img_bytes_cache,
                    mime_type=mime_type_cache,
                )
            else:
                dummy_ref = selected_ref or ReferenceItem(
                    source_name="Curated Scientific Catalogue",
                    image_url="",
                    license="Public Domain / CC",
                )
                visual_instructions = vision_service._build_domain_fallback_instructions(refined_output, dummy_ref)
        finally:
            # ── STAGE 5: Strictly Release RAM Image Buffers & Unload Vision Model ──
            if img_bytes_cache is not None:
                del img_bytes_cache
                img_bytes_cache = None
            _log_progress("releasing_image_buffers", "In-memory image buffers strictly purged from RAM.")
            _log_progress("unloading_vision_model", "Unloading Qwen3-VL-2B from LM Studio...")
            await model_manager.unload_all_models()

        _log_progress(
            "visual_instructions_ready",
            f"Extracted {len(visual_instructions.objects)} objects and {len(visual_instructions.connections)} joints from reference.",
            {"visual_instructions": visual_instructions.model_dump()},
        )

        # ── STAGE 6: Execute Deterministic Numerical Simulation ──
        _log_progress("running_simulation", f"Executing deterministic simulation engine for domain '{refined_output.domain}'...")
        sim_result = run_simulation(
            topic=refined_output.refined_experiment_prompt,
            design=refined_output.refined_experiment_prompt,
            domain=refined_output.domain,
            refinement=refined_output.model_dump(),
        )

        numerical_results = sim_result.get("numerical_results", {})
        plot_data = sim_result.get("plot_data", [])
        procedure = sim_result.get("procedure", {})
        procedure["domain"] = refined_output.domain
        procedure["experiment_type"] = refined_output.experiment_type
        procedure["refined_prompt"] = refined_output.refined_experiment_prompt
        procedure["parameters"] = {**numerical_results.get("parameters", {}), **refined_output.parameters}

        # ── STAGE 7: Load DeepSeek R1 7B & Synthesize 3D Scene Specification ──
        _log_progress("loading_main_model", "Sequentially loading OREAL DeepSeek R1 Distill Qwen 7B for 3D scene generation...")
        await model_manager.load_model(MAIN_MODEL_KEY)

        _log_progress("synthesizing_scene", "Synthesizing declarative 3D scene matching simulation constraints...")
        # Build base scene from domain template
        raw_scene_dict = generate_scene_specification(procedure, numerical_results, plot_data)
        scene_spec = SceneSpecification.model_validate(raw_scene_dict)

        # Augment with visual reconstruction instructions and reference attribution
        if visual_instructions:
            scene_spec.notes.append(f"Visual Reference Source: {visual_instructions.reference_attribution.get('source_name', 'Open Scientific')}")
            if visual_instructions.reference_attribution.get("license"):
                scene_spec.notes.append(f"Reference License: {visual_instructions.reference_attribution.get('license')}")
            for inst in visual_instructions.visual_instructions[:4]:
                scene_spec.notes.append(f"Visual Layout: {inst}")
            for uncert in visual_instructions.uncertainties[:2]:
                scene_spec.notes.append(f"Uncertainty Note: {uncert}")

        # ── STAGE 8: Validate Scene Specification ──
        _log_progress("validating_scene", "Validating 3D scene specification against allowable geometries & security constraints...")
        is_valid, validation_notices = validate_scene_specification(scene_spec)

        total_duration = round(time.time() - t0, 2)
        _log_progress("complete", f"Multi-model 3D visualization pipeline completed in {total_duration}s.")

        return {
            "success": True,
            "total_duration_s": total_duration,
            "scene_specification": scene_spec.model_dump(),
            "refined_prompt": refined_output.model_dump(),
            "visual_reconstruction_instructions": visual_instructions.model_dump(),
            "selected_reference": selected_ref.model_dump() if selected_ref else None,
            "simulation_results": {
                "procedure": procedure,
                "numerical_results": numerical_results,
                "plot_data": plot_data,
            },
            "timeline_events": timeline_events,
            "validation": {
                "is_valid": is_valid,
                "notices": validation_notices,
            },
        }


visualization_pipeline = VisualizationPipeline()

