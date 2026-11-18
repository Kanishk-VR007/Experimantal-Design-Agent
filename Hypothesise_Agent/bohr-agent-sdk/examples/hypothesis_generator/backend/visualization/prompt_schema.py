"""
Pydantic Schemas for Prompt Refinement and Search Results
=========================================================
Defines the strict contracts for:
  - Qwen3-4B-Thinking prompt refinement and intelligent stop-word filtering.
  - Search queries, candidate references, and relevance selection metadata.

Includes resilient `mode="before"` validators so valid LLM JSON outputs that emit
a single string or list of objects for list/dict fields are normalized cleanly
instead of crashing the pipeline.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


DomainLiteral = Literal[
    "physics",
    "chemistry",
    "biology",
    "civil_engineering",
    "mechanical_engineering",
    "electronics",
    "computer_science",
    "general",
]

_DOMAIN_ALIASES = {
    "civil": "civil_engineering",
    "civil eng": "civil_engineering",
    "structural": "civil_engineering",
    "mechanical": "mechanical_engineering",
    "mech": "mechanical_engineering",
    "electrical": "electronics",
    "electrical_engineering": "electronics",
    "circuit": "electronics",
    "cs": "computer_science",
    "comp sci": "computer_science",
    "algorithms": "computer_science",
    "bio": "biology",
    "biochemistry": "biology",
    "chem": "chemistry",
    "physical": "physics",
}


def _coerce_str_list(v: Any) -> List[str]:
    """Normalize string / None / list-of-dicts / scalar into a clean List[str]."""
    if v is None:
        return []
    if isinstance(v, str):
        text = v.strip()
        if not text:
            return []
        # Split multiline/semicolon bullet lists cleanly while preserving prose sentences
        if "\n" in text:
            parts = [p.strip(" -•*\t") for p in text.splitlines() if p.strip(" -•*\t")]
            return parts or [text]
        if ";" in text and len(text.split(";")) > 1:
            return [p.strip() for p in text.split(";") if p.strip()]
        return [text]
    if isinstance(v, dict):
        return [f"{k}: {val}" for k, val in v.items() if val is not None]
    if isinstance(v, (list, tuple, set)):
        out: List[str] = []
        for item in v:
            if item is None:
                continue
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
            elif isinstance(item, dict):
                label = item.get("name") or item.get("description") or item.get("text")
                out.append(str(label) if label else json.dumps(item, ensure_ascii=False))
            else:
                out.append(str(item))
        return out
    return [str(v)]


def _coerce_dict(v: Any) -> Dict[str, Any]:
    """Normalize dict / list-of-kv-dicts / None into Dict[str, Any]."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        out: Dict[str, Any] = {}
        for item in v:
            if isinstance(item, dict) and "name" in item and "value" in item:
                out[str(item["name"])] = item["value"]
        return out
    return {}


class RefinedPromptOutput(BaseModel):
    """
    Validated shape of Qwen3-4B-Thinking prompt refinement.
    Ensures scientific parameters, domain classification, and search terms are explicit.
    """
    original_request_received: bool = Field(default=True)
    domain: DomainLiteral = Field(default="general")
    experiment_type: str = Field(default="general_experiment")
    refined_experiment_prompt: str = Field(..., description="Complete, precise natural-language experiment specification")
    filtered_search_terms: List[str] = Field(default_factory=list, description="Concise keywords with non-essential stop words removed")
    apparatus: List[str] = Field(default_factory=list, description="Extracted equipment, apparatus, components")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Identified experimental parameters and baselines")
    search_queries: List[str] = Field(default_factory=list, description="Targeted web search queries for reference visualization")
    visual_reference_requirements: List[str] = Field(default_factory=list, description="Key visual features the reference image must show")
    constraints: List[str] = Field(default_factory=list, description="Physical laws, boundary conditions, or limitations")
    uncertainties: List[str] = Field(default_factory=list, description="Ambiguous or missing user inputs")

    @field_validator("domain", mode="before")
    @classmethod
    def _normalize_domain(cls, v: Any) -> str:
        raw = str(v or "general").strip().lower().replace("-", "_")
        norm = _DOMAIN_ALIASES.get(raw, raw)
        valid = {
            "physics", "chemistry", "biology", "civil_engineering",
            "mechanical_engineering", "electronics", "computer_science", "general",
        }
        return norm if norm in valid else "general"

    @field_validator("experiment_type", mode="before")
    @classmethod
    def _normalize_exp_type(cls, v: Any) -> str:
        if not v or not isinstance(v, str):
            return "general_experiment"
        return v.strip().lower().replace(" ", "_") or "general_experiment"

    @field_validator(
        "filtered_search_terms",
        "apparatus",
        "search_queries",
        "visual_reference_requirements",
        "constraints",
        "uncertainties",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, v: Any) -> List[str]:
        return _coerce_str_list(v)

    @field_validator("parameters", mode="before")
    @classmethod
    def _normalize_parameters(cls, v: Any) -> Dict[str, Any]:
        return _coerce_dict(v)


class ReferenceItem(BaseModel):
    """Single visual reference candidate or selected reference."""
    source_name: str = Field(..., description="Source name (e.g., Wikimedia Commons, FreeCAD, CircuitJS1)")
    page_url: str = Field(default="", description="Web page or documentation URL")
    image_url: str = Field(..., description="Direct HTTP/HTTPS link to reference image or diagram")
    image_type: str = Field(default="technical_diagram", description="Type: technical_diagram, 3d_render, schematic, photograph")
    license: str = Field(default="Open / Public Domain", description="License metadata (e.g., CC-BY-SA 4.0, Public Domain, MIT)")
    license_verified: bool = Field(default=False)
    relevance_reason: str = Field(default="", description="Why this reference accurately depicts the experimental setup")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class SearchSelectionResult(BaseModel):
    """Result of Qwen3-4B-Thinking's evaluation of candidate references."""
    search_performed: bool = Field(default=True)
    refined_experiment_prompt: str = Field(default="")
    selected_references: List[ReferenceItem] = Field(default_factory=list)
    search_limitations: List[str] = Field(default_factory=list)
    fallback_required: bool = Field(default=False)

    @field_validator("search_limitations", mode="before")
    @classmethod
    def _normalize_limitations(cls, v: Any) -> List[str]:
        return _coerce_str_list(v)
