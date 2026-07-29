from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from tools.lookup.tool import web_search


def _is_x_status(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    return host in {"x.com", "twitter.com"} and "/status/" in parsed.path


def _social_items(
    items: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if _is_x_status(str(item.get("url") or ""))
    ][: int(limit or 5)]


def search_tweets(
    query: str = "",
    search_type: str = "Latest",
    limit: int = 5,
) -> dict[str, Any]:
    normalized_search_type = (
        search_type if search_type in {"Latest", "Top"} else "Latest"
    )
    timeframe = "week" if normalized_search_type == "Latest" else "month"
    result = web_search(
        query=f"site:x.com status {query}",
        topic="general",
        timeframe=timeframe,
        max_results=int(limit or 5),
    )
    if result.get("error"):
        return {
            "tool": "search_tweets",
            "provider": "tavily",
            "error": result["error"],
            "message": result.get("message", "Tavily search failed."),
        }
    return {
        "tool": "search_tweets",
        "provider": "tavily",
        "coverage": "public_web_index",
        "query": query,
        "search_type": normalized_search_type,
        "items": _social_items(result.get("items", []), limit),
    }
