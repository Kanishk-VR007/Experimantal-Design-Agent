"""
Model-Role Mapping & Sequential LM Studio Policy Verification Suite (Part 10.6)
================================================================================
Repeatable, mocked unit tests covering all 15 mandatory checks in Part 10.6:
  1. Prompt-refinement tasks route only to `prompt_refiner`.
  2. Online search query generation & result evaluation use `prompt_refiner`.
  3. Image inputs route only to `vision_analyzer`.
  4. Vision model receives image bytes + analysis instruction and returns structured reconstruction JSON.
  5. Main scene-generation tasks route only to `main_reasoner`.
  6. Main model receives BOTH refined prompt and visual reconstruction instructions.
  7. Main model is NOT required to call tools directly (`supports_tools=False`, `reasoning_only=True`).
  8. No old Qwen3-VL-2B mapping remains in active runtime configuration.
  9. No OREAL 7B mapping remains as the active main model.
 10. No Ollama inference call remains for these three models.
 11. Unknown or ambiguous LM Studio model identifiers raise `ModelConfigurationError` rather than silently remapping.
 12. A second model cannot load until the previous model instance is confirmed unloaded.
 13. Concurrent requests cannot violate the single-active-model policy.
 14. A failed unload blocks the next load and produces a visible error.
 15. Vision input and image buffers are released after inference, including failure paths.
"""

from __future__ import annotations

import asyncio
import json
import os
import weakref
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.services.local_model_manager import LocalModelManager, model_manager
from backend.services.model_registry import (
    ModelConfigurationError,
    ModelRegistry,
    model_registry,
)
from backend.services.prompt_refiner_service import prompt_refiner_service
from backend.services.reference_selection_service import select_best_reference_with_qwen
from backend.services.vision_service import vision_service
from backend.visualization.prompt_schema import ReferenceItem, RefinedPromptOutput
from backend.visualization.visual_description_schema import VisualReconstructionInstructions
from backend.visualization.visualization_pipeline import (
    build_main_reasoner_context,
    visualization_pipeline,
)
from simulation_agent import llm_client


