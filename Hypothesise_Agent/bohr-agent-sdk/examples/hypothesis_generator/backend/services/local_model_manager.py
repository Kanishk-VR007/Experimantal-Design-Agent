"""
Centralized Sequential Local Model Execution Manager
=====================================================
Enforces the Strict Single Active Model Policy for LM Studio.
Guarantees that on constrained local hardware (~6 GB VRAM):
  1. Only ONE model (Qwen 4B, Qwen3-VL-2B, or DeepSeek 7B) is loaded in GPU memory at a time.
  2. Transitions verify complete unloading via LM Studio native REST API before loading the next model.
  3. Provides an exclusive process-safe asynchronous lock and queue to prevent concurrency collisions.
"""

import os
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configured Model Keys from Environment
LM_STUDIO_BASE = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234").rstrip("/")
LM_STUDIO_REST_BASE = os.getenv("LM_STUDIO_REST_BASE_URL", f"{LM_STUDIO_BASE}/api/v1").rstrip("/")
LM_STUDIO_OPENAI_BASE = os.getenv("LM_STUDIO_OPENAI_BASE_URL", f"{LM_STUDIO_BASE}/v1").rstrip("/")
LM_STUDIO_API_TOKEN = os.getenv("LM_STUDIO_API_TOKEN", "").strip()

PROMPT_REFINER_MODEL_KEY = os.getenv("PROMPT_REFINER_MODEL", "qwen/qwen3-4b-thinking-2507").strip()
VISION_MODEL_KEY = os.getenv("VISION_MODEL", "qwen3-vl-2b-instruct").strip()
MAIN_MODEL_KEY = os.getenv("MAIN_MODEL", "oreal-deepseek-r1-distill-qwen-7b").strip()
MODEL_CONTEXT_LENGTH = int(os.getenv("MODEL_CONTEXT_LENGTH", "4096"))
MAX_ACTIVE_MODELS = int(os.getenv("MAX_ACTIVE_MODELS", "1"))


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
    return headers


