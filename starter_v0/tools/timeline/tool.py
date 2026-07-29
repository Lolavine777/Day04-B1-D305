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
        item_url = str(item.get("url") or "")
        if not _is_x_status(item_url):
            continue
        path_parts = [
            part
            for part in urlparse(item_url).path.split("/")
            if part
        ]
        if (
            len(path_parts) < 3
            or path_parts[0].casefold() != screenname.casefold()
            or path_parts[1].casefold() != "status"
        ):
            continue
        normalized = dict(item)
        normalized["source"] = source
        results.append(normalized)
    return results[: max(1, min(int(limit or 5), 20))]


def get_user_tweets(
    screenname: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    normalized_screenname = screenname.strip().lstrip("@")
    normalized_limit = max(1, min(int(limit or 5), 20))
    result = web_search(
        query=(
            f"site:x.com/{normalized_screenname}/status "
            f"recent posts by @{normalized_screenname}"
        ),
        topic="general",
        timeframe="month",
        max_results=normalized_limit,
    )
    if result.get("error"):
        return {
            "tool": "get_user_tweets",
            "provider": "tavily",
            "error": result["error"],
            "message": result.get("message", "Tavily search failed."),
            **{
                key: result[key]
                for key in ("code", "status_code")
                if key in result
            },
        }
    return {
        "tool": "get_user_tweets",
        "provider": "tavily",
        "coverage": "public_web_index",
        "screenname": normalized_screenname,
        "items": _timeline_items(
            result.get("items", []),
            normalized_screenname,
            normalized_limit,
        ),
    }