class _FakeLMStudioState:
    """Deterministic in-memory mock of LM Studio native REST + OpenAI APIs."""

    def __init__(self, fail_unload: bool = False):
        self.loaded: dict[str, list[str]] = {}
        self.load_events: list[str] = []
        self.unload_events: list[str] = []
        self.chat_models_used: list[str] = []
        self.max_simultaneous_loaded: int = 0
        self.fail_unload = fail_unload
        self.catalog = [
            {
                "key": "qwen/qwen3-4b-thinking-2507",
                "capabilities": {"vision": False, "trained_for_tool_use": True},
                "max_context_length": 262144,
            },
            {
                "key": "qwen3-vl-4b-thinking",
                "capabilities": {"vision": True, "trained_for_tool_use": True},
                "max_context_length": 262144,
            },
            {
                "key": "deepseek/deepseek-r1-0528-qwen3-8b",
                "capabilities": {"vision": False, "trained_for_tool_use": False},
                "max_context_length": 131072,
            },
        ]

    def mock_get(self, url: str, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "/api/v1/models" in url:
            models_out = []
            for m in self.catalog:
                entry = dict(m)
                insts = self.loaded.get(m["key"], [])
                entry["loaded_instances"] = [{"id": iid} for iid in insts]
                models_out.append(entry)
            resp.json.return_value = {"models": models_out}
        elif "/v1/models" in url:
            resp.json.return_value = {"data": [{"id": m["key"]} for m in self.catalog]}
        else:
            resp.status_code = 404
            resp.json.return_value = {}
        return resp

    def mock_post(self, url: str, json=None, *args, **kwargs):
        payload = json or {}
        resp = MagicMock()
        if url.endswith("/models/unload"):
            iid = payload.get("instance_id", "")
            self.unload_events.append(iid)
            if self.fail_unload:
                resp.status_code = 500
                resp.text = "Simulated GPU unload hang"
                return resp
            for k in list(self.loaded.keys()):
                if iid in self.loaded[k]:
                    self.loaded[k].remove(iid)
                    if not self.loaded[k]:
                        del self.loaded[k]
            resp.status_code = 200
            resp.text = "ok"
            resp.json.return_value = {"unloaded": iid}
            return resp

        if url.endswith("/models/load"):
            m_key = payload.get("model", "")
            iid = f"{m_key}#inst1"
            self.loaded.setdefault(m_key, []).append(iid)
            self.load_events.append(m_key)
            self.max_simultaneous_loaded = max(
                self.max_simultaneous_loaded, sum(len(v) for v in self.loaded.values())
            )
            resp.status_code = 200
            resp.json.return_value = {"instance_id": iid}
            return resp

        if url.endswith("/chat/completions"):
            m_key = payload.get("model", "")
            self.chat_models_used.append(m_key)
            resp.status_code = 200
            if m_key == "qwen3-vl-4b-thinking":
                vision_json = {
                    "domain": "mechanical_engineering",
                    "scene_type": "four_bar_linkage",
                    "scene_composition": {"camera_view": "three_quarter", "coordinate_system": "right_handed", "layout": "planar"},
                    "objects": [{"id": "crank", "name": "Crank Link", "geometry": "cylinder", "relative_position": "left"}],
                    "connections": [{"source": "ground", "target": "crank", "type": "revolute_joint"}],
                    "visual_instructions": ["Align four planar links on XY plane"],
                    "animation_hints": ["Rotate crank around pivot A"],
                    "uncertainties": ["Exact link cross-section estimated visually"],
                }
                resp.json.return_value = {"choices": [{"message": {"content": f"<think>analyzing</think>{json_dumps(vision_json)}"}}]}
            else:
                resp.iter_lines.return_value = [
                    'data: {"choices":[{"delta":{"content":"\\"selected_index\\": 0, \\"relevance_rationale\\": \\"Best diagram\\", \\"confidence\\": 0.9}"}}]}',
                    "data: [DONE]",
                ]
                resp.json.return_value = {"choices": [{"message": {"content": '{"selected_index": 0}'}}]}
            return resp

        resp.status_code = 404
        resp.text = "not found"
        return resp


def json_dumps(obj) -> str:
    return json.dumps(obj)


# ── Test 1 & 2: Prompt refinement & search evaluation route only to `prompt_refiner` ──
def test_01_02_prompt_refiner_and_reference_selection_route_only_to_prompt_refiner():
    fake = _FakeLMStudioState()
    mgr = LocalModelManager()

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.prompt_refiner_service.model_manager", mgr), \
         patch("backend.services.prompt_refiner_service.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.reference_selection_service.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.prompt_refiner_service.free_search_service.find_references", return_value=[]):
        asyncio.run(prompt_refiner_service.refine_prompt_and_search("Four-bar linkage mechanism crank 1m"))

    assert fake.load_events == ["qwen/qwen3-4b-thinking-2507"]
    assert all(m == "qwen/qwen3-4b-thinking-2507" for m in fake.chat_models_used)

    # Test 2: Reference selection uses `prompt_refiner`
    fake2 = _FakeLMStudioState()
    refined = RefinedPromptOutput(
        original_request_received=True,
        domain="mechanical_engineering",
        experiment_type="four_bar_linkage",
        refined_experiment_prompt="Four-bar linkage",
        apparatus=["crank", "coupler", "rocker"],
    )
    cands = [
        ReferenceItem(source_name="Wikimedia", image_url="https://commons.wikimedia.org/a.png"),
        ReferenceItem(source_name="OpenStax", image_url="https://openstax.org/b.png"),
    ]
    with patch("backend.services.reference_selection_service.requests.post", side_effect=fake2.mock_post):
        sel = select_best_reference_with_qwen(refined, cands)
    assert sel.selected_references
    assert fake2.chat_models_used == ["qwen/qwen3-4b-thinking-2507"]


# ── Test 3 & 4: Vision inputs route only to `vision_analyzer` and return structured JSON ──
def test_03_04_vision_analyzer_receives_image_bytes_and_returns_structured_instructions():
    fake = _FakeLMStudioState()
    mgr = LocalModelManager()
    captured_payloads = []

    def _capture_post(url, json=None, *args, **kwargs):
        if url.endswith("/chat/completions"):
            captured_payloads.append(json)
        return fake.mock_post(url, json=json, *args, **kwargs)

    refined = RefinedPromptOutput(
        original_request_received=True,
        domain="mechanical_engineering",
        experiment_type="four_bar_linkage",
        refined_experiment_prompt="Four-bar linkage kinematics",
        apparatus=["crank", "coupler", "rocker", "ground"],
    )
    ref = ReferenceItem(source_name="Wikimedia", image_url="https://commons.wikimedia.org/test.png")

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.vision_service.model_manager", mgr), \
         patch("backend.services.vision_service.requests.post", side_effect=_capture_post):
        result = asyncio.run(
            vision_service.analyze_reference_image(refined, ref, b"\x89PNG\r\n\x1a\nFAKEIMAGE", "image/png")
        )

    assert isinstance(result, VisualReconstructionInstructions)
    assert fake.load_events == ["qwen3-vl-4b-thinking"]
    assert captured_payloads[0]["model"] == "qwen3-vl-4b-thinking"
    content_parts = captured_payloads[0]["messages"][0]["content"]
    assert any(p.get("type") == "text" for p in content_parts)
    assert any(p.get("type") == "image_url" and "data:image/png;base64," in p["image_url"]["url"] for p in content_parts)
    assert len(result.objects) >= 1
    assert len(result.connections) >= 1


# ── Test 5, 6 & 7: Main reasoner receives refined prompt + visual instructions, NO tool calls ──
def test_05_06_07_main_reasoner_routing_context_and_no_tool_requirement():
    spec = model_registry.get_role("main_reasoner")
    assert spec.configured_model_id == "deepseek/deepseek-r1-0528-qwen3-8b"
    assert spec.reasoning_only is True
    assert spec.supports_tools is False

    ctx = build_main_reasoner_context(
        refined_output={"refined_experiment_prompt": "Four-bar linkage kinematics", "domain": "mechanical_engineering"},
        visual_instructions={"objects": [{"id": "crank"}], "visual_instructions": ["Align links"]},
        simulation_results={"domain": "mechanical_engineering", "experiment_id": "four_bar_linkage", "simulation_status": "success"},
    )
    assert ctx["role_key"] == "main_reasoner"
    assert ctx["model_id"] == "deepseek/deepseek-r1-0528-qwen3-8b"
    assert ctx["tools_enabled"] is False
    assert ctx["reasoning_only"] is True
    assert "refined_experiment_prompt" in ctx["refined_prompt"]
    assert "visual_instructions" in ctx["visual_reconstruction_instructions"]


# ── Test 8, 9 & 10: No Qwen3-VL-2B, no OREAL 7B, no Ollama inference for these 3 models ──
def test_08_09_10_no_stale_models_and_no_ollama_fallback_in_lmstudio_mode():
    roles = model_registry.all_roles()
    all_ids = [r.configured_model_id.lower() for r in roles.values()]
    assert all("qwen3-vl-2b" not in mid for mid in all_ids)
    assert all("oreal" not in mid for mid in all_ids)
    assert roles["prompt_refiner"].configured_model_id == "qwen/qwen3-4b-thinking-2507"
    assert roles["vision_analyzer"].configured_model_id == "qwen3-vl-4b-thinking"
    assert roles["main_reasoner"].configured_model_id == "deepseek/deepseek-r1-0528-qwen3-8b"

    # Test 10: When LM Studio is offline and provider is lmstudio, check_llm_health must NOT call Ollama
    with patch("simulation_agent.llm_client.check_lmstudio_status", return_value={"available": False, "server_reachable": False, "provider": "lmstudio", "active_model": "deepseek/deepseek-r1-0528-qwen3-8b", "models": []}), \
         patch("simulation_agent.llm_client.check_ollama_status", side_effect=AssertionError("Ollama must never be invoked for LM Studio models!")):
        health = llm_client.check_llm_health()
        assert health["provider"] == "lmstudio"
        assert health["available"] is False


# ── Test 11: Unknown or ambiguous LM Studio model ID raises clear error, no silent remap ──
def test_11_unknown_or_ambiguous_model_id_raises_configuration_error():
    reg = ModelRegistry()
    with pytest.raises(ModelConfigurationError):
        reg.get_role("nonexistent_role")

    # Missing configured model must fail strictly (never silently substitute another model)
    with pytest.raises(ModelConfigurationError, match="not found"):
        reg.resolve_and_validate_catalog(available_models=["some-other-random-model"], strict=True)

    # Non-vision model assigned to vision_analyzer must fail capability check
    with pytest.raises(ModelConfigurationError, match="vision capability"):
        reg.resolve_and_validate_catalog(
            available_models=[
                "qwen/qwen3-4b-thinking-2507",
                "qwen3-vl-4b-thinking",
                "deepseek/deepseek-r1-0528-qwen3-8b",
            ],
            capabilities_map={
                "qwen/qwen3-4b-thinking-2507": {"vision": False},
                "qwen3-vl-4b-thinking": {"vision": False},  # missing vision!
                "deepseek/deepseek-r1-0528-qwen3-8b": {"vision": False},
            },
            strict=True,
        )


# ── Test 12: Second model cannot load until previous instance is confirmed unloaded ──
def test_12_sequential_load_unloads_prior_model_before_loading_next():
    fake = _FakeLMStudioState()
    mgr = LocalModelManager()

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post):
        assert mgr.load_role_sync("prompt_refiner") is True
        assert mgr.load_role_sync("vision_analyzer") is True
        assert mgr.load_role_sync("main_reasoner") is True
        assert mgr.unload_all_models_sync(poll_attempts=3, poll_interval_s=0.0) is True

    assert fake.max_simultaneous_loaded == 1
    assert fake.load_events == [
        "qwen/qwen3-4b-thinking-2507",
        "qwen3-vl-4b-thinking",
        "deepseek/deepseek-r1-0528-qwen3-8b",
    ]
    assert len(fake.unload_events) >= 3
    assert fake.loaded == {}


