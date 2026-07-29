from __future__ import annotations

import asyncio
from collections import deque
import json
import math
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTER_ROOT = PROJECT_ROOT / "starter_v0"
if str(STARTER_ROOT) not in sys.path:
    sys.path.insert(0, str(STARTER_ROOT))

from chat import run_model_tool_loop, trim_history  # noqa: E402
from guardrails import check_tool_call  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import load_tool_declarations, to_openai_tools  # noqa: E402
from versioning import artifact_version_dict, build_artifact_version  # noqa: E402


SYSTEM_PROMPT_PATH = STARTER_ROOT / "artifacts" / "system_prompt.md"
TOOLS_PATH = STARTER_ROOT / "artifacts" / "tools.yaml"
HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4
PUBLIC_BLOCKED_TOOLS = {"send"}
PUBLIC_PROVIDER = "openrouter"
DEFAULT_PUBLIC_MODEL = "openai/gpt-4o-mini"
DEFAULT_ARTIFACT_VERSION = (
    os.getenv("PUBLIC_ARTIFACT_VERSION", "v3").strip() or "v3"
)
DEFAULT_RATE_LIMIT = 8
DEFAULT_RATE_WINDOW_SECONDS = 60
MAX_RATE_LIMIT_BUCKETS = 4_096
PROVIDER_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=50_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    provider: Literal["openrouter", "openai", "anthropic", "gemini"] = "openrouter"
    model: str | None = Field(default=None, max_length=200)
    version: str = Field(
        default=DEFAULT_ARTIFACT_VERSION,
        min_length=1,
        max_length=32,
    )


