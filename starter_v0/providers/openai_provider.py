from __future__ import annotations

import json
import os
from typing import Any, Callable

from providers.base import ModelResponse, ToolCall


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        return dumped if isinstance(dumped, dict) else {}
    legacy_dict = getattr(value, "dict", None)
    if callable(legacy_dict):
        dumped = legacy_dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_usage(value: Any) -> dict[str, int | float]:
    raw = _as_dict(value)
    prompt_details = _as_dict(raw.get("prompt_tokens_details"))
    completion_details = _as_dict(raw.get("completion_tokens_details"))
    candidates = {
        "prompt_tokens": raw.get("prompt_tokens"),
        "completion_tokens": raw.get("completion_tokens"),
        "total_tokens": raw.get("total_tokens"),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "cost": raw.get("cost"),
    }
    normalized: dict[str, int | float] = {}
    for key, candidate in candidates.items():
        number = _number(candidate)
        if number is not None:
            normalized[key] = number
    return normalized


class OpenAIProvider:
    """OpenAI Chat Completions provider with normalized tool_calls output."""

    def __init__(
        self,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
        max_tokens: int | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.default_model = default_model
        self.max_tokens = max_tokens

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
    ) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install live provider dependency first: pip install openai") from exc

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.api_key_env}")

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for call in msg.tool_calls or []:
            args = json.loads(call.function.arguments or "{}")
            calls.append(ToolCall(name=call.function.name, args=args))
        return ModelResponse(
            text=msg.content,
            tool_calls=calls,
            usage=normalize_usage(getattr(resp, "usage", None)),
            raw=resp,
        )

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ModelResponse:
        """Stream text while assembling a normalized final response."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install live provider dependency first: pip install openai") from exc

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.api_key_env}")

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        selected_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        # OpenRouter now includes usage automatically. OpenAI still uses this flag.
        if not (self.base_url and "openrouter.ai" in self.base_url):
            kwargs["stream_options"] = {"include_usage": True}

        text_parts: list[str] = []
        calls_by_index: dict[int, dict[str, str]] = {}
        usage: dict[str, int | float] = {}
        response_id: str | None = None
        response_model: str | None = None

        for chunk in client.chat.completions.create(**kwargs):
            response_id = getattr(chunk, "id", None) or response_id
            response_model = getattr(chunk, "model", None) or response_model
            chunk_usage = normalize_usage(getattr(chunk, "usage", None))
            if chunk_usage:
                usage = chunk_usage

            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                text_parts.append(content)
                if on_text_delta is not None:
                    on_text_delta(content)

            for partial_call in getattr(delta, "tool_calls", None) or []:
                index = int(getattr(partial_call, "index", 0) or 0)
                accumulator = calls_by_index.setdefault(
                    index,
                    {"id": "", "name": "", "arguments": ""},
                )
                call_id = getattr(partial_call, "id", None)
                if call_id:
                    accumulator["id"] += call_id
                function = getattr(partial_call, "function", None)
                if function is None:
                    continue
                name_fragment = getattr(function, "name", None)
                args_fragment = getattr(function, "arguments", None)
                if name_fragment:
                    accumulator["name"] += name_fragment
                if args_fragment:
                    accumulator["arguments"] += args_fragment

        calls: list[ToolCall] = []
        for index in sorted(calls_by_index):
            partial = calls_by_index[index]
            raw_arguments = partial["arguments"] or "{}"
            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError:
                args = {
                    "_raw_arguments": raw_arguments,
                    "_parse_error": "invalid_tool_arguments_json",
                }
            calls.append(ToolCall(name=partial["name"], args=args))

        return ModelResponse(
            text="".join(text_parts) or None,
            tool_calls=calls,
            usage=usage,
            raw={
                "id": response_id,
                "model": response_model or selected_model,
                "usage": usage,
            },
        )
