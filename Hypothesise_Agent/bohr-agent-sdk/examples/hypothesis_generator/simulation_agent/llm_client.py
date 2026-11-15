"""
Unified Local LLM Client (LM Studio Primary + Ollama Fallback)
==============================================================
Targets LM Studio OpenAI-compatible local server serving
`oreal-deepseek-r1-distill-qwen-7b` by default, with clean separation
of `<think>...</think>` / `reasoning_content` tokens and safe streaming.
"""

import os
import re
import json
import time
import logging
import shutil
import subprocess
from typing import Dict, Any, Generator, List, Optional, Tuple
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger(__name__)

LMS_CLI = os.path.expanduser(r"~\.lmstudio\bin\lms.exe")


def get_llm_config() -> Dict[str, str]:
    """Read current LLM configuration dynamically from environment."""
    return {
        "provider": os.getenv("LLM_PROVIDER", "lmstudio").lower().strip(),
        "lmstudio_url": os.getenv("LMSTUDIO_URL", "http://localhost:1234/v1").rstrip("/"),
        "lmstudio_model": os.getenv("LMSTUDIO_MODEL", "oreal-deepseek-r1-distill-qwen-7b").strip(),
        "lmstudio_refiner_model": os.getenv("LMSTUDIO_REFINER_MODEL", "qwen/qwen3-4b-thinking-2507").strip(),
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen3:4b-thinking").strip(),
    }


