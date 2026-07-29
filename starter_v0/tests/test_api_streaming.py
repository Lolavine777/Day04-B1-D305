from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import index as api_index
from providers.base import ModelResponse


app = api_index.app


class FakeStreamingProvider:
    default_model = "test/model"

    def complete_stream(
        self,
        *args,
        on_text_delta=None,
        **kwargs,
    ) -> ModelResponse:
        if on_text_delta is not None:
            on_text_delta("Hello")
            on_text_delta(" world")
        return ModelResponse(
            text="Hello world",
            usage={
                "prompt_tokens": 4,
                "completion_tokens": 2,
                "total_tokens": 6,
                "cost": 0.00001,
            },
        )


def parse_sse(body: str) -> list[tuple[str, dict]]:
    parsed: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block or block.startswith(":"):
            continue
        lines = block.splitlines()
        event_type = next(
            line.removeprefix("event: ")
            for line in lines
            if line.startswith("event: ")
        )
        data = next(
            line.removeprefix("data: ")
            for line in lines
            if line.startswith("data: ")
        )
        parsed.append((event_type, json.loads(data)))
    return parsed


class ApiStreamingTests(unittest.TestCase):
    def setUp(self) -> None:
        with api_index._RATE_LIMIT_LOCK:
            api_index._RATE_LIMIT_BUCKETS.clear()

    def test_chat_emits_valid_sse_lifecycle_and_usage(self) -> None:
        with patch("api.index.make_provider", return_value=FakeStreamingProvider()):
            with TestClient(app) as client:
                response = client.post(
                    "/api/chat",
                    json={
                        "messages": [{"role": "user", "content": "Hello"}],
                        "provider": "openrouter",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith("text/event-stream")
        )
        events = parse_sse(response.text)
        event_types = [event_type for event_type, _ in events]
        self.assertEqual(event_types[0], "connected")
        self.assertIn("run_started", event_types)
        self.assertEqual(event_types.count("assistant_delta"), 2)
        self.assertEqual(event_types[-1], "run_completed")

        run_ids = {
            payload["run_id"]
            for _, payload in events
            if "run_id" in payload
        }
        self.assertEqual(len(run_ids), 1)
        completed = events[-1][1]
        self.assertEqual(completed["assistant_text"], "Hello world")
        self.assertEqual(completed["usage"]["total_tokens"], 6)
        self.assertEqual(completed["cost_basis"], "provider")

    def test_chat_rejects_empty_messages_before_starting_a_stream(self) -> None:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"messages": []})

        self.assertEqual(response.status_code, 422)

    def test_chat_rejects_non_public_provider_and_unlisted_model(self) -> None:
        with TestClient(app) as client:
            provider_response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "provider": "openai",
                },
            )
            model_response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "provider": "openrouter",
                    "model": "anthropic/claude-opus-4",
                },
            )

        self.assertEqual(provider_response.status_code, 400)
        self.assertEqual(model_response.status_code, 400)

    def test_chat_rate_limit_returns_retry_after(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PUBLIC_RATE_LIMIT": "1",
                "PUBLIC_RATE_WINDOW_SECONDS": "60",
            },
            clear=False,
        ), patch(
            "api.index.make_provider",
            return_value=FakeStreamingProvider(),
        ):
            with TestClient(app) as client:
                first = client.post(
                    "/api/chat",
                    json={
                        "messages": [{"role": "user", "content": "Hello"}],
                    },
                )
                second = client.post(
                    "/api/chat",
                    json={
                        "messages": [{"role": "user", "content": "Again"}],
                    },
                )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertGreaterEqual(int(second.headers["retry-after"]), 1)


if __name__ == "__main__":
    unittest.main()
