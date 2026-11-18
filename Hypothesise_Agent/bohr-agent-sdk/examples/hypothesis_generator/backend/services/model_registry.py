"""
Authoritative LM Studio Model-Role Registry
===========================================
Single source of truth for the three-model sequential local architecture:
  - `prompt_refiner`  -> Qwen3-4B-Thinking (`qwen/qwen3-4b-thinking-2507`)
  - `vision_analyzer` -> Qwen3-VL-4B-Thinking (`qwen3-vl-4b-thinking`)
  - `main_reasoner`   -> DeepSeek-R1-0528-Qwen3-8B (`deepseek/deepseek-r1-0528-qwen3-8b`)

Agents and services request models strictly by stable role key (`prompt_refiner`,
`vision_analyzer`, `main_reasoner`) rather than hardcoding model identifiers.
Unknown or ambiguous model identifiers raise `ModelConfigurationError` rather
than silently substituting another model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class ModelConfigurationError(ValueError):
    """Raised when a role key is unknown or its configured LM Studio model is invalid/ambiguous."""


@dataclass
class ModelRoleSpec:
    """Metadata, capabilities, and runtime configuration for one canonical model role."""
    role_key: str
    expected_family: str
    configured_model_id: str
    required_capabilities: List[str] = field(default_factory=list)
    supported_modalities: List[str] = field(default_factory=lambda: ["text"])
    requires_vision: bool = False
    supports_tools: bool = False
    reasoning_only: bool = False
    context_length: int = 4096
    max_output_tokens: int = 2048
    temperature: float = 0.2
    loading_policy: str = "sequential_single_active"
    discovered_model_id: Optional[str] = None
    health_status: str = "unchecked"  # unchecked | available | missing | capability_mismatch | ambiguous

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_key": self.role_key,
            "expected_family": self.expected_family,
            "configured_model_id": self.configured_model_id,
            "discovered_model_id": self.discovered_model_id,
            "required_capabilities": list(self.required_capabilities),
            "supported_modalities": list(self.supported_modalities),
            "requires_vision": self.requires_vision,
            "supports_tools": self.supports_tools,
            "reasoning_only": self.reasoning_only,
            "context_length": self.context_length,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "loading_policy": self.loading_policy,
            "health_status": self.health_status,
        }


def _env_first(*names: str, default: str) -> str:
    for name in names:
        val = os.getenv(name, "").strip()
        if val:
            return val
    return default


def get_lm_studio_endpoints() -> Dict[str, str]:
    """Return canonical LM Studio OpenAI-compatible and native management URLs."""
    raw_base = _env_first("LM_STUDIO_BASE_URL", default="http://localhost:1234").rstrip("/")
    if raw_base.endswith("/v1"):
        root = raw_base[:-3].rstrip("/")
        openai_url = raw_base
    else:
        root = raw_base
        openai_url = _env_first("LM_STUDIO_OPENAI_BASE_URL", "LMSTUDIO_URL", default=f"{root}/v1").rstrip("/")
    mgmt_url = _env_first(
        "LM_STUDIO_MANAGEMENT_URL",
        "LM_STUDIO_REST_BASE_URL",
        default=f"{root}/api/v1",
    ).rstrip("/")
    return {
        "root_url": root,
        "openai_base_url": openai_url,
        "management_base_url": mgmt_url,
    }


def get_lifecycle_settings() -> Dict[str, int]:
    """Return global sequential model lifecycle settings."""
    default_ctx = int(_env_first("MODEL_CONTEXT_LENGTH", default="4096"))
    return {
        "max_active_local_models": int(
            _env_first("MAX_ACTIVE_LOCAL_MODELS", "LM_STUDIO_MAX_ACTIVE_MODELS", "MAX_ACTIVE_MODELS", default="1")
        ),
        "load_timeout_seconds": int(_env_first("MODEL_LOAD_TIMEOUT_SECONDS", default="90")),
        "unload_timeout_seconds": int(_env_first("MODEL_UNLOAD_TIMEOUT_SECONDS", default="30")),
        "default_context_length": default_ctx,
        "refiner_context_length": int(_env_first("LM_STUDIO_REFINER_CONTEXT_LENGTH", default=str(default_ctx))),
        "vision_context_length": int(_env_first("LM_STUDIO_VISION_CONTEXT_LENGTH", default=str(default_ctx))),
        "main_context_length": int(_env_first("LM_STUDIO_MAIN_CONTEXT_LENGTH", default=str(default_ctx))),
    }


class ModelRegistry:
    """Authoritative registry of the 3 canonical LM Studio model roles."""

    VALID_ROLES = ("prompt_refiner", "vision_analyzer", "main_reasoner")

    def __init__(self) -> None:
        self._roles: Dict[str, ModelRoleSpec] = {}
        self.reload_from_env()

    def reload_from_env(self) -> None:
        settings = get_lifecycle_settings()
        refiner_id = _env_first(
            "PROMPT_REFINER_MODEL",
            "LM_STUDIO_PROMPT_REFINER_MODEL",
            "LMSTUDIO_REFINER_MODEL",
            default="qwen/qwen3-4b-thinking-2507",
        )
        vision_id = _env_first(
            "VISION_ANALYZER_MODEL",
            "LM_STUDIO_VISION_MODEL",
            "VISION_MODEL",
            default="qwen3-vl-4b-thinking",
        )
        main_id = _env_first(
            "MAIN_REASONER_MODEL",
            "LM_STUDIO_MAIN_MODEL",
            "MAIN_MODEL",
            "LMSTUDIO_MODEL",
            default="deepseek/deepseek-r1-0528-qwen3-8b",
        )

        self._roles = {
            "prompt_refiner": ModelRoleSpec(
                role_key="prompt_refiner",
                expected_family="Qwen3-4B-Thinking",
                configured_model_id=refiner_id,
                required_capabilities=["text_generation"],
                supported_modalities=["text"],
                requires_vision=False,
                supports_tools=True,
                reasoning_only=False,
                context_length=settings["refiner_context_length"],
                max_output_tokens=1024,
                temperature=0.1,
            ),
            "vision_analyzer": ModelRoleSpec(
                role_key="vision_analyzer",
                expected_family="Qwen3-VL-4B-Thinking",
                configured_model_id=vision_id,
                required_capabilities=["text_generation", "vision"],
                supported_modalities=["text", "image"],
                requires_vision=True,
                supports_tools=True,
                reasoning_only=False,
                context_length=settings["vision_context_length"],
                max_output_tokens=1200,
                temperature=0.1,
            ),
            "main_reasoner": ModelRoleSpec(
                role_key="main_reasoner",
                expected_family="DeepSeek-R1-0528-Qwen3-8B",
                configured_model_id=main_id,
                required_capabilities=["text_generation", "reasoning"],
                supported_modalities=["text"],
                requires_vision=False,
                supports_tools=False,
                reasoning_only=True,
                context_length=settings["main_context_length"],
                max_output_tokens=2500,
                temperature=0.2,
            ),
        }

    def get_role(self, role_key: str) -> ModelRoleSpec:
        if role_key not in self._roles:
            raise ModelConfigurationError(
                f"Unknown model role '{role_key}'. Valid roles: {list(self.VALID_ROLES)}."
            )
        return self._roles[role_key]

    def get_model_id(self, role_key: str) -> str:
        spec = self.get_role(role_key)
        if not spec.configured_model_id:
            raise ModelConfigurationError(f"Role '{role_key}' has no configured LM Studio model ID.")
        return spec.configured_model_id

    def role_for_model_id(self, model_id: str) -> Optional[str]:
        for role_key, spec in self._roles.items():
            if model_id in (spec.configured_model_id, spec.discovered_model_id):
                return role_key
        return None

    def all_roles(self) -> Dict[str, ModelRoleSpec]:
        return dict(self._roles)

    def resolve_and_validate_catalog(
        self,
        available_models: List[str],
        capabilities_map: Optional[Dict[str, Dict[str, Any]]] = None,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate every role against discovered LM Studio models and capabilities.
        Raises `ModelConfigurationError` when `strict=True` and any configured ID is
        missing, ambiguous, or incompatible with required capabilities (e.g. vision).
        Never silently remaps a role to an unrelated model.
        """
        caps = capabilities_map or {}
        avail_list = list(available_models or [])
        avail_set = set(avail_list)
        issues: List[str] = []
        report: Dict[str, Any] = {}

        for role_key, spec in self._roles.items():
            target = spec.configured_model_id
            if target in avail_set:
                matched = [target]
            else:
                # Detect ambiguous partial matches without silently guessing
                matched = [m for m in avail_list if target.lower() in m.lower()]

            if len(matched) == 0:
                spec.discovered_model_id = None
                spec.health_status = "missing"
                issues.append(
                    f"Role '{role_key}' configured model '{target}' not found in LM Studio catalog ({avail_list})."
                )
            elif len(matched) > 1:
                spec.discovered_model_id = None
                spec.health_status = "ambiguous"
                issues.append(
                    f"Role '{role_key}' configured model '{target}' is ambiguous; matched multiple IDs: {matched}."
                )
            elif matched[0] != target:
                # Partial match is still ambiguous/unexact; require explicit configuration
                spec.discovered_model_id = None
                spec.health_status = "ambiguous"
                issues.append(
                    f"Role '{role_key}' configured model '{target}' does not match exact LM Studio ID '{matched[0]}'. "
                    "Configure the exact LM Studio identifier rather than relying on partial matching."
                )
            else:
                spec.discovered_model_id = matched[0]
                mcaps = caps.get(matched[0], {})
                if spec.requires_vision and not bool(mcaps.get("vision", False)):
                    spec.health_status = "capability_mismatch"
                    issues.append(
                        f"Role '{role_key}' model '{matched[0]}' does not advertise vision capability."
                    )
                else:
                    spec.health_status = "available"

            report[role_key] = spec.to_dict()

        if strict and issues:
            raise ModelConfigurationError("; ".join(issues))

        return {
            "all_roles_valid": len(issues) == 0,
            "roles": report,
            "issues": issues,
        }


model_registry = ModelRegistry()

