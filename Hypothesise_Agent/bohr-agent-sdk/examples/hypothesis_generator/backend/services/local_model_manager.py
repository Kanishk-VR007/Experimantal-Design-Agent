"""
Centralized Sequential Local Model Execution Manager
=====================================================
Enforces the Strict Single Active Model Policy for LM Studio via `model_registry.py`:
  1. `prompt_refiner`  -> Qwen3-4B-Thinking (`qwen/qwen3-4b-thinking-2507`)
  2. `vision_analyzer` -> Qwen3-VL-4B-Thinking (`qwen3-vl-4b-thinking`)
  3. `main_reasoner`   -> DeepSeek-R1-0528-Qwen3-8B (`deepseek/deepseek-r1-0528-qwen3-8b`)

Guarantees:
  - Single authoritative role lookup via `model_registry`.
  - Capability-aware discovery via GET /api/v1/models and GET /v1/models.
  - Strict single active model policy (MAX_ACTIVE_LOCAL_MODELS = 1).
  - Cross-process lockfile + asyncio.Lock for multi-worker GPU safety.
  - Explicit load, unload, and residency verification phases: a failed unload blocks
    the next model load and records a clear error.
  - Ownership-aware instance tracking: never silently kills external user-loaded models.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional, Set

import requests

from backend.services.model_registry import (
    ModelConfigurationError,
    get_lifecycle_settings,
    get_lm_studio_endpoints,
    model_registry,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_ENDPOINTS = get_lm_studio_endpoints()
_SETTINGS = get_lifecycle_settings()

LM_STUDIO_BASE = _ENDPOINTS["root_url"]
LM_STUDIO_REST_BASE = _ENDPOINTS["management_base_url"]
LM_STUDIO_OPENAI_BASE = _ENDPOINTS["openai_base_url"]
LM_STUDIO_API_TOKEN = os.getenv("LM_STUDIO_API_TOKEN", "").strip()

# Re-exported canonical keys sourced exclusively from model_registry
PROMPT_REFINER_MODEL_KEY = model_registry.get_model_id("prompt_refiner")
VISION_MODEL_KEY = model_registry.get_model_id("vision_analyzer")
MAIN_MODEL_KEY = model_registry.get_model_id("main_reasoner")

MODEL_CONTEXT_LENGTH = _SETTINGS["default_context_length"]
REFINER_CONTEXT_LENGTH = _SETTINGS["refiner_context_length"]
VISION_CONTEXT_LENGTH = _SETTINGS["vision_context_length"]
MAIN_CONTEXT_LENGTH = _SETTINGS["main_context_length"]
MAX_ACTIVE_MODELS = _SETTINGS["max_active_local_models"]
LOAD_TIMEOUT_SECONDS = _SETTINGS["load_timeout_seconds"]
UNLOAD_TIMEOUT_SECONDS = _SETTINGS["unload_timeout_seconds"]

ROLE_CONFIG: Dict[str, Dict[str, Any]] = {
    role_key: {
        "model_key": spec.configured_model_id,
        "context_length": spec.context_length,
        "requires_vision": spec.requires_vision,
        "supports_tools": spec.supports_tools,
        "reasoning_only": spec.reasoning_only,
    }
    for role_key, spec in model_registry.all_roles().items()
}


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
    return headers


@contextlib.contextmanager
def _cross_process_gpu_lock(timeout_s: float = 30.0):
    """Cross-process lockfile guarding LM Studio model load/unload transitions."""
    lock_path = os.path.join(tempfile.gettempdir(), "hypothesise_lmstudio_gpu.lock")
    fh = open(lock_path, "a+b")
    acquired = False
    deadline = time.time() + timeout_s
    try:
        while time.time() < deadline:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                time.sleep(0.1)
        yield acquired
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


class LocalModelManager:
    """Central sequential orchestrator for LM Studio models."""

    _instance: Optional["LocalModelManager"] = None

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.active_role_key: Optional[str] = None
        self.active_model_key: Optional[str] = None
        self.active_instance_id: Optional[str] = None
        self.current_pipeline_stage: str = "idle"
        self._owned_instances: Set[str] = set()
        self.last_transition_time: float = 0.0
        self.last_conflict: Optional[str] = None
        self.last_load_error: Optional[str] = None
        self.last_unload_error: Optional[str] = None
        self.transition_history: List[Dict[str, Any]] = []
        self.discovered_capabilities: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "LocalModelManager":
        if cls._instance is None:
            cls._instance = LocalModelManager()
        return cls._instance

    def set_pipeline_stage(self, stage: str) -> None:
        self.current_pipeline_stage = stage

    def query_models_status(self) -> Dict[str, Any]:
        """Query LM Studio native GET /api/v1/models to inspect loaded instances & capabilities."""
        url = f"{LM_STUDIO_REST_BASE}/models"
        try:
            resp = requests.get(url, headers=_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                loaded_map: Dict[str, List[str]] = {}
                capabilities_map: Dict[str, Dict[str, Any]] = {}
                all_keys: List[str] = []
                for m in models:
                    k = m.get("key", "")
                    if not k:
                        continue
                    all_keys.append(k)
                    caps = m.get("capabilities") or {}
                    capabilities_map[k] = {
                        "vision": bool(caps.get("vision", False)),
                        "trained_for_tool_use": bool(caps.get("trained_for_tool_use", False)),
                        "max_context_length": m.get("max_context_length"),
                        "params_string": m.get("params_string"),
                        "architecture": m.get("architecture"),
                    }
                    insts = m.get("loaded_instances", [])
                    if insts:
                        loaded_map[k] = [inst.get("id") or inst.get("instance_id") or k for inst in insts]
                self.discovered_capabilities = capabilities_map
                return {
                    "server_online": True,
                    "available_models": all_keys,
                    "loaded_instances": loaded_map,
                    "capabilities": capabilities_map,
                    "raw_models": models,
                }
        except Exception as e:
            logger.warning("[LocalModelManager] Failed to query /api/v1/models: %s", e)
        return {
            "server_online": False,
            "available_models": [],
            "loaded_instances": {},
            "capabilities": {},
            "raw_models": [],
        }

    def discover_and_verify_models(self, strict: bool = False) -> Dict[str, Any]:
        """
        Capability-aware startup verification against GET /api/v1/models and GET /v1/models.
        Delegates strict role validation to `model_registry.resolve_and_validate_catalog`.
        """
        rest_status = self.query_models_status()
        openai_ids: List[str] = []
        try:
            r_oai = requests.get(f"{LM_STUDIO_OPENAI_BASE}/models", headers=_headers(), timeout=5)
            if r_oai.status_code == 200:
                openai_ids = [m.get("id", "") for m in r_oai.json().get("data", []) if m.get("id")]
        except Exception:
            pass

        if not rest_status["server_online"]:
            return {
                "server_online": False,
                "openai_models": openai_ids,
                "roles": {k: v.to_dict() for k, v in model_registry.all_roles().items()},
                "all_roles_valid": False,
                "issues": [f"LM Studio server is unreachable at {LM_STUDIO_BASE}"],
            }

        cat_report = model_registry.resolve_and_validate_catalog(
            available_models=rest_status["available_models"],
            capabilities_map=rest_status["capabilities"],
            strict=strict,
        )
        return {
            "server_online": True,
            "openai_models": openai_ids,
            "roles": cat_report["roles"],
            "all_roles_valid": cat_report["all_roles_valid"],
            "issues": cat_report["issues"],
        }

    def detect_external_models(self, status: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """Return any loaded LM Studio instances NOT owned by Hypothesise Agent."""
        st = status or self.query_models_status()
        loaded = st.get("loaded_instances") or {}
        known_pipeline_keys = {spec.configured_model_id for spec in model_registry.all_roles().values()}
        external: Dict[str, List[str]] = {}
        for m_key, inst_ids in loaded.items():
            unowned = [iid for iid in inst_ids if iid not in self._owned_instances and m_key not in known_pipeline_keys]
            if unowned:
                external[m_key] = unowned
        return external

    async def get_loaded_instances_async(self) -> Dict[str, List[str]]:
        status = await asyncio.to_thread(self.query_models_status)
        return status.get("loaded_instances", {})

    async def unload_all_models(self, allow_external: bool = False) -> bool:
        return await asyncio.to_thread(self.unload_all_models_sync, allow_external)

    def unload_all_models_sync(self, allow_external: bool = False, poll_attempts: int = 24, poll_interval_s: float = 0.5) -> bool:
        """
        Unload active pipeline-owned models in LM Studio and verify absence from `loaded_instances`.
        Records `self.last_unload_error` if any instance remains loaded.
        """
        with _cross_process_gpu_lock():
            status = self.query_models_status()
            loaded = status.get("loaded_instances", {})
            if not loaded:
                self.active_role_key = None
                self.active_model_key = None
                self.active_instance_id = None
                self._owned_instances.clear()
                self.last_conflict = None
                self.last_unload_error = None
                return True

            if not allow_external:
                external = self.detect_external_models(status)
                if external:
                    self.last_conflict = (
                        f"External user-loaded model(s) detected in LM Studio: {list(external.keys())}. "
                        "Refusing to silently unload external models; unload them manually or pass allow_external=True."
                    )
                    self.last_unload_error = self.last_conflict
                    logger.warning("[LocalModelManager] %s", self.last_conflict)
                    return False

            for model_key, inst_ids in loaded.items():
                for inst_id in inst_ids:
                    logger.info("[LocalModelManager] Unloading instance '%s' of model '%s'...", inst_id, model_key)
                    try:
                        resp = requests.post(
                            f"{LM_STUDIO_REST_BASE}/models/unload",
                            json={"instance_id": inst_id},
                            headers=_headers(),
                            timeout=UNLOAD_TIMEOUT_SECONDS,
                        )
                        if resp.status_code != 200:
                            self.last_unload_error = f"Unload HTTP {resp.status_code} for '{inst_id}': {resp.text[:160]}"
                            logger.warning("[LocalModelManager] %s", self.last_unload_error)
                        else:
                            self._owned_instances.discard(inst_id)
                    except Exception as e:
                        self.last_unload_error = f"Unload request error for '{inst_id}': {e}"
                        logger.warning("[LocalModelManager] %s", self.last_unload_error)

            for _ in range(poll_attempts):
                if poll_interval_s > 0:
                    time.sleep(poll_interval_s)
                chk = self.query_models_status()
                if not chk.get("loaded_instances"):
                    self.active_role_key = None
                    self.active_model_key = None
                    self.active_instance_id = None
                    self._owned_instances.clear()
                    self.last_conflict = None
                    self.last_unload_error = None
                    logger.info("[LocalModelManager] Verified all models successfully unloaded.")
                    return True

            still_loaded = list(self.query_models_status().get("loaded_instances", {}).keys())
            self.last_unload_error = (
                f"Model unload verification failed; instance(s) still loaded in LM Studio: {still_loaded}."
            )
            logger.error("[LocalModelManager] %s", self.last_unload_error)
            return False

    def _context_length_for_model(self, model_key: str, override: Optional[int]) -> int:
        if override is not None:
            return override
        role_key = model_registry.role_for_model_id(model_key)
        if role_key:
            return model_registry.get_role(role_key).context_length
        return MODEL_CONTEXT_LENGTH

    async def load_role(
        self,
        role_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
    ) -> bool:
        spec = model_registry.get_role(role_key)
        return await self.load_model(
            spec.configured_model_id,
            context_length=context_length or spec.context_length,
            allow_external_unload=allow_external_unload,
            role_key=role_key,
        )

    def load_role_sync(
        self,
        role_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
    ) -> bool:
        spec = model_registry.get_role(role_key)
        return self.load_model_sync(
            spec.configured_model_id,
            context_length=context_length or spec.context_length,
            allow_external_unload=allow_external_unload,
            role_key=role_key,
        )

    async def load_model(
        self,
        target_model_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
        role_key: Optional[str] = None,
    ) -> bool:
        return await asyncio.to_thread(
            self.load_model_sync, target_model_key, context_length, allow_external_unload, role_key
        )

    def load_model_sync(
        self,
        target_model_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
        role_key: Optional[str] = None,
        poll_attempts: int = 24,
        poll_interval_s: float = 0.5,
    ) -> bool:
        """
        Sequentially load `target_model_key` enforcing strict single-active-model policy:
          1. Verify server online & capability checks (vision role must have vision=True).
          2. Check if target is already the sole loaded instance.
          3. Unload other models and VERIFY empty VRAM; if unload fails, BLOCK the next load.
          4. Load `target_model_key` via POST /api/v1/models/load and track returned `instance_id`.
        """
        eff_role = role_key or model_registry.role_for_model_id(target_model_key)
        eff_ctx = self._context_length_for_model(target_model_key, context_length)
        t0 = time.time()

        with _cross_process_gpu_lock():
            status = self.query_models_status()
            if not status.get("server_online"):
                self.last_load_error = f"LM Studio server is unreachable at {LM_STUDIO_BASE}"
                logger.warning("[LocalModelManager] %s", self.last_load_error)
                return False

            # Capability check: vision role model must support vision
            caps = status.get("capabilities") or {}
            if eff_role == "vision_analyzer" and target_model_key in caps:
                if not caps[target_model_key].get("vision", False):
                    self.last_load_error = (
                        f"Refusing to load '{target_model_key}' for role 'vision_analyzer': capabilities.vision is False."
                    )
                    logger.error("[LocalModelManager] %s", self.last_load_error)
                    return False

            loaded = status.get("loaded_instances", {})
            if target_model_key in loaded and len(loaded) == 1:
                insts = loaded[target_model_key]
                inst_id = insts[0] if insts else target_model_key
                self.active_role_key = eff_role
                self.active_model_key = target_model_key
                self.active_instance_id = inst_id
                self._owned_instances.add(inst_id)
                self.last_conflict = None
                self.last_load_error = None
                logger.info("[LocalModelManager] Model '%s' is already solely active in GPU memory.", target_model_key)
                return True

            if loaded:
                if not allow_external_unload:
                    external = self.detect_external_models(status)
                    if external:
                        self.last_conflict = (
                            f"External user-loaded model(s) active in LM Studio: {list(external.keys())}. "
                            "Cannot enforce single-active-model switch without unloading external model."
                        )
                        self.last_load_error = self.last_conflict
                        logger.error("[LocalModelManager] %s", self.last_conflict)
                        return False

                logger.info(
                    "[LocalModelManager] Unloading prior model(s) (%s) before loading '%s'...",
                    list(loaded.keys()),
                    target_model_key,
                )
                for m_key, inst_ids in loaded.items():
                    for iid in inst_ids:
                        try:
                            resp = requests.post(
                                f"{LM_STUDIO_REST_BASE}/models/unload",
                                json={"instance_id": iid},
                                headers=_headers(),
                                timeout=UNLOAD_TIMEOUT_SECONDS,
                            )
                            if resp.status_code != 200:
                                self.last_unload_error = f"Unload HTTP {resp.status_code} for '{iid}': {resp.text[:160]}"
                            else:
                                self._owned_instances.discard(iid)
                        except Exception as exc:
                            self.last_unload_error = f"Unload error for '{iid}': {exc}"
                            logger.warning("[LocalModelManager] %s", self.last_unload_error)

                # Verify unload completion BEFORE loading the next model
                unloaded_clean = False
                for _ in range(poll_attempts):
                    if poll_interval_s > 0:
                        time.sleep(poll_interval_s)
                    if not self.query_models_status().get("loaded_instances"):
                        unloaded_clean = True
                        break
                if not unloaded_clean:
                    self.last_unload_error = (
                        f"Blocked loading '{target_model_key}': prior model failed to unload cleanly from LM Studio."
                    )
                    self.last_load_error = self.last_unload_error
                    logger.error("[LocalModelManager] %s", self.last_unload_error)
                    return False

            logger.info("[LocalModelManager] Loading model '%s' (role=%s, context_length=%d)...", target_model_key, eff_role, eff_ctx)
            payload = {
                "model": target_model_key,
                "context_length": eff_ctx,
                "eval_batch_size": 128,
                "echo_load_config": True,
            }
            try:
                resp = requests.post(
                    f"{LM_STUDIO_REST_BASE}/models/load",
                    json=payload,
                    headers=_headers(),
                    timeout=LOAD_TIMEOUT_SECONDS,
                )
                if resp.status_code == 200:
                    res_data = resp.json()
                    inst_id = res_data.get("instance_id") or target_model_key
                    self.active_role_key = eff_role
                    self.active_model_key = target_model_key
                    self.active_instance_id = inst_id
                    self._owned_instances.add(inst_id)
                    self.last_conflict = None
                    self.last_load_error = None
                    self.last_unload_error = None
                    elapsed = time.time() - t0
                    self.last_transition_time = elapsed
                    self.transition_history.append({
                        "role": eff_role,
                        "model": target_model_key,
                        "instance_id": inst_id,
                        "context_length": eff_ctx,
                        "timestamp": time.time(),
                        "duration_s": round(elapsed, 3),
                        "status": "loaded",
                    })
                    logger.info(
                        "[LocalModelManager] Loaded '%s' in %.2fs (instance_id=%s, ctx=%d)",
                        target_model_key, elapsed, inst_id, eff_ctx,
                    )
                    return True
                self.last_load_error = f"Failed to load model {target_model_key}: HTTP {resp.status_code} - {resp.text[:200]}"
                logger.error("[LocalModelManager] %s", self.last_load_error)
                return False
            except Exception as e:
                self.last_load_error = f"Error during load of '{target_model_key}': {e}"
                logger.error("[LocalModelManager] %s", self.last_load_error)
                return False

    async def execute_sequential_stage(
        self,
        target_model_or_role: str,
        coroutine_func,
        *args,
        context_length: Optional[int] = None,
        unload_after: bool = False,
        **kwargs,
    ):
        """Acquire exclusive lock, switch active model sequentially, execute stage, optionally unload."""
        async with self._lock:
            if target_model_or_role in model_registry.VALID_ROLES:
                spec = model_registry.get_role(target_model_or_role)
                target_key = spec.configured_model_id
                role_key = target_model_or_role
            else:
                target_key = target_model_or_role
                role_key = model_registry.role_for_model_id(target_key)

            self.set_pipeline_stage(f"loading:{role_key or target_key}")
            ok = await self.load_model(target_key, context_length=context_length, role_key=role_key)
            if not ok:
                self.set_pipeline_stage("error")
                raise RuntimeError(
                    self.last_load_error or self.last_conflict or f"Failed to load LM Studio model '{target_key}'"
                )
            try:
                self.set_pipeline_stage(f"running:{role_key or target_key}")
                return await coroutine_func(*args, **kwargs)
            finally:
                if unload_after:
                    self.set_pipeline_stage(f"unloading:{role_key or target_key}")
                    unloaded = await self.unload_all_models()
                    if not unloaded:
                        self.set_pipeline_stage("unload_failed")
                    else:
                        self.set_pipeline_stage("idle")

    def get_diagnostic_status(self) -> Dict[str, Any]:
        """Detailed diagnostic status for GET /api/models/status (Part 10.5)."""
        live = self.query_models_status()
        discovery = self.discover_and_verify_models(strict=False) if live["server_online"] else None
        loaded_instances = live.get("loaded_instances", {})
        roles_out = []
        for role_key, spec in model_registry.all_roles().items():
            insts = loaded_instances.get(spec.configured_model_id, [])
            roles_out.append({
                "role_key": role_key,
                "expected_family": spec.expected_family,
                "configured_model_id": spec.configured_model_id,
                "discovered_model_id": spec.discovered_model_id,
                "current_instance_id": insts[0] if insts else None,
                "loaded": bool(insts),
                "requires_vision": spec.requires_vision,
                "supports_tools": spec.supports_tools,
                "reasoning_only": spec.reasoning_only,
                "context_length": spec.context_length,
                "health_status": spec.health_status,
            })
        return {
            "runtime": "lm_studio",
            "server_online": live["server_online"],
            "openai_base_url": LM_STUDIO_OPENAI_BASE,
            "management_base_url": LM_STUDIO_REST_BASE,
            "max_active_local_models": MAX_ACTIVE_MODELS,
            "single_active_model_policy": True,
            "current_pipeline_stage": self.current_pipeline_stage,
            "active_role_key": self.active_role_key,
            "active_model_id": self.active_model_key,
            "active_instance_id": self.active_instance_id,
            "loaded_instances": loaded_instances,
            "load_error": self.last_load_error,
            "unload_error": self.last_unload_error,
            "external_conflict": self.last_conflict,
            "all_roles_valid": discovery["all_roles_valid"] if discovery else False,
            "issues": discovery["issues"] if discovery else [f"LM Studio offline at {LM_STUDIO_BASE}"],
            "roles": roles_out,
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Telemetry metadata for health endpoints and frontend monitor."""
        return {
            "active_role": self.active_role_key,
            "active_model": self.active_model_key,
            "active_instance_id": self.active_instance_id,
            "current_pipeline_stage": self.current_pipeline_stage,
            "owned_instances": sorted(self._owned_instances),
            "last_conflict": self.last_conflict,
            "last_load_error": self.last_load_error,
            "last_unload_error": self.last_unload_error,
            "max_active_models": MAX_ACTIVE_MODELS,
            "single_active_model_policy": True,
            "last_transition_duration_s": round(self.last_transition_time, 3),
            "configured_models": {
                "refiner": model_registry.get_model_id("prompt_refiner"),
                "vision": model_registry.get_model_id("vision_analyzer"),
                "main": model_registry.get_model_id("main_reasoner"),
            },
            "role_capabilities": {
                role_key: spec.to_dict()
                for role_key, spec in model_registry.all_roles().items()
            },
        }


# Singleton accessor
model_manager = LocalModelManager.get_instance()
