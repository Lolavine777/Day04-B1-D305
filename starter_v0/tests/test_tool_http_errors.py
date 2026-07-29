from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

import requests

from tools.fetch.tool import read_url
from tools.lookup.tool import web_search


def rejected_response(status_code: int, secret: str) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} failure for https://upstream.example/search?key={secret}",
        response=response,
    )
    return response


class ToolHttpErrorTests(unittest.TestCase):
    def test_tavily_401_is_actionable_and_safe(self) -> None:
        secret = "tavily-secret-value"
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(401, secret)),
        ):
            result = web_search(
                "Myanmar",
                topic="news",
                timeframe="day",
            )

        self.assertEqual(result["error"], "HTTPError")
        self.assertEqual(result.get("code"), "authentication_failed")
        self.assertEqual(result.get("status_code"), 401)
        self.assertIn("TAVILY_API_KEY", result["message"])
        self.assertIn("reboot", result["message"].lower())
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))

    def test_tavily_429_is_classified_without_leaking_url(self) -> None:
        secret = "tavily-secret-value"
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(429, secret)),
        ):
            result = web_search("AI")

        self.assertEqual(result.get("code"), "rate_limited")
        self.assertEqual(result.get("status_code"), 429)
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))

    def test_firecrawl_401_names_its_streamlit_secret(self) -> None:
        secret = "firecrawl-secret-value"
        with (
            patch.dict(os.environ, {"FIRECRAWL_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(401, secret)),
        ):
            result = read_url("https://example.com")

        self.assertEqual(result.get("code"), "authentication_failed")
        self.assertEqual(result.get("status_code"), 401)
        self.assertIn("FIRECRAWL_API_KEY", result["message"])
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))


if __name__ == "__main__":
    unittest.main()
