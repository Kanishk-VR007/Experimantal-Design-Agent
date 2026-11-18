"""
Qwen 4B Thinking Prompt Refiner & Reference Search Service
==========================================================
Executes Stage 1 of the Multi-Model Pipeline:
  1. Intelligent Stop-Word Filtering (preserves scientific terms, units, negations, operators).
  2. Qwen 4B Prompt Refinement & Domain Identification.
  3. Search Query Generation.
  4. Controlled Free Web Search Execution.
  5. Qwen 4B Reference Image Evaluation & Selection.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import requests

from backend.visualization.prompt_schema import RefinedPromptOutput, DomainLiteral
from backend.services.free_web_search_service import free_search_service
from backend.services.reference_selection_service import select_best_reference_with_qwen
from backend.services.local_model_manager import model_manager
from backend.services.model_registry import model_registry

logger = logging.getLogger(__name__)

LM_STUDIO_OPENAI_BASE = os.getenv("LM_STUDIO_OPENAI_BASE_URL", "http://localhost:1234/v1").rstrip("/")

# Standard English stop words EXCLUDING scientific operators, units, negations, constraints
# (Intentionally KEPT: not, no, nor, without, unless, only, before, after, between, per, vs, if, then, when, while, above, below)
STOP_WORDS_DISCARD = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "must", "can", "could", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our", "us",
    "you", "your", "i", "me", "my", "he", "she", "him", "her", "his", "who",
    "whom", "which", "what", "whose", "where", "why", "how", "all", "any",
    "both", "each", "few", "many", "most", "other", "some", "such",
    "own", "so", "than", "too", "very", "just", "also", "even", "here", "there",
    "about", "into", "through", "during", "up", "down", "out", "off", "again",
    "further", "once", "etc", "via", "please", "kindly", "show", "tell",
    "simulate", "want", "like", "see",
})

NOISE_PATTERNS = [
    r"https?://\S+",
    r"<[^>]+>",
    r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]",
    r"\b(?:et\s+al\.?|fig\.?|eq\.?|copyright)\b",
]


def extract_scientific_tokens(text: str) -> List[str]:
    """Tokenize preserving numbers, units (e.g. 50Nm, 10kN, O(n^2)), formulas, symbols."""
    cleaned = text
    for pat in NOISE_PATTERNS:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Match alphanumeric terms with units/subscripts or mathematical/chemical symbols
    pattern = r"[A-Za-z0-9]+(?:[._/\-\+\^][A-Za-z0-9]+)*|[=<>±×÷√πθαωμΩ°%]+"
    return re.findall(pattern, cleaned)


def intelligent_stop_word_filter(raw_text: str) -> Tuple[str, List[str]]:
    """
    Filter conversational fluff while strictly preserving scientific operators,
    units, numbers, constraints, and negations.
    Returns: (filtered_text_string, list_of_filtered_search_terms)
    """
    tokens = extract_scientific_tokens(raw_text)
    filtered_tokens = []
    for tok in tokens:
        low = tok.lower()
        if low not in STOP_WORDS_DISCARD or any(c.isdigit() for c in tok) or any(c in "=<>+-/*^%°" for c in tok):
            filtered_tokens.append(tok)

    filtered_text = " ".join(filtered_tokens)
    # Search terms: high signal keywords (deduplicated preserving order)
    seen = set()
    search_terms = []
    for t in filtered_tokens:
        low = t.lower()
        if low not in seen and len(t) > 1:
            seen.add(low)
            search_terms.append(t)

    return filtered_text, search_terms[:8]


class PromptRefinerService:
    """
    Qwen 4B Thinking Prompt Refinement & Search Control Service.
    """

    async def refine_prompt_and_search(
        self,
        raw_prompt: str,
        domain_hint: Optional[str] = None,
        timeout: int = 40,
    ) -> Tuple[RefinedPromptOutput, Any]:
        """
        Full Stage 1 Execution:
          1. Filter stop words intelligently.
          2. Sequential model load: Qwen 4B.
          3. Generate structured refinement JSON.
          4. Execute free online reference search.
          5. Evaluate and select reference image with Qwen 4B.
          6. Returns (RefinedPromptOutput, SearchSelectionResult).
        """
        filtered_text, search_terms = intelligent_stop_word_filter(raw_prompt)

        # Ensure Qwen3-4B-Thinking (`prompt_refiner`) is active in LM Studio via model_registry
        refiner_model_id = model_registry.get_model_id("prompt_refiner")
        await model_manager.load_role("prompt_refiner")

        system_msg = (
            "You are a Senior Scientific Prompt Refinement & Experimental Apparatus Identification Agent. "
            "Given a raw experiment request and stop-word filtered scientific tokens: "
            "1. Identify the domain (physics, mechanical_engineering, civil_engineering, electronics, computer_science, chemistry, biology, general). "
            "2. Identify experiment type (concise snake_case). "
            "3. Generate a precise, publication-grade natural language 'refined_experiment_prompt' describing the exact apparatus and physical behavior. "
            "4. Extract apparatus list, key numeric parameters, targeted web search queries, and visual reference requirements. "
            "Output strictly valid JSON with keys: "
            "'original_request_received', 'domain', 'experiment_type', 'refined_experiment_prompt', "
            "'filtered_search_terms', 'apparatus', 'parameters', 'search_queries', 'visual_reference_requirements', 'constraints', 'uncertainties'."
        )

        user_msg = (
            f"Original Request: {raw_prompt}\n"
            f"Filtered Scientific Tokens: {filtered_text}\n"
            f"Domain Hint: {domain_hint or 'unspecified'}\n"
            "Output complete refinement JSON now."
        )

        payload = {
            "model": refiner_model_id,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": '{"original_request_received": true, "domain": "'},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
            "stream": True,
            "stop": ["\n\n", "}\n\n"],
        }

        url = f"{LM_STUDIO_OPENAI_BASE}/chat/completions"

        def _call_refiner_http() -> str:
            parts: List[str] = []
            try:
                resp = requests.post(url, json=payload, stream=True, timeout=timeout)
                if resp.status_code == 200:
                    resp.encoding = "utf-8"
                    for line in resp.iter_lines(decode_unicode=True):
                        if line and line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                c = chunk["choices"][0]["delta"].get("content")
                                if c:
                                    parts.append(c)
                            except Exception:
                                pass
            except Exception as e:
                logger.warning("[PromptRefinerService] Qwen3-4B HTTP call error: %s", e)
            return "".join(parts).strip()

        import asyncio
        from simulation_agent.llm_client import strip_thinking_tags
        raw_tail = strip_thinking_tags(await asyncio.to_thread(_call_refiner_http))
        reconstructed = '{"original_request_received": true, "domain": "' + raw_tail

        # Parse JSON
        parsed = None
        try:
            parsed = json.loads(reconstructed)
        except Exception:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(reconstructed)
            except Exception:
                pass

        if not parsed or not isinstance(parsed, dict):
            logger.warning("[PromptRefinerService] Falling back to heuristic refinement.")
            domain = domain_hint if domain_hint and domain_hint != "unspecified" else "general"
            refined_output = RefinedPromptOutput(
                original_request_received=True,
                domain=domain,
                experiment_type="scientific_simulation",
                refined_experiment_prompt=f"Interactive 3D simulation of {raw_prompt}",
                filtered_search_terms=search_terms,
                apparatus=[filtered_text],
                parameters={},
                search_queries=[f"{filtered_text} diagram simulation"],
                visual_reference_requirements=["apparatus layout", "spatial relationships"],
                constraints=[],
                uncertainties=[],
            )
        else:
            # Coerce cleanly into Pydantic schema (field validators normalize str -> List[str], domain aliases, etc.)
            domain_val = parsed.get("domain", domain_hint or "general")
            try:
                refined_output = RefinedPromptOutput(
                    original_request_received=True,
                    domain=domain_val,
                    experiment_type=parsed.get("experiment_type", "experiment"),
                    refined_experiment_prompt=str(parsed.get("refined_experiment_prompt") or f"Interactive 3D simulation of {raw_prompt}"),
                    filtered_search_terms=parsed.get("filtered_search_terms") or search_terms,
                    apparatus=parsed.get("apparatus", []),
                    parameters=parsed.get("parameters", {}),
                    search_queries=parsed.get("search_queries") or [f"{filtered_text} technical diagram"],
                    visual_reference_requirements=parsed.get("visual_reference_requirements", ["apparatus layout"]),
                    constraints=parsed.get("constraints", []),
                    uncertainties=parsed.get("uncertainties", []),
                )
            except Exception as val_err:
                logger.warning("[PromptRefinerService] RefinedPromptOutput validation fallback: %s", val_err)
                refined_output = RefinedPromptOutput(
                    original_request_received=True,
                    domain=domain_hint or "general",
                    experiment_type="scientific_simulation",
                    refined_experiment_prompt=f"Interactive 3D simulation of {raw_prompt}",
                    filtered_search_terms=search_terms,
                    apparatus=[filtered_text],
                    parameters={},
                    search_queries=[f"{filtered_text} diagram simulation"],
                    visual_reference_requirements=["apparatus layout"],
                    constraints=[],
                    uncertainties=[],
                )

        # ── Step 4: Execute Free Web Search (off event loop) ──
        logger.info("[PromptRefinerService] Executing free reference search for domain '%s'...", refined_output.domain)
        candidates = await asyncio.to_thread(
            free_search_service.find_references,
            domain=refined_output.domain,
            search_queries=refined_output.search_queries,
            filtered_search_terms=refined_output.filtered_search_terms,
        )

        # ── Step 5: Qwen3-4B Evaluates & Selects Reference (off event loop) ──
        logger.info("[PromptRefinerService] Qwen3-4B evaluating %d visual reference candidates...", len(candidates))
        selection_result = await asyncio.to_thread(
            select_best_reference_with_qwen, refined_output, candidates, 25
        )

        return refined_output, selection_result


prompt_refiner_service = PromptRefinerService()

