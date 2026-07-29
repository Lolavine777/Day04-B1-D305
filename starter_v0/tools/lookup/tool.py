from __future__ import annotations

import os
import re
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


_X_TIMELINE_QUERY = re.compile(
    r"^site:x\.com/(?P<handle>[^/\s]+)/status\s+"
    r"recent posts by @(?P=handle)$",
    re.IGNORECASE,
)
_X_DOMAINS = ["x.com", "twitter.com"]


def web_search(
    query: str = "",
    topic: str = "general",
    timeframe: str | None = "week",
    max_results: int = 5,
    include_domains: list[str] | None = None,
) -> dict[str, Any]:
    try:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Missing TAVILY_API_KEY env var")
        requested_results = max(1, min(int(max_results or 5), 20))
        outgoing_query = query
        outgoing_domains = include_domains
        timeline_match = _X_TIMELINE_QUERY.match(query.strip())
        if timeline_match:
            handle = timeline_match.group("handle")
            outgoing_query = f'"https://x.com/{handle}/status"'
            outgoing_domains = outgoing_domains or _X_DOMAINS
        elif query.strip().lower().startswith("site:x.com status "):
            outgoing_domains = outgoing_domains or _X_DOMAINS

        body: dict[str, Any] = {
            "query": outgoing_query,
            "topic": topic,
            "max_results": requested_results,
            "search_depth": "basic",
        }
        if timeframe:
            body["time_range"] = timeframe
        if outgoing_domains:
            body["include_domains"] = outgoing_domains
        response = requests.post(
            "https://api.tavily.com/search",
            json=body,
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        items = [{
            "title": item.get("title"),
            "url": item.get("url"),
            "source": domain(item.get("url", "")),
            "summary": item.get("content"),
            "score": item.get("score"),
        } for item in data.get("results", [])]
        return {"tool": "web_search", "query": query, "topic": topic, "timeframe": timeframe, "items": items}
    except Exception as exc:
        return err(
            "web_search",
            exc,
            service="Tavily",
            secret_name="TAVILY_API_KEY",
        )
