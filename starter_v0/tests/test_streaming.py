from __future__ import annotations

import unittest
from unittest.mock import patch

from chat import run_model_tool_loop
from providers.base import ModelResponse, ToolCall


class StreamingProvider:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = iter(responses)

    def complete_stream(self, *args, on_text_delta=None, **kwargs) -> ModelResponse:
        response = next(self.responses)
        if response.text and on_text_delta is not None:
            for fragment in response.text.split("|"):
                on_text_delta(fragment)
            response.text = response.text.replace("|", "")
        return response


class BufferedProvider:
    def complete(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(
            text="Buffered answer.",
            usage={
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
            },
        )


class StreamingLoopTests(unittest.TestCase):
    def test_streams_tool_lifecycle_and_aggregates_usage(self) -> None:
        provider = StreamingProvider(
            [
                ModelResponse(
                    tool_calls=[ToolCall(name="lookup", args={"query": "AI"})],
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                        "cost": 0.001,
                    },
                ),
                ModelResponse(
                    text="Final| answer.",
                    usage={
                        "prompt_tokens": 14,
                        "completion_tokens": 4,
                        "total_tokens": 18,
                        "cost": 0.002,
                    },
                ),
            ]
        )
        events: list[dict] = []

        with patch.dict(
            "chat.TOOL_FUNCTIONS",
            {"lookup": lambda **_: {"items": [{"title": "Result"}]}},
        ):
            result = run_model_tool_loop(
                provider=provider,
                messages=[{"role": "user", "content": "Research AI"}],
                tools=[],
                model=None,
                max_tool_rounds=3,
                event_callback=events.append,
            )

        self.assertEqual(result["assistant_text"], "Final answer.")
        self.assertEqual(result["usage"]["total_tokens"], 30)
        self.assertAlmostEqual(result["usage"]["cost"], 0.003)
        event_types = [event["type"] for event in events]
        self.assertLess(
            event_types.index("tool_started"),
            event_types.index("tool_completed"),
        )
        self.assertEqual(event_types[-1], "run_completed")
        deltas = [
            event["delta"]
            for event in events
            if event["type"] == "assistant_delta"
        ]
        self.assertEqual(deltas, ["Final", " answer."])

    def test_provider_without_streaming_emits_buffered_delta(self) -> None:
        events: list[dict] = []
        result = run_model_tool_loop(
            provider=BufferedProvider(),
            messages=[{"role": "user", "content": "Hello"}],
            tools=[],
            model=None,
            max_tool_rounds=1,
            event_callback=events.append,
        )

        delta = next(
            event for event in events if event["type"] == "assistant_delta"
        )
        completed = next(
            event for event in events if event["type"] == "model_completed"
        )
        self.assertEqual(delta["delta"], "Buffered answer.")
        self.assertEqual(completed["stream_mode"], "buffered")
        self.assertEqual(result["usage"]["total_tokens"], 5)

    def test_blocked_side_effect_tool_is_never_executed(self) -> None:
        provider = StreamingProvider(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            name="send",
                            args={"text": "private", "confirmed": True},
                        )
                    ]
                ),
                ModelResponse(text="Sending is disabled here."),
            ]
        )
        events: list[dict] = []

        def fail_if_called(**kwargs):
            raise AssertionError("blocked tool was executed")

        with patch.dict("chat.TOOL_FUNCTIONS", {"send": fail_if_called}):
            result = run_model_tool_loop(
                provider=provider,
                messages=[{"role": "user", "content": "Send it"}],
                tools=[],
                model=None,
                max_tool_rounds=2,
                event_callback=events.append,
                blocked_tools={"send"},
            )

        tool_event = result["tool_events"][0]
        self.assertEqual(tool_event["result"]["error"], "tool_disabled")
        self.assertEqual(tool_event["status"], "error")

    def test_cancellation_after_model_response_skips_tools(self) -> None:
        cancelled = False

        class CancellingProvider:
            def complete_stream(
                self,
                *args,
                on_text_delta=None,
                **kwargs,
            ) -> ModelResponse:
                nonlocal cancelled
                cancelled = True
                return ModelResponse(
                    tool_calls=[
                        ToolCall(name="lookup", args={"query": "AI"})
                    ]
                )

        def fail_if_called(**kwargs):
            raise AssertionError("tool ran after client cancellation")

        with patch.dict("chat.TOOL_FUNCTIONS", {"lookup": fail_if_called}):
            result = run_model_tool_loop(
                provider=CancellingProvider(),
                messages=[{"role": "user", "content": "Research AI"}],
                tools=[],
                model=None,
                max_tool_rounds=2,
                event_callback=lambda event: None,
                should_cancel=lambda: cancelled,
            )

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["tool_events"], [])


if __name__ == "__main__":
    unittest.main()
