from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 30


def err(
    tool: str,
    exc: Exception,
    *,
    service: str | None = None,
    secret_name: str | None = None,
) -> dict[str, Any]:
    if not isinstance(exc, requests.HTTPError):
        return {
            "tool": tool,
            "error": type(exc).__name__,
            "message": str(exc),
        }

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    service_name = service or "Upstream service"
    if status_code in {401, 403}:
        code = "authentication_failed"
        if secret_name:
            message = (
                f"{service_name} authentication failed. Replace "
                f"{secret_name} in Streamlit Secrets, save, and reboot the app."
            )
        else:
            message = f"{service_name} authentication failed."
    elif status_code == 429:
        code = "rate_limited"
        message = f"{service_name} rate limit reached. Wait before retrying."
    else:
        code = "upstream_http_error"
        status = f" with HTTP status {status_code}" if status_code else ""
        message = f"{service_name} request failed{status}."

    return {
        "tool": tool,
        "error": "HTTPError",
        "code": code,
        "status_code": status_code,
        "message": message,
    }


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def is_social_post(url: str, screenname: str | None = None) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    if host not in {"x.com", "twitter.com"} or len(parts) < 3 or parts[1].lower() != "status" or not parts[2]:
        return False
    return screenname is None or parts[0].lower() == screenname.lstrip("@").lower()


def fold_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def terms(text: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "is", "of", "on", "or", "the", "to",
        "ban", "bao", "can", "cho", "co", "cua", "duoc", "gi", "giup", "la", "lam", "minh", "mot", "nay",
        "nen", "the", "thi", "trong", "va", "ve", "voi",
    }
    folded = fold_text(text)
    return {term for term in re.findall(r"[a-z0-9]+", folded) if len(term) > 1 and term not in stopwords}
