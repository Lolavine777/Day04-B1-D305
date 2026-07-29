from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

import requests

from tools.send.tool import send_telegram


class SendTelegramTests(unittest.TestCase):
    def test_unconfirmed_request_never_calls_telegram(self) -> None:
        with patch("tools.send.tool.requests.post") as post:
            result = send_telegram("Hello", confirmed=False)

        self.assertEqual(result["status"], "needs_confirmation")
        self.assertFalse(post.called)

    def test_non_boolean_confirmation_never_calls_telegram(self) -> None:
        with patch("tools.send.tool.requests.post") as post:
            result = send_telegram("Hello", confirmed="true")  # type: ignore[arg-type]

        self.assertEqual(result["status"], "needs_confirmation")
        self.assertFalse(post.called)

    def test_http_error_never_exposes_bot_token(self) -> None:
        token = "123456:super-secret-token"
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError(
            f"401 Client Error for url: https://api.telegram.org/bot{token}/sendMessage"
        )

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": token,
                    "TELEGRAM_CHAT_ID": "-100123",
                },
                clear=True,
            ),
            patch("tools.send.tool.requests.post", return_value=response),
        ):
            result = send_telegram("Hello", confirmed=True)

        self.assertNotIn(token, json.dumps(result))

    def test_success_sends_plain_text_and_returns_message_id(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "ok": True,
            "result": {"message_id": 42},
        }

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": "test-token",
                    "TELEGRAM_CHAT_ID": "-100123",
                },
                clear=True,
            ),
            patch("tools.send.tool.requests.post", return_value=response) as post,
        ):
            result = send_telegram("Use _ and * literally", confirmed=True)

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], 42)
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "chat_id": "-100123",
                "text": "Use _ and * literally",
            },
        )

    def test_empty_text_is_rejected_without_network_call(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": "test-token",
                    "TELEGRAM_CHAT_ID": "-100123",
                },
                clear=True,
            ),
            patch("tools.send.tool.requests.post") as post,
        ):
            result = send_telegram("   ", confirmed=True)

        self.assertEqual(result["status"], "invalid_input")
        self.assertFalse(post.called)

    def test_non_string_text_is_rejected_without_network_call(self) -> None:
        with patch("tools.send.tool.requests.post") as post:
            result = send_telegram(None, confirmed=True)  # type: ignore[arg-type]

        self.assertEqual(result["status"], "invalid_input")
        self.assertFalse(post.called)

    def test_missing_credentials_returns_configuration_error_without_network(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("tools.send.tool.requests.post") as post,
        ):
            result = send_telegram("Hello", confirmed=True)

        self.assertEqual(result["status"], "configuration_error")
        self.assertEqual(result["error"], "missing_credentials")
        self.assertFalse(post.called)

    def test_telegram_api_rejection_is_not_reported_as_sent(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: chat not found",
        }

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": "test-token",
                    "TELEGRAM_CHAT_ID": "-100123",
                },
                clear=True,
            ),
            patch("tools.send.tool.requests.post", return_value=response),
        ):
            result = send_telegram("Hello", confirmed=True)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "telegram_api_error")
        self.assertEqual(result["message"], "Bad Request: chat not found")


if __name__ == "__main__":
    unittest.main()
