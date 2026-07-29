from __future__ import annotations

from typing import Any

from tools._shared import is_social_post
from tools.lookup.tool import web_search


def get_user_tweets(screenname: str = "", limit: int = 5) -> dict[str, Any]:
    requested_limit = max(int(limit or 5), 1)
    result = web_search(
        query=f'"https://x.com/{screenname}/status"',
        topic="general",
        timeframe=None,
        max_results=min(requested_limit, 20),
        include_domains=["x.com", "twitter.com"],
    )
    if "error" in result:
        return {"tool": "get_user_tweets", "error": result["error"], "message": result["message"]}
    items = [item for item in result["items"] if is_social_post(item.get("url") or "", screenname)]
    return {"tool": "get_user_tweets", "screenname": screenname, "items": items[:requested_limit]}
