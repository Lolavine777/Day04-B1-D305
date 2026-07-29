from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from tools.lookup.tool import web_search


def _is_x_status(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    return host in {"x.com", "twitter.com"} and "/status/" in parsed.path


def _timeline_items(
    items: list[dict[str, Any]],
    screenname: str,
    limit: int,
) -> list[dict[str, Any]]:
    source = f"@{screenname}" if screenname else "x.com"
    results: list[dict[str, Any]] = []
    for item in items:
        if not _is_x_status(str(item.get("url") or "")):
            continue
        normalized = dict(item)
        normalized["source"] = source
        results.append(normalized)
    return results[: int(limit or 5)]


def get_user_tweets(
    screenname: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    normalized_screenname = screenname.strip().lstrip("@")
    result = web_search(
        query=(
            f"site:x.com/{normalized_screenname}/status "
            f"recent posts by @{normalized_screenname}"
        ),
        topic="general",
        timeframe="month",
        max_results=int(limit or 5),
    )
    if result.get("error"):
        return {
            "tool": "get_user_tweets",
            "provider": "tavily",
            "error": result["error"],
            "message": result.get("message", "Tavily search failed."),
        }
    return {
        "tool": "get_user_tweets",
        "provider": "tavily",
        "coverage": "public_web_index",
        "screenname": normalized_screenname,
        "items": _timeline_items(
            result.get("items", []),
            normalized_screenname,
            limit,
        ),
    }
