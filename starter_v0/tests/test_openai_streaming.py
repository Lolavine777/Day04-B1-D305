from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

from providers.openai_provider import OpenAIProvider


def obj(**kwargs):
    return types.SimpleNamespace(**kwargs)


class FakeCompletions:
    def __init__(self, chunks):
        self.chunks = chunks
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return iter(self.chunks)


class OpenAIStreamingProviderTests(unittest.TestCase):
    def test_assembles_text_tool_arguments_and_final_usage(self) -> None:
        chunks = [
            obj(
                id="gen-1",
                model="test/model",
                usage=None,
                choices=[
                    obj(
                        delta=obj(
                            content="Working",
                            tool_calls=[
                                obj(
                                    index=0,
                                    id="call-1",
                                    function=obj(
                                        name="lookup",
                                        arguments='{"query":"',
                                    ),
                                )
                            ],
                        )
                    )
                ],
            ),
            obj(
                id="gen-1",
                model="test/model",
                usage=None,
                choices=[
                    obj(
                        delta=obj(
                            content=None,
                            tool_calls=[
                                obj(
                                    index=0,
                                    id=None,
                                    function=obj(
                                        name=None,
                                        arguments='AI"}',
                                    ),
                                )
                            ],
                        )
                    )
                ],
            ),
            obj(
                id="gen-1",
                model="test/model",
                usage={
                    "prompt_tokens": 7,
                    "completion_tokens": 3,
                    "total_tokens": 10,
                    "cost": 0.0002,
                },
                choices=[],
            ),
        ]
        completions = FakeCompletions(chunks)
        fake_module = types.SimpleNamespace(
            OpenAI=lambda **_: obj(
                chat=obj(completions=completions),
            )
        )
        deltas: list[str] = []
        provider = OpenAIProvider(
            api_key_env="TEST_OPENAI_KEY",
            base_url="https://example.test/v1",
            default_model="test/model",
        )

        with patch.dict(
            os.environ,
            {"TEST_OPENAI_KEY": "test-secret"},
            clear=False,
        ), patch.dict(sys.modules, {"openai": fake_module}):
            response = provider.complete_stream(
                [{"role": "user", "content": "Research AI"}],
                [],
                on_text_delta=deltas.append,
            )

        self.assertEqual(deltas, ["Working"])
        self.assertEqual(response.text, "Working")
        self.assertEqual(response.tool_calls[0].name, "lookup")
        self.assertEqual(response.tool_calls[0].args, {"query": "AI"})
        self.assertEqual(response.usage["total_tokens"], 10)
        self.assertEqual(response.usage["cost"], 0.0002)
        self.assertTrue(completions.kwargs["stream"])
        self.assertEqual(
            completions.kwargs["stream_options"],
            {"include_usage": True},
        )

    def test_openrouter_does_not_send_deprecated_stream_options(self) -> None:
        completions = FakeCompletions(
            [
                obj(
                    id="gen-2",
                    model="test/model",
                    usage=None,
                    choices=[obj(delta=obj(content="ok", tool_calls=[]))],
                )
            ]
        )
        fake_module = types.SimpleNamespace(
            OpenAI=lambda **_: obj(
                chat=obj(completions=completions),
            )
        )
        provider = OpenAIProvider(
            api_key_env="TEST_OPENROUTER_KEY",
            base_url="https://openrouter.ai/api/v1",
            default_model="test/model",
        )

        with patch.dict(
            os.environ,
            {"TEST_OPENROUTER_KEY": "test-secret"},
            clear=False,
        ), patch.dict(sys.modules, {"openai": fake_module}):
            provider.complete_stream(
                [{"role": "user", "content": "Hello"}],
                [],
            )

        self.assertNotIn("stream_options", completions.kwargs)


if __name__ == "__main__":
    unittest.main()
