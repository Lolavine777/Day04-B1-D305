from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT


def send_telegram(text: str = "", confirmed: bool = False) -> dict[str, Any]:
    if confirmed is not True:
        return {
            "tool": "send_telegram",
            "status": "needs_confirmation",
            "message": "Only send after the user explicitly confirms.",
        }
    if not isinstance(text, str) or not text.strip():
        return {
            "tool": "send_telegram",
            "status": "invalid_input",
            "message": "Telegram message text cannot be empty.",
        }
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return {
                "tool": "send_telegram",
                "status": "configuration_error",
                "error": "missing_credentials",
                "message": "Telegram credentials are not configured.",
            }
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            description = str(
                data.get("description") or "Telegram API rejected the message."
            ).replace(token, "[redacted]")
            return {
                "tool": "send_telegram",
                "status": "error",
                "error": "telegram_api_error",
                "message": description[:500],
            }
        return {
            "tool": "send_telegram",
            "status": "sent",
            "message_id": data.get("result", {}).get("message_id"),
        }
    except requests.RequestException as exc:
        return {
            "tool": "send_telegram",
            "status": "error",
            "error": type(exc).__name__,
            "message": "Telegram request failed.",
        }
    except Exception as exc:
        return {
            "tool": "send_telegram",
            "status": "error",
            "error": type(exc).__name__,
            "message": "Telegram message was not sent.",
        }