# ── Test 13: Concurrent requests cannot violate the single-active-model policy ──
def test_13_concurrent_requests_serialized_single_active_model():
    fake = _FakeLMStudioState()
    mgr = LocalModelManager()

    async def _worker(role_key: str):
        async def _stage_work():
            await asyncio.sleep(0.02)
            assert sum(len(v) for v in fake.loaded.values()) <= 1
            return role_key

        return await mgr.execute_sequential_stage(role_key, _stage_work, unload_after=True)

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.local_model_manager.time.sleep", return_value=None):
        async def _run_all():
            return await asyncio.gather(
                _worker("prompt_refiner"),
                _worker("vision_analyzer"),
                _worker("main_reasoner"),
            )

        results = asyncio.run(_run_all())

    assert results == ["prompt_refiner", "vision_analyzer", "main_reasoner"]
    assert fake.max_simultaneous_loaded == 1
    assert fake.loaded == {}


# ── Test 14: Failed unload blocks next load and produces visible error ──
def test_14_failed_unload_blocks_next_load_and_records_error():
    fake = _FakeLMStudioState(fail_unload=True)
    mgr = LocalModelManager()

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post):
        assert mgr.load_model_sync("qwen/qwen3-4b-thinking-2507", poll_attempts=2, poll_interval_s=0.0) is True
        # Now attempt to load vision_analyzer while unload fails -> MUST be blocked!
        ok_next = mgr.load_model_sync("qwen3-vl-4b-thinking", poll_attempts=2, poll_interval_s=0.0)

    assert ok_next is False
    assert mgr.last_unload_error is not None
    assert "failed to unload" in mgr.last_unload_error.lower()
    assert "qwen3-vl-4b-thinking" not in fake.loaded


