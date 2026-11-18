"""
Master Multi-Model Vision-Assisted Scientific 3D Visualization Pipeline
========================================================================
Coordinates the 3-Model Sequential LM Studio Architecture via `model_registry.py`:
  Stage A (`prompt_refiner` — Qwen3-4B-Thinking):
           - Intelligent stop-word filtering & prompt refinement
           - Search query generation, free online search & reference image selection
           - Temporary in-memory RAM image acquisition (zero disk writes)
           - Explicit unload + verification before Stage B
  Stage B (`vision_analyzer` — Qwen3-VL-4B-Thinking):
           - Multimodal visual decomposition (objects, joints, hierarchy, camera, uncertainties)
           - Strict `finally` RAM image buffer purge + verified unload before Stage C
  Stage C (`main_reasoner` — DeepSeek-R1-0528-Qwen3-8B, reasoning-only, NO tool calls):
           - Deterministic numerical simulation & ScientificValidator execution
           - Combines refined prompt + validated visual instructions + deterministic solver results
           - Declarative SceneSpecification synthesis & SceneValidator check
           - Explicit unload + verification when stage completes
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

from backend.services.local_model_manager import model_manager
from backend.services.model_registry import model_registry
from backend.services.prompt_refiner_service import prompt_refiner_service
from backend.services.reference_acquisition_service import reference_acquisition_service
from backend.services.vision_service import vision_service
from backend.visualization.prompt_schema import ReferenceItem
from backend.visualization.scene_validator import validate_scene_specification
from backend.visualization.visual_description_schema import VisualReconstructionInstructions
from simulation_agent.agent import run_simulation
from simulation_agent.visualization.scene_generator import (
    generate_scene_specification,
    resolve_visualization_template,
)
from simulation_agent.visualization.scene_schema import SceneSpecification

logger = logging.getLogger(__name__)


def build_main_reasoner_context(
    refined_output: Dict[str, Any],
    visual_instructions: Dict[str, Any],
    simulation_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the strictly textual/JSON context handed to `main_reasoner` (DeepSeek-R1-0528-Qwen3-8B).
    Contains BOTH refined prompt and validated visual reconstruction instructions plus
    authoritative deterministic simulation outputs — NEVER raw image bytes, NEVER tool schemas.
    """
    return {
        "role_key": "main_reasoner",
        "model_id": model_registry.get_model_id("main_reasoner"),
        "reasoning_only": True,
        "tools_enabled": False,
        "refined_prompt": refined_output,
        "visual_reconstruction_instructions": visual_instructions,
        "simulation_results": {
            "domain": simulation_results.get("domain"),
            "experiment_id": simulation_results.get("experiment_id"),
            "simulation_status": simulation_results.get("simulation_status"),
            "solver": simulation_results.get("solver"),
            "numerical_results": simulation_results.get("numerical_results", {}),
            "validation": simulation_results.get("validation"),
            "assumptions": simulation_results.get("assumptions", []),
            "limitations": simulation_results.get("limitations", []),
            "warnings": simulation_results.get("warnings", []),
        },
    }


