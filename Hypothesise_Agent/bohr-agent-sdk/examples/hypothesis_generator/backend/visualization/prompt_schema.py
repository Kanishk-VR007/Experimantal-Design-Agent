"""
Pydantic Schemas for Prompt Refinement and Search Results
=========================================================
Defines the strict contracts for:
  - Qwen 4B Thinking prompt refinement and intelligent stop-word filtering.
  - Search queries, candidate references, and relevance selection metadata.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


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


class RefinedPromptOutput(BaseModel):
    """
    Validated shape of Qwen 4B Thinking prompt refinement.
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


class ReferenceItem(BaseModel):
    """
    Single visual reference candidate or selected reference.
    """
    source_name: str = Field(..., description="Source name (e.g., Wikimedia Commons, FreeCAD, CircuitJS1)")
    page_url: str = Field(default="", description="Web page or documentation URL")
    image_url: str = Field(..., description="Direct HTTP/HTTPS link to reference image or diagram")
    image_type: str = Field(default="technical_diagram", description="Type: technical_diagram, 3d_render, schematic, photograph")
    license: str = Field(default="Open / Public Domain", description="License metadata (e.g., CC-BY-SA 4.0, Public Domain, MIT)")
    license_verified: bool = Field(default=False)
    relevance_reason: str = Field(default="", description="Why this reference accurately depicts the experimental setup")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class SearchSelectionResult(BaseModel):
    """
    Result of Qwen 4B Thinking's evaluation of candidate references.
    """
    search_performed: bool = Field(default=True)
    refined_experiment_prompt: str = Field(default="")
    selected_references: List[ReferenceItem] = Field(default_factory=list)
    search_limitations: List[str] = Field(default_factory=list)
    fallback_required: bool = Field(default=False)

