from __future__ import annotations

from typing import Any

from tools._shared import is_social_post
from tools.lookup.tool import web_search


def search_tweets(query: str = "", search_type: str = "Latest", limit: int = 5) -> dict[str, Any]:
    ranking = "popular posts" if search_type == "Top" else "recent posts"
    requested_limit = max(int(limit or 5), 1)
    result = web_search(
        query=f"{query} {ranking} status x.com",
        topic="general",
        timeframe=None,
        max_results=min(max(requested_limit * 3, 5), 20),
        include_domains=["x.com", "twitter.com"],
    )
    if "error" in result:
        return {"tool": "search_tweets", "error": result["error"], "message": result["message"]}
    items = [item for item in result["items"] if is_social_post(item.get("url") or "")]
    return {"tool": "search_tweets", "query": query, "search_type": search_type, "items": items[:requested_limit]}
