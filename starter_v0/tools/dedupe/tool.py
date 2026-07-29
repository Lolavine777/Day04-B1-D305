from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit


def _normalized_url(value: str) -> str | None:
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return None

    userinfo, separator, host_and_port = parsed.netloc.rpartition("@")
    if not separator:
        host_and_port = parsed.netloc

    if host_and_port.startswith("[") and "]" in host_and_port:
        bracket_index = host_and_port.index("]")
        host = host_and_port[: bracket_index + 1].lower()
        port = host_and_port[bracket_index + 1 :]
    else:
        host, port_separator, port_value = host_and_port.partition(":")
        host = host.lower()
        port = f"{port_separator}{port_value}" if port_separator else ""

    normalized_netloc = f"{userinfo}@{host}{port}" if separator else f"{host}{port}"
    normalized_path = parsed.path.rstrip("/")
    return urlunsplit(parsed._replace(netloc=normalized_netloc, path=normalized_path))


def dedupe_items(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source_items = items or []
    deduplicated_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in source_items:
        url = item.get("url")
        key: tuple[str, str] | None = None
        if isinstance(url, str) and url.strip():
            normalized_url = _normalized_url(url)
            if normalized_url is not None:
                key = ("url", normalized_url)
        if key is None:
            title = item.get("title")
            if isinstance(title, str) and title.strip():
                key = ("title", " ".join(title.split()).casefold())
        if key is not None:
            if key in seen_keys:
                continue
            seen_keys.add(key)
        deduplicated_items.append(dict(item))
    return {
        "tool": "dedupe",
        "items": deduplicated_items,
        "original_count": len(source_items),
        "deduplicated_count": len(deduplicated_items),
    }
