from __future__ import annotations

import os
import unittest
from typing import get_type_hints
from unittest.mock import Mock, patch

import requests

from tools.social_search.tool import search_tweets
from tools.timeline.tool import get_user_tweets


def tavily_response(
    *,
    title: str = "A post",
    url: str = "https://x.com/sama/status/1",
    results: list[dict[str, object]] | None = None,
) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results or [{"title": title, "url": url, "content": "Post body", "score": 0.9}]}
    return response


class TavilySocialFallbackTests(unittest.TestCase):
    def test_timeline_uses_tavily_with_x_domains(self) -> None:
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=True),
            patch("requests.get", side_effect=AssertionError("RapidAPI GET must not be used")),
            patch("requests.post", return_value=tavily_response()) as post,
        ):
            result = get_user_tweets("sama", limit=3)

        self.assertNotIn("error", result)
        self.assertEqual(result["screenname"], "sama")
        self.assertEqual(result["items"][0]["url"], "https://x.com/sama/status/1")
        self.assertEqual(post.call_args.kwargs["json"]["query"], '"https://x.com/sama/status"')
        self.assertEqual(post.call_args.kwargs["json"]["include_domains"], ["x.com", "twitter.com"])
        self.assertEqual(post.call_args.kwargs["json"]["max_results"], 3)

    def test_timeline_rejects_other_handles_and_caps_tavily_limit(self) -> None:
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=True),
            patch(
                "requests.post",
                return_value=tavily_response(
                    results=[
                        {"title": "Wrong host", "url": "https://example.com/sama/status/1", "content": "Wrong", "score": 0.9},
                        {"title": "Wrong handle", "url": "https://x.com/other/status/2", "content": "Wrong", "score": 0.8},
                        {"title": "Expected", "url": "https://twitter.com/sama/status/3", "content": "Right", "score": 0.7},
                    ]
                ),
            ) as post,
        ):
            result = get_user_tweets("sama", limit=21)

        self.assertEqual([item["url"] for item in result["items"]], ["https://twitter.com/sama/status/3"])
        self.assertEqual(post.call_args.kwargs["json"]["max_results"], 20)

    def test_social_search_keeps_top_intent_in_tavily_query(self) -> None:
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=True),
            patch("requests.get", side_effect=AssertionError("RapidAPI GET must not be used")),
            patch(
                "requests.post",
                return_value=tavily_response(
                    results=[
                        {"title": "OpenAI profile", "url": "https://x.com/OpenAI", "content": "Profile", "score": 0.9},
                        {"title": "OpenAI post", "url": "https://x.com/OpenAI/status/1", "content": "Post", "score": 0.8},
                    ]
                ),
            ) as post,
        ):
            result = search_tweets("OpenAI", search_type="Top", limit=2)

        self.assertNotIn("error", result)
        self.assertEqual(result["search_type"], "Top")
        self.assertEqual(result["items"][0]["url"], "https://x.com/OpenAI/status/1")
        self.assertIn("OpenAI", post.call_args.kwargs["json"]["query"])
        self.assertIn("popular", post.call_args.kwargs["json"]["query"].lower())
        self.assertIn("status", post.call_args.kwargs["json"]["query"].lower())
        self.assertEqual(post.call_args.kwargs["json"]["include_domains"], ["x.com", "twitter.com"])
        self.assertEqual(post.call_args.kwargs["json"]["max_results"], 6)

    def test_social_search_rejects_non_x_status_urls(self) -> None:
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=True),
            patch(
                "requests.post",
                return_value=tavily_response(
                    results=[
                        {"title": "Wrong", "url": "https://example.com/user/status/1", "content": "Wrong", "score": 0.9},
                        {"title": "Expected", "url": "https://x.com/user/status/2", "content": "Right", "score": 0.8},
                    ]
                ),
            ),
        ):
            result = search_tweets("OpenAI", limit=2)

        self.assertEqual([item["url"] for item in result["items"]], ["https://x.com/user/status/2"])

    def test_public_type_hints_are_resolvable(self) -> None:
        self.assertEqual(get_type_hints(get_user_tweets)["limit"], int)
        self.assertEqual(get_type_hints(search_tweets)["limit"], int)

    def test_tavily_http_failure_is_reported_by_timeline(self) -> None:
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=True),
            patch("requests.get", side_effect=AssertionError("RapidAPI GET must not be used")),
            patch("requests.post", side_effect=requests.HTTPError("Tavily unavailable")),
        ):
            result = get_user_tweets("sama")

        self.assertEqual(result["tool"], "get_user_tweets")
        self.assertEqual(result["error"], "HTTPError")
        self.assertEqual(result["code"], "upstream_http_error")
        self.assertEqual(result["message"], "Tavily request failed.")
        self.assertNotIn("Tavily unavailable", repr(result))


if __name__ == "__main__":
    unittest.main()