def ensure_lmstudio_model_loaded(model_name: str) -> bool:
    """
    Ensure the requested model is active in LM Studio via the CLI.
    Enables clean sequential multi-model loading (Refiner -> Generator).
    """
    if not model_name:
        return False
    cli_path = LMS_CLI if os.path.exists(LMS_CLI) else (shutil.which("lms") or "")
    if not cli_path or not os.path.exists(cli_path):
        return True

    try:
        res = subprocess.run([cli_path, "ps"], capture_output=True, text=True, timeout=6)
        if res.returncode == 0:
            for line in res.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts and (model_name in parts[0] or parts[0] in model_name):
                    logger.info("[sequential_loader] Model %s is already active in LM Studio", model_name)
                    return True
    except Exception as e:
        logger.warning("[sequential_loader] Error querying `lms ps`: %s", e)

    logger.info("[sequential_loader] Sequentially loading %s into LM Studio...", model_name)
    try:
        t0 = time.time()
        load_res = subprocess.run(
            [cli_path, "load", model_name, "-y"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        logger.info(
            "[sequential_loader] `lms load %s` exited with code %s in %.2fs",
            model_name, load_res.returncode, time.time() - t0,
        )
        return load_res.returncode == 0
    except Exception as e:
        logger.warning("[sequential_loader] Failed to load %s via lms CLI: %s", model_name, e)
        return False


def strip_thinking_tags(text: str) -> str:
    """Remove any <think>...</think> reasoning blocks from LLM text."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    # Also strip unclosed trailing <think> if model truncated mid-thought
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()


class ThinkTagStreamSplitter:
    """
    Incremental parser separating `<think>...</think>` spans from answer content
    across arbitrary token/chunk boundaries.
    """

    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self) -> None:
        self.buffer: str = ""
        self.in_think: bool = False

    def _partial_prefix_index(self, text: str, tag: str) -> int:
        max_len = min(len(text), len(tag) - 1)
        for length in range(max_len, 0, -1):
            if text[-length:].lower() == tag[:length]:
                return len(text) - length
        return -1

    def feed(self, chunk: str) -> List[Tuple[str, str]]:
        if not chunk:
            return []
        self.buffer += chunk
        out: List[Tuple[str, str]] = []

        while self.buffer:
            lower_buf = self.buffer.lower()
            if not self.in_think:
                idx = lower_buf.find(self.OPEN_TAG)
                if idx != -1:
                    if idx > 0:
                        out.append(("content", self.buffer[:idx]))
                    self.buffer = self.buffer[idx + len(self.OPEN_TAG):]
                    self.in_think = True
                else:
                    partial_idx = self._partial_prefix_index(self.buffer, self.OPEN_TAG)
                    if partial_idx != -1:
                        if partial_idx > 0:
                            out.append(("content", self.buffer[:partial_idx]))
                        self.buffer = self.buffer[partial_idx:]
                    else:
                        out.append(("content", self.buffer))
                        self.buffer = ""
                    break
            else:
                idx = lower_buf.find(self.CLOSE_TAG)
                if idx != -1:
                    if idx > 0:
                        out.append(("reasoning", self.buffer[:idx]))
                    self.buffer = self.buffer[idx + len(self.CLOSE_TAG):]
                    self.in_think = False
                else:
                    partial_idx = self._partial_prefix_index(self.buffer, self.CLOSE_TAG)
                    if partial_idx != -1:
                        if partial_idx > 0:
                            out.append(("reasoning", self.buffer[:partial_idx]))
                        self.buffer = self.buffer[partial_idx:]
                    else:
                        out.append(("reasoning", self.buffer))
                        self.buffer = ""
                    break

        return out

    def flush(self) -> List[Tuple[str, str]]:
        if not self.buffer:
            return []
        kind = "reasoning" if self.in_think else "content"
        out = [(kind, self.buffer)]
        self.buffer = ""
        return out


def check_lmstudio_status() -> Dict[str, Any]:
    """Check whether LM Studio local server is reachable and list loaded/available models."""
    cfg = get_llm_config()
    url = cfg["lmstudio_url"]
    preferred = cfg["lmstudio_model"]
    try:
        resp = requests.get(f"{url}/models", timeout=3)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            all_ids = [m.get("id", "") for m in data if m.get("id")]
            chat_models = [m for m in all_ids if "embed" not in m.lower()]
            models = chat_models or all_ids
            active_model = preferred if preferred in models else (models[0] if models else preferred)
            return {
                "available": len(models) > 0,
                "server_reachable": True,
                "provider": "lmstudio",
                "active_model": active_model,
                "models": models,
            }
    except Exception:
        pass
    return {
        "available": False,
        "server_reachable": False,
        "provider": "lmstudio",
        "active_model": preferred,
        "models": [],
    }


def check_refiner_status() -> Dict[str, Any]:
    """Check whether Qwen prompt refiner is available (in LM Studio or Ollama)."""
    cfg = get_llm_config()
    refiner_model = cfg.get("lmstudio_refiner_model") or "qwen/qwen3-4b-thinking-2507"
    url = cfg["lmstudio_url"]
    try:
        resp = requests.get(f"{url}/models", timeout=3)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            models = [m.get("id", "") for m in data if m.get("id")]
            has_refiner = any(refiner_model in m or m in refiner_model for m in models)
            return {
                "available": has_refiner or len(models) > 0,
                "server_reachable": True,
                "provider": "lmstudio",
                "active_model": refiner_model,
                "models": models,
            }
    except Exception:
        pass

    # Fallback to Ollama if LM Studio is offline
    return check_ollama_status()


def check_ollama_status() -> Dict[str, Any]:
    """Check whether local Ollama is reachable and list installed models."""
    cfg = get_llm_config()
    url = cfg["ollama_url"]
    preferred = cfg["ollama_model"]
    try:
        resp = requests.get(f"{url}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
            active_model = preferred if preferred in models else (models[0] if models else preferred)
            return {
                "available": len(models) > 0,
                "server_reachable": True,
                "provider": "ollama",
                "active_model": active_model,
                "models": models,
            }
    except Exception:
        pass
    return {
        "available": False,
        "server_reachable": False,
        "provider": "ollama",
        "active_model": preferred,
        "models": [],
    }


def check_llm_health() -> Dict[str, Any]:
    """Check configured primary LLM provider (LM Studio first, Ollama fallback)."""
    cfg = get_llm_config()
    if cfg["provider"] == "ollama":
        ol = check_ollama_status()
        if ol["available"]:
            return ol
        lm = check_lmstudio_status()
        return lm if lm["available"] else ol

    lm = check_lmstudio_status()
    if lm["available"]:
        return lm
    ol = check_ollama_status()
    if ol["available"]:
        return ol
    return lm


# ─── Retry / truncation policy ───────────────────────────────────────────

#: Attempts against a single provider before giving up (or falling back).
RETRY_ATTEMPTS = 2

#: Linear backoff between attempts, in seconds.
RETRY_BACKOFF_SECONDS = 2

#: Extra tokens granted when retrying an output cut off by the max_tokens limit.
TRUNCATION_TOKEN_BUMP = 500


def _build_lmstudio_payload(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    stop: Optional[List[str]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if stop:
        payload["stop"] = stop
    return payload


def _build_ollama_payload(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    stop: Optional[List[str]],
) -> Dict[str, Any]:
    options: Dict[str, Any] = {
        "temperature": temperature,
        "num_predict": max_tokens,
        "num_ctx": 4096,
    }
    if stop:
        options["stop"] = stop
    return {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options,
    }


def _open_chat_stream(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
    stop: Optional[List[str]],
    cfg: Dict[str, str],
) -> requests.Response:
    """POST a streaming chat request to `provider` and validate the HTTP status."""
    if provider == "ollama":
        url = f"{cfg['ollama_url']}/api/chat"
        payload = _build_ollama_payload(model, messages, temperature, max_tokens, stop)
        label = "Ollama"
    else:
        url = f"{cfg['lmstudio_url']}/chat/completions"
        payload = _build_lmstudio_payload(model, messages, temperature, max_tokens, stop)
        label = "LM Studio"

    resp = requests.post(url, json=payload, stream=True, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"{label} HTTP {resp.status_code}: {resp.text[:300]}")
    resp.encoding = "utf-8"
    return resp


def _connect_with_retry(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
    stop: Optional[List[str]],
    cfg: Dict[str, str],
    attempts: int = RETRY_ATTEMPTS,
) -> requests.Response:
    """
    Open a streaming response, retrying `attempts` times with a fixed backoff.

    Retrying here is always safe: the connection is established before any token
    has been handed to the caller, so no partial output can be duplicated.
    """
    last_error: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            resp = _open_chat_stream(
                provider, model, messages, temperature, max_tokens, timeout, stop, cfg
            )
            logger.info(
                "[llm_client] %s:%s stream connected (attempt %d/%d)",
                provider, model, attempt, attempts,
            )
            return resp
        except (requests.RequestException, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "[llm_client] %s attempt %d/%d failed: %s", provider, attempt, attempts, exc
            )
            if attempt < attempts:
                time.sleep(RETRY_BACKOFF_SECONDS)

    raise RuntimeError(f"{provider} failed after {attempts} attempt(s): {last_error}")


def _alternate_provider(
    primary_provider: str,
    cfg: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """Return the other reachable local provider (Ollama fallback), or None."""
    status = check_lmstudio_status() if primary_provider == "ollama" else check_ollama_status()
    if not status.get("available"):
        return None
    return {"provider": status["provider"], "model": status["active_model"]}


def _iter_lmstudio_events(
    resp: requests.Response,
    splitter: ThinkTagStreamSplitter,
    state: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """Parse LM Studio / OpenAI SSE chunks, recording `finish_reason` in `state`."""
    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            state["saw_done_sentinel"] = True
            break
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0]

        finish_reason = choice.get("finish_reason")
        if finish_reason:
            state["finish_reason"] = finish_reason

        delta = choice.get("delta") or {}

        reasoning_piece = delta.get("reasoning_content") or ""
        if reasoning_piece:
            yield {"type": "reasoning", "text": reasoning_piece}

        content_piece = delta.get("content") or ""
        if content_piece:
            for kind, text in splitter.feed(content_piece):
                if text:
                    yield {"type": kind, "text": text}


def _iter_ollama_events(
    resp: requests.Response,
    splitter: ThinkTagStreamSplitter,
    state: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """Parse Ollama /api/chat NDJSON chunks, recording `done_reason` in `state`."""
    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        try:
            chunk = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        msg = chunk.get("message") or {}
        if msg.get("thinking"):
            yield {"type": "reasoning", "text": msg["thinking"]}
        content_piece = msg.get("content") or ""
        if content_piece:
            for kind, text in splitter.feed(content_piece):
                if text:
                    yield {"type": kind, "text": text}
        if chunk.get("done"):
            state["saw_done_sentinel"] = True
            state["finish_reason"] = (
                chunk.get("done_reason") or state.get("finish_reason") or "stop"
            )
            break


def stream_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 2500,
    timeout: int = 300,
    stop: Optional[List[str]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Stream completion events from LM Studio (`oreal-deepseek-r1-distill-qwen-7b`)
    or fallback to Ollama.
    Yields dicts:
      {"type": "model_info", "provider": ..., "model": ...}
      {"type": "reasoning", "text": ...}
      {"type": "content", "text": ...}
      {"type": "finish", "finish_reason": ..., "truncated": bool, ...}
    """
    health = check_llm_health()
    if not health["available"]:
        raise RuntimeError(
            "No local LLM server is available. Start LM Studio server (`lms server start`) "
            "and load `oreal-deepseek-r1-distill-qwen-7b`, or start Ollama."
        )

    cfg = get_llm_config()
    primary_provider = health["provider"]
    primary_model = health["active_model"]

    yield {"type": "model_info", "provider": primary_provider, "model": primary_model}

    splitter = ThinkTagStreamSplitter()

    # ── Connection phase: retryable, nothing has been streamed yet ───────
    provider, model = primary_provider, primary_model
    if provider == "lmstudio":
        try:
            ensure_lmstudio_model_loaded(model)
        except Exception as exc:
            logger.warning("[llm_client] ensure_lmstudio_model_loaded warning: %s", exc)

    try:
        resp = _connect_with_retry(
            provider, model, messages, temperature, max_tokens, timeout, stop, cfg
        )
    except RuntimeError as primary_error:
        # Second failure on the primary provider: try the alternative if reachable.
        fallback = _alternate_provider(primary_provider, cfg)
        if not fallback:
            raise
        provider, model = fallback["provider"], fallback["model"]
        logger.warning(
            "[llm_client] %s failed after %d attempt(s) (%s) — falling back to %s:%s",
            primary_provider, RETRY_ATTEMPTS, primary_error, provider, model,
        )
        resp = _connect_with_retry(
            provider, model, messages, temperature, max_tokens, timeout, stop, cfg, attempts=1
        )

    if provider != primary_provider or model != primary_model:
        # Tell consumers (and the UI) that the active model actually changed.
        yield {"type": "model_info", "provider": provider, "model": model}

    # ── Streaming phase: never retried, chunks may already be delivered ──
    state: Dict[str, Any] = {"finish_reason": None, "saw_done_sentinel": False, "stream_error": None}
    chunk_iter = (
        _iter_lmstudio_events(resp, splitter, state)
        if provider == "lmstudio"
        else _iter_ollama_events(resp, splitter, state)
    )

    try:
        for ev in chunk_iter:
            yield ev
    except (requests.RequestException, RuntimeError) as exc:
        # Mid-stream failure: retrying would duplicate emitted tokens, so flag instead.
        state["stream_error"] = str(exc)
        logger.warning("[llm_client] %s stream interrupted mid-flight: %s", provider, exc)
    finally:
        try:
            resp.close()
        except Exception:
            pass

    for kind, text in splitter.flush():
        if text:
            yield {"type": kind, "text": text}

    # ── finish_reason validation & truncation detection ──────────────────
    finish_reason = state.get("finish_reason")
    truncated = False
    if finish_reason == "length":
        truncated = True
        logger.warning("Output truncated at max_tokens limit (max_tokens=%d)", max_tokens)
    elif finish_reason is None:
        # Missing reason usually means the stream ended early (dropped connection).
        truncated = True
        logger.warning(
            "finish_reason missing from %s stream — treating output as potentially truncated",
            provider,
        )

    yield {
        "type": "finish",
        "finish_reason": finish_reason,
        "truncated": truncated,
        "provider": provider,
        "model": model,
        "max_tokens": max_tokens,
    }


def _collect_completion(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
    stop: Optional[List[str]],
) -> Tuple[str, Dict[str, Any]]:
    """Drain a stream into text plus finish_reason/truncation metadata."""
    parts: List[str] = []
    meta: Dict[str, Any] = {
        "truncated": True,
        "finish_reason": None,
        "provider": None,
        "model": None,
    }
    for ev in stream_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stop=stop,
    ):
        ev_type = ev.get("type")
        if ev_type == "content":
            parts.append(ev.get("text", ""))
        elif ev_type == "finish":
            meta["truncated"] = bool(ev.get("truncated", True))
            meta["finish_reason"] = ev.get("finish_reason")
        elif ev_type == "model_info":
            meta["provider"] = ev.get("provider")
            meta["model"] = ev.get("model")
    return strip_thinking_tags("".join(parts)), meta


def chat_completion_ex(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 2500,
    timeout: int = 180,
    stop: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Synchronous completion returning text plus truncation metadata.

    If the first pass stopped because `finish_reason == "length"`, one retry is made
    with `max_tokens + TRUNCATION_TOKEN_BUMP`. `truncated` stays True when even the
    retry was cut off, so downstream layers can reduce their confidence.
    """
    text, meta = _collect_completion(messages, temperature, max_tokens, timeout, stop)
    attempts = 1
    effective_max_tokens = max_tokens

    if meta["truncated"]:
        retry_tokens = max_tokens + TRUNCATION_TOKEN_BUMP
        logger.warning(
            "Output truncated at max_tokens limit (%d) — retrying once with max_tokens=%d",
            max_tokens, retry_tokens,
        )
        retry_text, retry_meta = _collect_completion(
            messages, temperature, retry_tokens, timeout, stop
        )
        attempts = 2
        effective_max_tokens = retry_tokens
        if (not retry_meta["truncated"]) or len(retry_text) > len(text):
            text, meta = retry_text, retry_meta
        if meta["truncated"]:
            logger.warning("Output still truncated after retry (max_tokens=%d)", retry_tokens)

    return {
        "text": text,
        "truncated": bool(meta["truncated"]),
        "finish_reason": meta.get("finish_reason"),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "attempts": attempts,
        "max_tokens": effective_max_tokens,
    }


def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 2500,
    timeout: int = 180,
    stop: Optional[List[str]] = None,
) -> str:
    """Synchronous completion returning clean text with `<think>` tags stripped."""
    return chat_completion_ex(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stop=stop,
    )["text"]