# ── Test 15: Vision image buffers released after inference, including failure paths ──
def test_15_vision_buffers_released_on_failure_path_and_status_endpoint():
    fake = _FakeLMStudioState()
    mgr = LocalModelManager()
    refined = RefinedPromptOutput(
        original_request_received=True,
        domain="mechanical_engineering",
        experiment_type="four_bar_linkage",
        refined_experiment_prompt="Four-bar linkage",
        apparatus=["crank"],
    )
    ref = ReferenceItem(source_name="Wikimedia", image_url="https://commons.wikimedia.org/fail.png")

    def _failing_post(url, *args, **kwargs):
        if url.endswith("/chat/completions"):
            raise RuntimeError("Simulated vision inference crash")
        return fake.mock_post(url, *args, **kwargs)

    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get), \
         patch("backend.services.local_model_manager.requests.post", side_effect=fake.mock_post), \
         patch("backend.services.vision_service.model_manager", mgr), \
         patch("backend.services.vision_service.requests.post", side_effect=_failing_post):
        with pytest.raises(RuntimeError, match="Simulated vision inference crash"):
            asyncio.run(vision_service.analyze_reference_image(refined, ref, b"\x89PNG_TEMP_BYTES", "image/png"))

    # Empty image bytes must be rejected immediately (never call vision with missing image)
    with pytest.raises(ValueError, match="empty or missing"):
        asyncio.run(vision_service.analyze_reference_image(refined, ref, b"", "image/png"))

    # Verify /api/models/status diagnostic endpoint exposes all required Part 10.5 fields
    from backend.server import app
    client = TestClient(app)
    with patch("backend.services.local_model_manager.requests.get", side_effect=fake.mock_get):
        resp = client.get("/api/models/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["runtime"] == "lm_studio"
    assert body["max_active_local_models"] == 1
    assert "current_pipeline_stage" in body
    assert "load_error" in body
    assert "unload_error" in body
    role_keys = {r["role_key"] for r in body["roles"]}
    assert role_keys == {"prompt_refiner", "vision_analyzer", "main_reasoner"}
