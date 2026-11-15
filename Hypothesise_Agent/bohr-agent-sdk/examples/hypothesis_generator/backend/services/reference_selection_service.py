"""
Qwen 4B Controlled Reference Selection Service
===============================================
Presents candidate visual search results back to Qwen 4B Thinking.
Qwen evaluates technical accuracy, relevance, and fidelity to experimental apparatus:
  - Prioritizes: Engineering apparatus, technical drawings, 3D views, circuit/structural schematics.
  - Rejects: Unrelated stock photos, marketing images, decorative artwork.
  - Selects 1 to 3 top references with structured justification.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

from backend.visualization.prompt_schema import ReferenceItem, SearchSelectionResult, RefinedPromptOutput

logger = logging.getLogger(__name__)

LM_STUDIO_OPENAI_BASE = os.getenv("LM_STUDIO_OPENAI_BASE_URL", "http://localhost:1234/v1").rstrip("/")
PROMPT_REFINER_MODEL_KEY = os.getenv("PROMPT_REFINER_MODEL", "qwen/qwen3-4b-thinking-2507").strip()


def select_best_reference_with_qwen(
    refined: RefinedPromptOutput,
    candidates: List[ReferenceItem],
    timeout: int = 30,
) -> SearchSelectionResult:
    """
    Have Qwen 4B select the most scientifically relevant reference visualization from candidates.
    """
    if not candidates:
        logger.info("[ReferenceSelection] No search candidates available. Using empty fallback.")
        return SearchSelectionResult(
            search_performed=True,
            refined_experiment_prompt=refined.refined_experiment_prompt,
            selected_references=[],
            search_limitations=["No online references discovered for query."],
            fallback_required=True,
        )

    if len(candidates) == 1:
        # Sole candidate
        return SearchSelectionResult(
            search_performed=True,
            refined_experiment_prompt=refined.refined_experiment_prompt,
            selected_references=[candidates[0]],
            search_limitations=[],
            fallback_required=False,
        )

    # Format candidates for Qwen
    cand_summaries = []
    for idx, c in enumerate(candidates):
        cand_summaries.append({
            "index": idx,
            "title": c.relevance_reason or c.source_name,
            "source": c.source_name,
            "image_type": c.image_type,
            "url": c.image_url,
            "license": c.license,
        })

    system_prompt = (
        "You are an expert Scientific Visual Reference Evaluator. "
        "Given an experiment specification and candidate diagrams/images, select the SINGLE BEST reference "
        "that accurately depicts the physical apparatus, geometry, and component layout. "
        "Prioritize technical diagrams, schematics, and mechanical assemblies. Reject decorative graphics. "
        "Output strictly valid JSON with keys: 'selected_index' (integer), 'relevance_rationale' (string), 'confidence' (float 0.0-1.0)."
    )

    user_prompt = (
        f"Experiment Domain: {refined.domain}\n"
        f"Experiment Type: {refined.experiment_type}\n"
        f"Refined Prompt: {refined.refined_experiment_prompt}\n"
        f"Key Apparatus: {', '.join(refined.apparatus)}\n"
        f"Visual Requirements: {', '.join(refined.visual_reference_requirements)}\n\n"
        f"Candidate Visual References:\n{json.dumps(cand_summaries, indent=2)}\n\n"
        "Select the most appropriate technical reference now."
    )

    payload = {
        "model": PROMPT_REFINER_MODEL_KEY,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": '{"selected_index": '},
        ],
        "temperature": 0.1,
        "max_tokens": 250,
        "stream": True,
        "stop": ["\n\n", "}\n\n"],
    }

    try:
        url = f"{LM_STUDIO_OPENAI_BASE}/chat/completions"
        resp = requests.post(url, json=payload, stream=True, timeout=timeout)
        if resp.status_code == 200:
            content_parts = []
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        c = chunk["choices"][0]["delta"].get("content")
                        if c:
                            content_parts.append(c)
                    except Exception:
                        pass

            raw = "".join(content_parts).strip()
            # Parse prefix reconstructed JSON
            full_json = '{"selected_index": ' + raw
            parsed = None
            try:
                parsed = json.loads(full_json)
            except Exception:
                # Try raw decode
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(full_json)
                except Exception:
                    pass

            if parsed and isinstance(parsed, dict) and "selected_index" in parsed:
                sel_idx = int(parsed["selected_index"])
                if 0 <= sel_idx < len(candidates):
                    chosen = candidates[sel_idx]
                    chosen.relevance_reason = parsed.get("relevance_rationale") or chosen.relevance_reason
                    chosen.confidence = float(parsed.get("confidence", chosen.confidence))
                    logger.info("[ReferenceSelection] Qwen 4B selected candidate #%d: %s", sel_idx, chosen.image_url)
                    return SearchSelectionResult(
                        search_performed=True,
                        refined_experiment_prompt=refined.refined_experiment_prompt,
                        selected_references=[chosen],
                        search_limitations=[],
                        fallback_required=False,
                    )
    except Exception as e:
        logger.warning("[ReferenceSelection] Qwen selection call failed (%s); using top candidate", e)

    # Fallback to top candidate
    return SearchSelectionResult(
        search_performed=True,
        refined_experiment_prompt=refined.refined_experiment_prompt,
        selected_references=[candidates[0]],
        search_limitations=[],
        fallback_required=False,
    )