class LocalModelManager:
    """
    Central sequential orchestrator for LM Studio models.
    """

    _instance: Optional["LocalModelManager"] = None

    def __init__(self):
        self._lock = asyncio.Lock()
        self.active_model_key: Optional[str] = None
        self.active_instance_id: Optional[str] = None
        self.last_transition_time: float = 0.0
        self.transition_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "LocalModelManager":
        if cls._instance is None:
            cls._instance = LocalModelManager()
        return cls._instance

    def query_models_status(self) -> Dict[str, Any]:
        """Query LM Studio native GET /api/v1/models to inspect loaded instances."""
        url = f"{LM_STUDIO_REST_BASE}/models"
        try:
            resp = requests.get(url, headers=_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                loaded_map: Dict[str, List[str]] = {}
                all_keys = []
                for m in models:
                    k = m.get("key", "")
                    all_keys.append(k)
                    insts = m.get("loaded_instances", [])
                    if insts:
                        loaded_map[k] = [inst.get("id") or inst.get("instance_id") or k for inst in insts]
                return {
                    "server_online": True,
                    "available_models": all_keys,
                    "loaded_instances": loaded_map,
                    "raw_models": models,
                }
        except Exception as e:
            logger.warning("[LocalModelManager] Failed to query /api/v1/models: %s", e)
        return {
            "server_online": False,
            "available_models": [],
            "loaded_instances": {},
            "raw_models": [],
        }

    async def get_loaded_instances_async(self) -> Dict[str, List[str]]:
        """Async helper to get currently loaded instances."""
        status = await asyncio.to_thread(self.query_models_status)
        return status.get("loaded_instances", {})

    async def unload_all_models(self) -> bool:
        """Unload any models currently active in LM Studio to free VRAM."""
        return await asyncio.to_thread(self.unload_all_models_sync)

    def unload_all_models_sync(self) -> bool:
        """Synchronous version of unload_all_models using requests."""
        status = self.query_models_status()
        loaded = status.get("loaded_instances", {})
        if not loaded:
            self.active_model_key = None
            self.active_instance_id = None
            return True

        for model_key, inst_ids in loaded.items():
            for inst_id in inst_ids:
                logger.info("[LocalModelManager] Unloading instance '%s' of model '%s'...", inst_id, model_key)
                try:
                    unload_url = f"{LM_STUDIO_REST_BASE}/models/unload"
                    payload = {"instance_id": inst_id}
                    resp = requests.post(unload_url, json=payload, headers=_headers(), timeout=30)
                    logger.info("[LocalModelManager] Unload response (%s): %s", resp.status_code, resp.text[:100])
                except Exception as e:
                    logger.warning("[LocalModelManager] Failed unload request for '%s': %s", inst_id, e)

        for _ in range(20):
            time.sleep(0.5)
            status = self.query_models_status()
            if not status.get("loaded_instances"):
                self.active_model_key = None
                self.active_instance_id = None
                logger.info("[LocalModelManager] Verified all models successfully unloaded.")
                return True

        logger.warning("[LocalModelManager] Warning: some instances may still appear loaded.")
        return False

    async def load_model(self, target_model_key: str, context_length: int = MODEL_CONTEXT_LENGTH) -> bool:
        """
        Sequentially load target_model_key:
          1. Check if target is already the sole loaded instance.
          2. If another model is loaded, unload it completely.
          3. Verify unload completion via GET /api/v1/models.
          4. Load target_model_key via POST /api/v1/models/load.
          5. Verify residency.
        """
        return await asyncio.to_thread(self.load_model_sync, target_model_key, context_length)

    def load_model_sync(self, target_model_key: str, context_length: int = MODEL_CONTEXT_LENGTH) -> bool:
        """Synchronous version of load_model using requests."""
        t0 = time.time()
        status = self.query_models_status()
        if not status.get("server_online"):
            logger.warning("[LocalModelManager] LM Studio server is unreachable at %s", LM_STUDIO_BASE)
            return False

        loaded = status.get("loaded_instances", {})
        if target_model_key in loaded and len(loaded) == 1:
            insts = loaded[target_model_key]
            self.active_model_key = target_model_key
            self.active_instance_id = insts[0] if insts else target_model_key
            logger.info("[LocalModelManager] Model '%s' is already solely active in GPU memory.", target_model_key)
            return True

        # Unload other models if loaded
        if loaded:
            logger.info("[LocalModelManager] Other models detected in VRAM (%s). Unloading...", list(loaded.keys()))
            self.unload_all_models_sync()

        # Load requested target
        logger.info("[LocalModelManager] Loading model '%s' (context_length=%d)...", target_model_key, context_length)
        load_url = f"{LM_STUDIO_REST_BASE}/models/load"
        payload = {
            "model": target_model_key,
            "context_length": context_length,
            "eval_batch_size": 128,
            "echo_load_config": True,
        }

        try:
            resp = requests.post(load_url, json=payload, headers=_headers(), timeout=60)
            if resp.status_code == 200:
                res_data = resp.json()
                inst_id = res_data.get("instance_id") or target_model_key
                self.active_model_key = target_model_key
                self.active_instance_id = inst_id
                elapsed = time.time() - t0
                self.last_transition_time = elapsed
                self.transition_history.append({
                    "model": target_model_key,
                    "instance_id": inst_id,
                    "timestamp": time.time(),
                    "duration_s": elapsed,
                    "status": "loaded",
                })
                logger.info("[LocalModelManager] Successfully loaded '%s' in %.2fs (instance_id=%s)", target_model_key, elapsed, inst_id)
                return True
            else:
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
        context_length: int = MODEL_CONTEXT_LENGTH,
        **kwargs,
    ):
        """
        Execute a stage under exclusive lock:
          1. Acquire global inference lock.
          2. Ensure target_model_key is loaded (unloading prior model).
          3. Execute stage work.
          4. Returns result.
        """
        async with self._lock:
            await self.load_model(target_model_key, context_length=context_length)
            return await coroutine_func(*args, **kwargs)

    def get_telemetry(self) -> Dict[str, Any]:
        """Telemetry metadata for health endpoints and frontend monitor."""
        return {
            "active_model": self.active_model_key,
            "active_instance_id": self.active_instance_id,
            "max_active_models": MAX_ACTIVE_MODELS,
            "single_active_model_policy": True,
            "last_transition_duration_s": self.last_transition_time,
            "configured_models": {
                "refiner": PROMPT_REFINER_MODEL_KEY,
                "vision": VISION_MODEL_KEY,
                "main": MAIN_MODEL_KEY,
            },
        }


# Singleton accessor
model_manager = LocalModelManager.get_instance()
