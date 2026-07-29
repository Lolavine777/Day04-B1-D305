from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_conversation, run_turn, sanitize_error_text
from providers.base import ModelResponse, ToolCall


class FakeProvider:
    default_model = "fake-model"

    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = iter(responses)
        self.requests: list[list[dict[str, str]]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *args,
        **kwargs,
    ) -> ModelResponse:
        self.requests.append(messages)
        return next(self.responses)


class AppLoopTests(unittest.TestCase):
    def make_conversation(
        self,
        provider: FakeProvider,
        transcript_dir: Path,
    ) -> dict:
        conversation = create_conversation(
            "openai",
            None,
            "test",
            provider_factory=lambda _: provider,
        )
        conversation["transcript_path"] = (
            transcript_dir / "test.transcript.json"
        )
        return conversation

    def test_normal_research_turn_persists_tool_trace(self) -> None:
        provider = FakeProvider(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            name="lookup",
                            args={"query": "AI news", "max_results": 2},
                        )
                    ]
                ),
                ModelResponse(text="Two AI updates with sources."),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation = self.make_conversation(provider, Path(temp_dir))
            fake_lookup = lambda **_: {
                "items": [
                    {
                        "title": "AI update",
                        "url": "https://example.com/ai",
                    }
                ]
            }
            with patch.dict("chat.TOOL_FUNCTIONS", {"lookup": fake_lookup}):
                turn = run_turn(
                    conversation,
                    "Find two AI updates",
                    provider_factory=lambda _: provider,
                )

            self.assertEqual(turn["status"], "answered")
            self.assertEqual(turn["tool_events"][0]["tool"], "lookup")
            transcript_text = conversation["transcript_path"].read_text(
                encoding="utf-8"
            )
            self.assertIn('"artifact_version"', transcript_text)
            self.assertIn('"tool_events"', transcript_text)

    def test_clarification_turn_waits_for_user(self) -> None:
        provider = FakeProvider(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            name="clarify",
                            args={
                                "question": "Which account?",
                                "response_type": "text",
                            },
                        )
                    ]
                )
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation = self.make_conversation(provider, Path(temp_dir))
            turn = run_turn(
                conversation,
                "Summarize recent posts",
                provider_factory=lambda _: provider,
            )

        self.assertEqual(turn["status"], "waiting_for_user")
        self.assertEqual(turn["assistant_text"], "Which account?")

    def test_sensitive_action_requests_confirmation_without_send(self) -> None:
        provider = FakeProvider(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            name="clarify",
                            args={
                                "question": "Send this to Telegram?",
                                "response_type": "yes_no",
                            },
                        )
                    ]
                )
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation = self.make_conversation(provider, Path(temp_dir))
            turn = run_turn(
                conversation,
                "Send the digest to Telegram",
                provider_factory=lambda _: provider,
            )

        self.assertEqual(turn["status"], "waiting_for_user")
        self.assertEqual(turn["tool_events"][0]["tool"], "clarify")
        self.assertNotIn("send", [event["tool"] for event in turn["tool_events"]])

    def test_second_turn_receives_session_history(self) -> None:
        provider = FakeProvider(
            [
                ModelResponse(text="First answer."),
                ModelResponse(text="Second answer."),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            conversation = self.make_conversation(provider, Path(temp_dir))
            run_turn(
                conversation,
                "First question",
                provider_factory=lambda _: provider,
            )
            run_turn(
                conversation,
                "Follow-up question",
                provider_factory=lambda _: provider,
            )

        second_request = provider.requests[1]
        self.assertEqual(
            [message["role"] for message in second_request],
            ["system", "user", "assistant", "user"],
        )
        self.assertEqual(second_request[-2]["content"], "First answer.")
        self.assertEqual(len(conversation["transcript"]["turns"]), 2)

    def test_provider_error_redacts_urls_and_keys(self) -> None:
        safe = sanitize_error_text(
            "Request failed at https://api.example.test/path?api_key=secret "
            "token=another-secret"
        )
        self.assertNotIn("https://", safe)
        self.assertNotIn("another-secret", safe)
        self.assertIn("[redacted-url]", safe)


if __name__ == "__main__":
    unittest.main()
