"""
Centralized Sequential Local Model Execution Manager
=====================================================
Enforces the Strict Single Active Model Policy for LM Studio on ~6 GB VRAM hardware:
  1. Model A (prompt_refiner): `qwen/qwen3-4b-thinking-2507` (text + tool use, vision=false)
  2. Model B (vision_analyzer): `qwen3-vl-4b-thinking` (vision=true + tool use)
  3. Model C (main_reasoner): `deepseek/deepseek-r1-0528-qwen3-8b` (reasoning-only, NO tool use)

Guarantees:
  - Capability-aware discovery via GET /api/v1/models and GET /v1/models.
  - Strict single active model policy (max_active_models = 1).
  - Ownership-aware instance tracking: never silently kills an unrelated external user-loaded model.
  - Cross-process lockfile + asyncio.Lock for multi-worker GPU safety.
  - Verified unload via GET /api/v1/models before loading the next model.
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
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# LM Studio runtime endpoints
LM_STUDIO_BASE = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234").rstrip("/")
LM_STUDIO_REST_BASE = os.getenv("LM_STUDIO_REST_BASE_URL", f"{LM_STUDIO_BASE}/api/v1").rstrip("/")
LM_STUDIO_OPENAI_BASE = os.getenv("LM_STUDIO_OPENAI_BASE_URL", f"{LM_STUDIO_BASE}/v1").rstrip("/")
LM_STUDIO_API_TOKEN = os.getenv("LM_STUDIO_API_TOKEN", "").strip()

# Exact three-model mapping (new LM_STUDIO_* vars take precedence over legacy aliases)
PROMPT_REFINER_MODEL_KEY = (
    os.getenv("LM_STUDIO_PROMPT_REFINER_MODEL")
    or os.getenv("PROMPT_REFINER_MODEL")
    or "qwen/qwen3-4b-thinking-2507"
).strip()

VISION_MODEL_KEY = (
    os.getenv("LM_STUDIO_VISION_MODEL")
    or os.getenv("VISION_MODEL")
    or "qwen3-vl-4b-thinking"
).strip()

MAIN_MODEL_KEY = (
    os.getenv("LM_STUDIO_MAIN_MODEL")
    or os.getenv("MAIN_MODEL")
    or "deepseek/deepseek-r1-0528-qwen3-8b"
).strip()

MODEL_CONTEXT_LENGTH = int(os.getenv("MODEL_CONTEXT_LENGTH", "4096"))
REFINER_CONTEXT_LENGTH = int(os.getenv("LM_STUDIO_REFINER_CONTEXT_LENGTH", str(MODEL_CONTEXT_LENGTH)))
VISION_CONTEXT_LENGTH = int(os.getenv("LM_STUDIO_VISION_CONTEXT_LENGTH", str(MODEL_CONTEXT_LENGTH)))
MAIN_CONTEXT_LENGTH = int(os.getenv("LM_STUDIO_MAIN_CONTEXT_LENGTH", str(MODEL_CONTEXT_LENGTH)))
MAX_ACTIVE_MODELS = int(os.getenv("LM_STUDIO_MAX_ACTIVE_MODELS", os.getenv("MAX_ACTIVE_MODELS", "1")))

ROLE_CONFIG: Dict[str, Dict[str, Any]] = {
    "prompt_refiner": {
        "model_key": PROMPT_REFINER_MODEL_KEY,
        "context_length": REFINER_CONTEXT_LENGTH,
        "requires_vision": False,
        "supports_tools": True,
        "reasoning_only": False,
    },
    "vision_analyzer": {
        "model_key": VISION_MODEL_KEY,
        "context_length": VISION_CONTEXT_LENGTH,
        "requires_vision": True,
        "supports_tools": True,
        "reasoning_only": False,
    },
    "main_reasoner": {
        "model_key": MAIN_MODEL_KEY,
        "context_length": MAIN_CONTEXT_LENGTH,
        "requires_vision": False,
        "supports_tools": False,
        "reasoning_only": True,
    },
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

    def __init__(self):
        self._lock = asyncio.Lock()
        self.active_model_key: Optional[str] = None
        self.active_instance_id: Optional[str] = None
        self._owned_instances: Set[str] = set()
        self.last_transition_time: float = 0.0
        self.last_conflict: Optional[str] = None
        self.transition_history: List[Dict[str, Any]] = []
        self.discovered_capabilities: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "LocalModelManager":
        if cls._instance is None:
            cls._instance = LocalModelManager()
        return cls._instance

    def query_models_status(self) -> Dict[str, Any]:
        """Query LM Studio native GET /api/v1/models (and /v1/models fallback) to inspect loaded instances & capabilities."""
        url = f"{LM_STUDIO_REST_BASE}/models"
        try:
            resp = requests.get(url, headers=_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                loaded_map: Dict[str, List[str]] = {}
                capabilities_map: Dict[str, Dict[str, Any]] = {}
                all_keys = []
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

    def discover_and_verify_models(self) -> Dict[str, Any]:
        """
        Capability-aware startup verification against GET /api/v1/models and GET /v1/models.
        Verifies each role's configured model key and checks required capabilities (e.g. vision=True for vision role).
        """
        rest_status = self.query_models_status()
        openai_ids: List[str] = []
        try:
            r_oai = requests.get(f"{LM_STUDIO_OPENAI_BASE}/models", headers=_headers(), timeout=5)
            if r_oai.status_code == 200:
                openai_ids = [m.get("id", "") for m in r_oai.json().get("data", []) if m.get("id")]
        except Exception:
            pass

        available = set(rest_status.get("available_models") or [])
        caps = rest_status.get("capabilities") or {}
        role_report: Dict[str, Any] = {}
        issues: List[str] = []

        for role_name, cfg in ROLE_CONFIG.items():
            key = cfg["model_key"]
            present = key in available
            model_caps = caps.get(key, {})
            vision_ok = (not cfg["requires_vision"]) or bool(model_caps.get("vision", False))
            if rest_status["server_online"] and not present:
                issues.append(f"Role '{role_name}' model '{key}' not found in LM Studio catalog.")
            if present and not vision_ok:
                issues.append(
                    f"Role '{role_name}' model '{key}' lacks required vision capability (capabilities.vision=False)."
                )
            role_report[role_name] = {
                "model_key": key,
                "context_length": cfg["context_length"],
                "available": present,
                "vision_capable": bool(model_caps.get("vision", False)),
                "trained_for_tool_use": bool(model_caps.get("trained_for_tool_use", False)),
                "reasoning_only": cfg["reasoning_only"],
                "capability_valid": present and vision_ok,
            }

        return {
            "server_online": rest_status["server_online"],
            "openai_models": openai_ids,
            "roles": role_report,
            "all_roles_valid": rest_status["server_online"] and all(r["capability_valid"] for r in role_report.values()),
            "issues": issues,
        }

    def detect_external_models(self, status: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """Return any loaded LM Studio instances NOT owned by Hypothesise Agent."""
        st = status or self.query_models_status()
        loaded = st.get("loaded_instances") or {}
        known_pipeline_keys = {PROMPT_REFINER_MODEL_KEY, VISION_MODEL_KEY, MAIN_MODEL_KEY}
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

    def unload_all_models_sync(self, allow_external: bool = False) -> bool:
        """
        Unload active pipeline-owned models in LM Studio and verify absence from `loaded_instances`.
        If an unrelated external user-loaded model is detected and `allow_external=False`,
        refuses to silently unload it and records `self.last_conflict`.
        """
        with _cross_process_gpu_lock():
            status = self.query_models_status()
            loaded = status.get("loaded_instances", {})
            if not loaded:
                self.active_model_key = None
                self.active_instance_id = None
                self._owned_instances.clear()
                self.last_conflict = None
                return True

            if not allow_external:
                external = self.detect_external_models(status)
                if external:
                    self.last_conflict = (
                        f"External user-loaded model(s) detected in LM Studio: {list(external.keys())}. "
                        "Refusing to silently unload external models; unload them manually or pass allow_external=True."
                    )
                    logger.warning("[LocalModelManager] %s", self.last_conflict)
                    return False

            for model_key, inst_ids in loaded.items():
                for inst_id in inst_ids:
                    logger.info("[LocalModelManager] Unloading instance '%s' of model '%s'...", inst_id, model_key)
                    try:
                        unload_url = f"{LM_STUDIO_REST_BASE}/models/unload"
                        resp = requests.post(unload_url, json={"instance_id": inst_id}, headers=_headers(), timeout=30)
                        logger.info("[LocalModelManager] Unload response (%s): %s", resp.status_code, resp.text[:100])
                        self._owned_instances.discard(inst_id)
                    except Exception as e:
                        logger.warning("[LocalModelManager] Failed unload request for '%s': %s", inst_id, e)

            for _ in range(24):
                time.sleep(0.5)
                chk = self.query_models_status()
                if not chk.get("loaded_instances"):
                    self.active_model_key = None
                    self.active_instance_id = None
                    self._owned_instances.clear()
                    self.last_conflict = None
                    logger.info("[LocalModelManager] Verified all models successfully unloaded.")
                    return True

            logger.warning("[LocalModelManager] Warning: some instances still appear loaded after unload polling.")
            return False

    def _context_length_for_model(self, model_key: str, override: Optional[int]) -> int:
        if override is not None:
            return override
        if model_key == PROMPT_REFINER_MODEL_KEY:
            return REFINER_CONTEXT_LENGTH
        if model_key == VISION_MODEL_KEY:
            return VISION_CONTEXT_LENGTH
        if model_key == MAIN_MODEL_KEY:
            return MAIN_CONTEXT_LENGTH
        return MODEL_CONTEXT_LENGTH

    async def load_model(
        self,
        target_model_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
    ) -> bool:
        return await asyncio.to_thread(
            self.load_model_sync, target_model_key, context_length, allow_external_unload
        )

    def load_model_sync(
        self,
        target_model_key: str,
        context_length: Optional[int] = None,
        allow_external_unload: bool = False,
    ) -> bool:
        """
        Sequentially load `target_model_key` enforcing strict single-active-model policy:
          1. Verify server online & capability checks (vision role must have vision=True).
          2. Check if target is already the sole loaded instance.
          3. Unload other models (respecting external-model ownership policy) and verify empty VRAM.
          4. Load `target_model_key` via POST /api/v1/models/load and track returned `instance_id`.
        """
        eff_ctx = self._context_length_for_model(target_model_key, context_length)
        t0 = time.time()

        with _cross_process_gpu_lock():
            status = self.query_models_status()
            if not status.get("server_online"):
                logger.warning("[LocalModelManager] LM Studio server is unreachable at %s", LM_STUDIO_BASE)
                return False

            # Capability check: vision role model must support vision
            caps = status.get("capabilities") or {}
            if target_model_key == VISION_MODEL_KEY and target_model_key in caps:
                if not caps[target_model_key].get("vision", False):
                    logger.error(
                        "[LocalModelManager] Refusing to load '%s' as vision model: capabilities.vision is False.",
                        target_model_key,
                    )
                    return False

            loaded = status.get("loaded_instances", {})
            if target_model_key in loaded and len(loaded) == 1:
                insts = loaded[target_model_key]
                inst_id = insts[0] if insts else target_model_key
                self.active_model_key = target_model_key
                self.active_instance_id = inst_id
                self._owned_instances.add(inst_id)
                self.last_conflict = None
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
                        logger.error("[LocalModelManager] %s", self.last_conflict)
                        return False

                logger.info("[LocalModelManager] Unloading prior model(s) (%s) before loading '%s'...", list(loaded.keys()), target_model_key)
                for m_key, inst_ids in loaded.items():
                    for iid in inst_ids:
                        try:
                            requests.post(
                                f"{LM_STUDIO_REST_BASE}/models/unload",
                                json={"instance_id": iid},
                                headers=_headers(),
                                timeout=30,
                            )
                            self._owned_instances.discard(iid)
                        except Exception as exc:
                            logger.warning("[LocalModelManager] Unload warning for '%s': %s", iid, exc)

                # Verify unload completion before loading next model
                unloaded_clean = False
                for _ in range(24):
                    time.sleep(0.5)
                    if not self.query_models_status().get("loaded_instances"):
                        unloaded_clean = True
                        break
                if not unloaded_clean:
                    logger.error("[LocalModelManager] Prior model failed to unload cleanly; aborting load of '%s'.", target_model_key)
                    return False

            logger.info("[LocalModelManager] Loading model '%s' (context_length=%d)...", target_model_key, eff_ctx)
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
                    timeout=90,
                )
                if resp.status_code == 200:
                    res_data = resp.json()
                    inst_id = res_data.get("instance_id") or target_model_key
                    self.active_model_key = target_model_key
                    self.active_instance_id = inst_id
                    self._owned_instances.add(inst_id)
                    self.last_conflict = None
                    elapsed = time.time() - t0
                    self.last_transition_time = elapsed
                    self.transition_history.append({
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
                logger.error("Failed to load model %s: HTTP %s - %s", target_model_key, resp.status_code, resp.text[:200])
                return False
            except Exception as e:
                logger.error("[LocalModelManager] Error during load of '%s': %s", target_model_key, e)
                return False

    async def execute_sequential_stage(
        self,
        target_model_key: str,
        coroutine_func,
        *args,
        context_length: Optional[int] = None,
        **kwargs,
    ):
        """Acquire exclusive lock, switch active model sequentially, execute stage."""
        async with self._lock:
            ok = await self.load_model(target_model_key, context_length=context_length)
            if not ok:
                raise RuntimeError(
                    self.last_conflict or f"Failed to load LM Studio model '{target_model_key}'"
                )
            return await coroutine_func(*args, **kwargs)

    def get_telemetry(self) -> Dict[str, Any]:
        """Telemetry metadata for health endpoints and frontend monitor."""
        return {
            "active_model": self.active_model_key,
            "active_instance_id": self.active_instance_id,
            "owned_instances": sorted(self._owned_instances),
            "last_conflict": self.last_conflict,
            "max_active_models": MAX_ACTIVE_MODELS,
            "single_active_model_policy": True,
            "last_transition_duration_s": round(self.last_transition_time, 3),
            "configured_models": {
                "refiner": PROMPT_REFINER_MODEL_KEY,
                "vision": VISION_MODEL_KEY,
                "main": MAIN_MODEL_KEY,
            },
            "role_capabilities": {
                role: {
                    "model_key": cfg["model_key"],
                    "context_length": cfg["context_length"],
                    "requires_vision": cfg["requires_vision"],
                    "supports_tools": cfg["supports_tools"],
                    "reasoning_only": cfg["reasoning_only"],
                }
                for role, cfg in ROLE_CONFIG.items()
            },
        }


# Singleton accessor
model_manager = LocalModelManager.get_instance()
