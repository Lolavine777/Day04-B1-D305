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
    ][: max(1, min(int(limit or 5), 20))]


def search_tweets(
    query: str = "",
    search_type: str = "Latest",
    limit: int = 5,
) -> dict[str, Any]:
    normalized_search_type = (
        search_type if search_type in {"Latest", "Top"} else "Latest"
    )
    normalized_limit = max(1, min(int(limit or 5), 20))
    timeframe = "week" if normalized_search_type == "Latest" else "month"
    tavily_query = (
        f"site:x.com status {query}"
        if normalized_search_type == "Latest"
        else f"site:x.com status {query} popular posts"
    )
    tavily_limit = (
        normalized_limit
        if normalized_search_type == "Latest"
        else min(normalized_limit * 3, 20)
    )
    result = web_search(
        query=tavily_query,
        topic="general",
        timeframe=timeframe,
        max_results=tavily_limit,
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
        "items": _social_items(result.get("items", []), normalized_limit),
    }