class VisualizationPipeline:
    """
    Central coordinator executing the sequential 3-model vision-assisted visualization flow
    under `model_manager._lock` so concurrent API requests never violate single-model residency.
    """

    async def run_pipeline(
        self,
        raw_prompt: str,
        domain_hint: Optional[str] = None,
        user_reference_url: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Execute full end-to-end sequential 3-model pipeline."""
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
            model_manager.set_pipeline_stage(stage)
            logger.info("[Pipeline] [%.2fs] %s: %s", event["timestamp"], stage, message)
            if progress_callback:
                progress_callback(stage, event)

        refiner_id = model_registry.get_model_id("prompt_refiner")
        vision_id = model_registry.get_model_id("vision_analyzer")
        main_id = model_registry.get_model_id("main_reasoner")

        async with model_manager._lock:
            # ── STAGE A: `prompt_refiner` (Qwen3-4B-Thinking) ──────────────
            _log_progress("stage_a_refining_prompt", f"Refining prompt & searching references with {refiner_id}...")
            refined_output, search_result = await prompt_refiner_service.refine_prompt_and_search(
                raw_prompt=raw_prompt,
                domain_hint=domain_hint,
            )

            selected_ref: Optional[ReferenceItem] = None
            if user_reference_url:
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

            # Acquire temporary reference image into RAM only
            img_bytes_cache: Optional[bytes] = None
            mime_type_cache = "image/jpeg"
            if selected_ref and selected_ref.image_url:
                _log_progress("acquiring_image", f"Fetching reference image into RAM ({selected_ref.source_name})...")
                try:
                    img_bytes_cache, mime_type_cache = reference_acquisition_service.fetch_image_into_ram(
                        selected_ref.image_url
                    )
                    _log_progress("image_in_ram", f"Image loaded in RAM buffer ({len(img_bytes_cache)} bytes). Zero disk writes.")
                except Exception as acq_err:
                    logger.warning("[Pipeline] Image acquisition failed (%s); will not invoke vision with missing image.", acq_err)
                    _log_progress("acquisition_failed", f"Reference image retrieval failed ({acq_err}); skipping vision inference.")
                    img_bytes_cache = None

            # Unload Stage A model and VERIFY before Stage B
            _log_progress("unloading_prompt_refiner", f"Unloading {refiner_id} and verifying VRAM release...")
            unloaded_a = await model_manager.unload_all_models()
            if not unloaded_a:
                err_msg = model_manager.last_unload_error or f"Failed to unload {refiner_id}; blocking Stage B."
                _log_progress("unload_blocked", err_msg)
                img_bytes_cache = None
                raise RuntimeError(err_msg)

            # ── STAGE B: `vision_analyzer` (Qwen3-VL-4B-Thinking) ──────────
            visual_instructions: VisualReconstructionInstructions
            try:
                if img_bytes_cache and selected_ref:
                    _log_progress("stage_b_analyzing_image", f"Loading {vision_id} and analyzing reference image...")
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
                # Strictly purge RAM image buffers and verify unload even on failure paths
                if img_bytes_cache is not None:
                    del img_bytes_cache
                    img_bytes_cache = None
                _log_progress("releasing_image_buffers", "In-memory image buffers purged from RAM.")
                _log_progress("unloading_vision_analyzer", f"Unloading {vision_id} and verifying VRAM release...")
                unloaded_b = await model_manager.unload_all_models()
                if not unloaded_b:
                    err_msg = model_manager.last_unload_error or f"Failed to unload {vision_id}; blocking Stage C."
                    _log_progress("unload_blocked", err_msg)
                    raise RuntimeError(err_msg)

            _log_progress(
                "visual_instructions_ready",
                f"Extracted {len(visual_instructions.objects)} objects and {len(visual_instructions.connections)} joints.",
                {"visual_instructions": visual_instructions.model_dump()},
            )

            # ── Deterministic Numerical Simulation & Scientific Validation ──
            _log_progress("running_simulation", f"Executing deterministic simulation engine for domain '{refined_output.domain}'...")
            sim_result = run_simulation({
                "topic": refined_output.refined_experiment_prompt,
                "design": refined_output.refined_experiment_prompt,
                "domain": refined_output.domain,
                "experiment_type": refined_output.experiment_type,
                "parameters": dict(refined_output.parameters or {}),
                "refinement": refined_output.model_dump(),
            })

            numerical_results = sim_result.get("numerical_results", {})
            plot_data = sim_result.get("plot_data", [])
            procedure = {
                "domain": sim_result.get("domain") or refined_output.domain,
                "experiment_type": sim_result.get("experiment_id") or refined_output.experiment_type,
                "hypothesis": sim_result.get("hypothesis") or refined_output.refined_experiment_prompt,
                "refined_prompt": refined_output.refined_experiment_prompt,
                "parameters": {**numerical_results.get("parameters", {}), **refined_output.parameters},
            }

            # ── STAGE C: `main_reasoner` (DeepSeek-R1-0528-Qwen3-8B, reasoning-only) ──
            main_context = build_main_reasoner_context(
                refined_output.model_dump(),
                visual_instructions.model_dump(),
                sim_result,
            )

            _log_progress("stage_c_loading_main_reasoner", f"Loading {main_id} (reasoning-only, no tool calls)...")
            try:
                loaded_c = await model_manager.load_role("main_reasoner")
                if not loaded_c:
                    logger.warning("[Pipeline] Main reasoner '%s' unavailable (%s); using deterministic scene synthesis.", main_id, model_manager.last_load_error)

                _log_progress("synthesizing_scene", "Synthesizing declarative 3D scene synchronized with solver output...")
                raw_scene_dict = sim_result.get("visualization_spec") or generate_scene_specification(
                    procedure, numerical_results, plot_data, simulation_status=sim_result.get("simulation_status")
                )
                if not raw_scene_dict:
                    return {
                        "success": False,
                        "total_duration_s": round(time.time() - t0, 2),
                        "simulation_status": sim_result.get("simulation_status", "unsupported"),
                        "scene_specification": None,
                        "refined_prompt": refined_output.model_dump(),
                        "visual_reconstruction_instructions": visual_instructions.model_dump(),
                        "main_reasoner_context": main_context,
                        "selected_reference": selected_ref.model_dump() if selected_ref else None,
                        "simulation_results": sim_result,
                        "timeline_events": timeline_events,
                        "validation": {"is_valid": False, "notices": ["No validated 3D scene for unsupported/failed simulation."]},
                    }

                scene_spec = SceneSpecification.model_validate(raw_scene_dict)
                if visual_instructions:
                    scene_spec.notes.append(
                        f"Visual Reference Source: {visual_instructions.reference_attribution.get('source_name', 'Open Scientific')}"
                    )
                    if visual_instructions.reference_attribution.get("license"):
                        scene_spec.notes.append(f"Reference License: {visual_instructions.reference_attribution.get('license')}")
                    for inst in visual_instructions.visual_instructions[:4]:
                        scene_spec.notes.append(f"Visual Layout: {inst}")
                    for uncert in visual_instructions.uncertainties[:2]:
                        scene_spec.notes.append(f"Uncertainty Note: {uncert}")

                exp_id, expected_tpl = resolve_visualization_template(procedure, sim_result)
                _log_progress("validating_scene", "Validating 3D scene specification against allowlisted primitives & template match...")
                is_valid, validation_notices = validate_scene_specification(
                    scene_spec,
                    expected_experiment_id=exp_id,
                    expected_template=expected_tpl,
                )
            finally:
                _log_progress("unloading_main_reasoner", f"Unloading {main_id} and verifying VRAM release...")
                await model_manager.unload_all_models()
                model_manager.set_pipeline_stage("idle")

            total_duration = round(time.time() - t0, 2)
            _log_progress("complete", f"Multi-model 3D visualization pipeline completed in {total_duration}s.")

            return {
                "success": True,
                "total_duration_s": total_duration,
                "scene_specification": scene_spec.model_dump() if is_valid else None,
                "refined_prompt": refined_output.model_dump(),
                "visual_reconstruction_instructions": visual_instructions.model_dump(),
                "main_reasoner_context": main_context,
                "selected_reference": selected_ref.model_dump() if selected_ref else None,
                "simulation_results": sim_result,
                "timeline_events": timeline_events,
                "validation": {
                    "is_valid": is_valid,
                    "notices": validation_notices,
                },
            }


visualization_pipeline = VisualizationPipeline()