app = FastAPI(title="Research Agent API", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _provider_ready(name: str) -> bool:
    return bool(os.getenv(PROVIDER_ENV[name]))


def _positive_int_env(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _allowed_public_models() -> set[str]:
    configured = os.getenv("PUBLIC_OPENROUTER_MODELS", "")
    allowed = {
        value.strip()
        for value in configured.split(",")
        if value.strip()
    }
    allowed.add(DEFAULT_PUBLIC_MODEL)
    return allowed


def _resolve_public_model(provider: str, requested_model: str | None) -> str:
    if provider != PUBLIC_PROVIDER:
        raise HTTPException(
            status_code=400,
            detail="The public workspace currently supports OpenRouter only.",
        )
    selected_model = requested_model or DEFAULT_PUBLIC_MODEL
    if selected_model not in _allowed_public_models():
        raise HTTPException(
            status_code=400,
            detail="That model is not enabled for the public workspace.",
        )
    return selected_model


def _client_rate_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first_hop = forwarded.split(",", 1)[0].strip()
        if first_hop:
            return first_hop[:128]
    if request.client and request.client.host:
        return request.client.host[:128]
    return "unknown-client"


def _enforce_rate_limit(request: Request) -> None:
    limit = _positive_int_env(
        "PUBLIC_RATE_LIMIT",
        DEFAULT_RATE_LIMIT,
        minimum=1,
        maximum=100,
    )
    window_seconds = _positive_int_env(
        "PUBLIC_RATE_WINDOW_SECONDS",
        DEFAULT_RATE_WINDOW_SECONDS,
        minimum=10,
        maximum=3_600,
    )
    now = time.monotonic()
    cutoff = now - window_seconds
    key = _client_rate_key(request)

    with _RATE_LIMIT_LOCK:
        if key not in _RATE_LIMIT_BUCKETS and len(_RATE_LIMIT_BUCKETS) >= MAX_RATE_LIMIT_BUCKETS:
            expired_keys = [
                bucket_key
                for bucket_key, timestamps in _RATE_LIMIT_BUCKETS.items()
                if not timestamps or timestamps[-1] <= cutoff
            ]
            for bucket_key in expired_keys:
                _RATE_LIMIT_BUCKETS.pop(bucket_key, None)
            if len(_RATE_LIMIT_BUCKETS) >= MAX_RATE_LIMIT_BUCKETS:
                key = "overflow-clients"

        timestamps = _RATE_LIMIT_BUCKETS.setdefault(key, deque())
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= limit:
            retry_after = max(
                1,
                math.ceil(window_seconds - (now - timestamps[0])),
            )
            raise HTTPException(
                status_code=429,
                detail="Too many research runs. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )
        timestamps.append(now)


def _safe_error_text(value: str) -> str:
    safe_value = value
    for env_name, env_value in os.environ.items():
        if (
            env_value
            and len(env_value) >= 4
            and any(marker in env_name.upper() for marker in SECRET_ENV_MARKERS)
        ):
            safe_value = safe_value.replace(env_value, "[redacted]")
    safe_value = re.sub(r"https?://\S+", "[redacted-url]", safe_value)
    safe_value = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*\S+",
        r"\1=[redacted]",
        safe_value,
    )
    return safe_value[:800]


def _sanitize_tool_errors(value: Any) -> Any:
    if isinstance(value, list):
        return [_sanitize_tool_errors(item) for item in value]
    if not isinstance(value, dict):
        return value

    has_error = bool(value.get("error"))
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, str) and (
            key == "error" or (has_error and key == "message")
        ):
            sanitized[key] = _safe_error_text(item)
        else:
            sanitized[key] = _sanitize_tool_errors(item)
    return sanitized


def _transport_event(event: dict[str, Any], run_id: str) -> dict[str, Any]:
    safe = _sanitize_tool_errors({"run_id": run_id, **event})
    if safe.get("type") == "tool_completed":
        result = safe.get("result")
        encoded = json.dumps(result, ensure_ascii=False, default=str)
        if len(encoded) > 40_000:
            safe["result"] = {
                "preview": encoded[:40_000],
                "truncated": True,
                "message": "The complete result stayed inside the agent loop.",
            }
    if safe.get("type") == "run_completed":
        usage = safe.get("usage") or {}
        safe["cost_basis"] = (
            "provider" if isinstance(usage.get("cost"), (int, float)) else "unavailable"
        )
    return safe


def _sse(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "message")
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _load_runtime(version: str, provider_name: str, model: str | None) -> dict[str, Any]:
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    public_declarations = [
        declaration
        for declaration in declarations
        if declaration.get("name") not in PUBLIC_BLOCKED_TOOLS
    ]
    provider = make_provider(provider_name)
    selected_model = model or getattr(provider, "default_model", None)
    artifact = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    return {
        "system_prompt": system_prompt,
        "tools": to_openai_tools(public_declarations),
        "provider": provider,
        "selected_model": selected_model,
        "artifact": artifact,
        "tool_count": len(public_declarations),
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "research-agent",
        "providers": {
            name: {"configured": _provider_ready(name)}
            for name in PROVIDER_ENV
        },
    }


@app.get("/api/config")
def config(
    provider: Literal["openrouter", "openai", "anthropic", "gemini"] = "openrouter",
    version: str = DEFAULT_ARTIFACT_VERSION,
) -> dict[str, Any]:
    selected_model = _resolve_public_model(provider, None)
    runtime = _load_runtime(version, provider, selected_model)
    return {
        "provider": provider,
        "provider_ready": _provider_ready(provider),
        "model": runtime["selected_model"],
        "tool_count": runtime["tool_count"],
        "blocked_tools": sorted(PUBLIC_BLOCKED_TOOLS),
        "artifact": artifact_version_dict(runtime["artifact"]),
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    selected_model = _resolve_public_model(payload.provider, payload.model)
    _enforce_rate_limit(request)
    run_id = uuid.uuid4().hex[:16]
    runtime = _load_runtime(payload.version, payload.provider, selected_model)
    client_messages = [message.model_dump() for message in payload.messages]
    model_messages = [
        {"role": "system", "content": runtime["system_prompt"]},
        *trim_history(client_messages, HISTORY_WINDOW),
    ]

    async def stream():
        event_loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        accepting_events = threading.Event()
        accepting_events.set()

        def publish(event: dict[str, Any]) -> None:
            if not accepting_events.is_set():
                return
            transported = _transport_event(event, run_id)
            try:
                event_loop.call_soon_threadsafe(queue.put_nowait, transported)
            except RuntimeError:
                accepting_events.clear()

        async def produce() -> None:
            try:
                await asyncio.to_thread(
                    run_model_tool_loop,
                    provider=runtime["provider"],
                    messages=model_messages,
                    tools=runtime["tools"],
                    model=selected_model,
                    max_tool_rounds=MAX_TOOL_ROUNDS,
                    event_callback=publish,
                    blocked_tools=PUBLIC_BLOCKED_TOOLS,
                    should_cancel=lambda: not accepting_events.is_set(),
                    tool_guard=check_tool_call,
                )
            except Exception as exc:
                publish(
                    {
                        "type": "run_failed",
                        "message": "The agent could not complete this request.",
                        "detail": _safe_error_text(
                            f"{type(exc).__name__}: {str(exc)}"
                        ),
                    }
                )
            finally:
                try:
                    event_loop.call_soon_threadsafe(queue.put_nowait, None)
                except RuntimeError:
                    pass

        metadata = {
            "type": "connected",
            "run_id": run_id,
            "provider": payload.provider,
            "model": runtime["selected_model"],
            "stream_mode": (
                "streaming"
                if hasattr(runtime["provider"], "complete_stream")
                else "buffered"
            ),
            "tool_count": runtime["tool_count"],
            "blocked_tools": sorted(PUBLIC_BLOCKED_TOOLS),
            "artifact": artifact_version_dict(runtime["artifact"]),
        }
        yield _sse(metadata)
        producer = asyncio.create_task(produce())

        try:
            while True:
                if await request.is_disconnected():
                    accepting_events.clear()
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    break
                yield _sse(event)
        finally:
            accepting_events.clear()
            if not producer.done():
                producer.cancel()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
