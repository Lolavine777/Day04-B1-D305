from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.social_search.tool import search_tweets
from tools.timeline.tool import get_user_tweets


TAVILY_ITEMS = [
    {
        "title": "Indexed X post",
        "url": "https://x.com/example/status/123",
        "source": "x.com",
        "summary": "Publicly indexed post.",
    },
    {
        "title": "Unrelated result",
        "url": "https://example.com/article",
        "source": "example.com",
        "summary": "Must not be returned as an X post.",
    },
]


class TavilySocialToolTests(unittest.TestCase):
    @patch("tools.timeline.tool.web_search")
    def test_timeline_uses_tavily_and_filters_non_x_results(
        self,
        web_search,
    ) -> None:
        web_search.return_value = {"items": TAVILY_ITEMS}

        result = get_user_tweets("@example", limit=3)

        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["coverage"], "public_web_index")
        self.assertEqual(result["screenname"], "example")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["source"], "@example")
        web_search.assert_called_once_with(
            query="site:x.com/example/status recent posts by @example",
            topic="general",
            timeframe="month",
            max_results=3,
        )

    @patch("tools.social_search.tool.web_search")
    def test_latest_social_search_uses_short_tavily_window(
        self,
        web_search,
    ) -> None:
        web_search.return_value = {"items": TAVILY_ITEMS}

        result = search_tweets("AI agents", search_type="Latest", limit=2)

        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["search_type"], "Latest")
        self.assertEqual(len(result["items"]), 1)
        web_search.assert_called_once_with(
            query="site:x.com status AI agents",
            topic="general",
            timeframe="week",
            max_results=2,
        )

    @patch("tools.social_search.tool.web_search")
    def test_tavily_error_preserves_social_tool_identity(
        self,
        web_search,
    ) -> None:
        web_search.return_value = {
            "tool": "web_search",
            "error": "HTTPError",
            "message": "Tavily unavailable.",
        }

        result = search_tweets("AI")

        self.assertEqual(result["tool"], "search_tweets")
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["error"], "HTTPError")


if __name__ == "__main__":
    unittest.main()
