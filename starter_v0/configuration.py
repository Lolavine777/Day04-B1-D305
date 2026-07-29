"""Credential configuration helpers for the Streamlit and CLI entrypoints."""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from typing import Any


PROVIDER_SECRET_NAMES = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
TOOL_SECRET_NAMES = ("TAVILY_API_KEY", "FIRECRAWL_API_KEY")
ALL_SECRET_NAMES = (
    *PROVIDER_SECRET_NAMES.values(),
    *TOOL_SECRET_NAMES,
)


def provider_secret_name(provider_name: str) -> str:
    return PROVIDER_SECRET_NAMES[provider_name]


def configured_secret_names(provider_name: str) -> tuple[str, ...]:
    return (provider_secret_name(provider_name), *TOOL_SECRET_NAMES)


def resolve_secrets(
    secret_source: Mapping[str, Any] | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, bool]:
    target = environ if environ is not None else os.environ
    for name in ALL_SECRET_NAMES:
        if target.get(name):
            continue
        if secret_source is None:
            continue
        try:
            value = secret_source.get(name)
        except FileNotFoundError:
            secret_source = None
            continue
        if isinstance(value, str) and value.strip():
            target[name] = value.strip()
    return {name: bool(target.get(name)) for name in ALL_SECRET_NAMES}
