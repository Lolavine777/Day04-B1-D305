"""Product guardrails for the Research Agent UI.

Pre-guard : detect prompt-injection attempts, validate input format, rate limiting.
Post-guard: mask PII in output, block dangerous tool calls before execution.
Fallback  : rule-based default responses so the product keeps answering when the
            model backend is unavailable, always flagged with FALLBACK_NOTICE.

The eval path (run_eval.py -> agent.py) never imports this module, so guardrails
change product behavior without touching measured eval behavior.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable
from urllib.parse import urlparse

from providers.base import ToolCall

MAX_INPUT_CHARS = 4000
MAX_LIST_LIMIT = 20

URL_ARG_KEYS = ("url", "arxiv_url")
LIMIT_ARG_KEYS = ("limit", "max_results", "top_k", "max_pages")

FALLBACK_NOTICE = "⚠️ CHẾ ĐỘ DỰ PHÒNG: backend AI hiện không khả dụng, đây là phản hồi mặc định."

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_instructions", re.compile(
        r"(bỏ qua|phớt lờ|quên hết|vô hiệu hóa)\s+(mọi|toàn bộ|tất cả|các)?\s*"
        r"(hướng dẫn|chỉ dẫn|quy tắc|ràng buộc|lệnh)"
        r"|ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?)"
        r"|disregard\s+(your|the)\s+(instructions?|rules?)",
        re.IGNORECASE)),
    ("reveal_system_prompt", re.compile(
        r"(in ra|tiết lộ|hiển thị|cho\s+\S+\s*(xem|biết)|đọc)\s+.{0,40}"
        r"(system prompt|prompt hệ thống|hướng dẫn nội bộ|hướng dẫn hệ thống)"
        r"|(reveal|show|print|output|display)\s+.{0,40}(system prompt|your instructions)",
        re.IGNORECASE)),
    ("secret_exfiltration", re.compile(
        r"(cho\s+\S+\s*(xem|biết)|đưa|in ra|tiết lộ|gửi|reveal|show|print|leak)"
        r".{0,60}(api[\s_-]?key|secret|mật khẩu|password|credential|\.env|bot[\s_-]?token)",
        re.IGNORECASE)),
    ("fake_authority", re.compile(
        r"(tôi|mình|đây)\s+là\s+(quản trị viên|admin|administrator|developer|hệ thống|kỹ sư hệ thống)"
        r"|i\s+am\s+(the\s+)?(admin|administrator|system|developer)",
        re.IGNORECASE)),
    ("tool_forcing", re.compile(
        r"(gọi|hãy gọi|call|invoke|execute)\s+(ngay\s+)?(the\s+)?tool\s+\w+"
        r"|confirmed\s*=\s*true",
        re.IGNORECASE)),
]

SENSITIVE_CONTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("adult_content", re.compile(
        r"phim\s*(18\s*\+|người lớn|nóng|sex)"
        r"|khiêu dâm|đồi trụy"
        r"|web\s*sex|clip\s*(nóng|sex)"
        r"|\bporn\w*|\bxxx\b|\bjav\b|\bnsfw\b|\bhentai\b",
        re.IGNORECASE)),
    ("drug_procurement", re.compile(
        r"(mua|bán|tìm mua|kiếm|order|đặt)\s+.{0,25}(ma túy|cần sa|heroin|thuốc lắc|\bmeth\b|cỏ mỹ)"
        r"|(ma túy|cần sa|heroin|thuốc lắc)\s*.{0,12}(mua|bán)\s*ở đâu",
        re.IGNORECASE)),
    ("weapon_instructions", re.compile(
        r"(cách|hướng dẫn|chỉ\s+\S+\s*cách)\s+.{0,15}(chế|chế tạo|làm|tự làm)\s+.{0,15}(bom|thuốc nổ|súng|vũ khí)"
        r"|(mua|bán)\s+.{0,15}(súng|vũ khí)\b",
        re.IGNORECASE)),
]

PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "[token đã ẩn]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[api key đã ẩn]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email đã ẩn]"),
    (re.compile(r"(?<![\w/.])(?:\+84|0)\d{9,10}(?![\w/])"), "[số điện thoại đã ẩn]"),
    (re.compile(r"(?<![\w/.])\d{12,16}(?![\w/])"), "[số nhạy cảm đã ẩn]"),
]

PRIVATE_HOST_PATTERN = re.compile(
    r"^(localhost|0\.0\.0\.0|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+"
    r"|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|169\.254\.\d+\.\d+)$",
    re.IGNORECASE,
)

EXTERNAL_ACTION_PATTERN = re.compile(
    r"(?:\b(?:send|post|publish)\b|\b(?:gửi|đăng|đăng tải|xuất bản)\b).{0,80}\b(?:telegram|channel|kênh)\b"
    r"|\b(?:telegram|channel|kênh)\b.{0,80}(?:\b(?:send|post|publish)\b|\b(?:gửi|đăng|đăng tải|xuất bản)\b)",
    re.IGNORECASE,
)


# ---------------- Pre-guard ----------------

def detect_injection(text: str) -> list[str]:
    """Return the labels of injection patterns found in the user input."""
    return [label for label, pattern in INJECTION_PATTERNS if pattern.search(text)]


def detect_sensitive_content(text: str) -> list[str]:
    """Return labels of sensitive-content categories found in the user input.

    Deliberately narrow: consuming/procuring NSFW, drugs, or weapons is blocked,
    while news research ABOUT those topics (crime coverage, policy news) passes.
    Keyword-based, lab-grade — a real product would add a moderation classifier.
    """
    return [label for label, pattern in SENSITIVE_CONTENT_PATTERNS if pattern.search(text)]


def validate_input(text: str, max_chars: int = MAX_INPUT_CHARS) -> tuple[bool, str | None]:
    stripped = text.strip()
    if not stripped:
        return False, "Yêu cầu trống. Bạn hãy nhập một câu hỏi research cụ thể nhé."
    if len(stripped) > max_chars:
        return False, f"Yêu cầu quá dài (tối đa {max_chars} ký tự). Bạn hãy rút gọn lại nhé."
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in stripped):
        return False, "Yêu cầu chứa ký tự điều khiển không hợp lệ."
    return True, None


class RateLimiter:
    """Sliding-window rate limiter, one instance per conversation/session."""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._timestamps: list[float] = []

    def allow(self) -> tuple[bool, float]:
        now = self.clock()
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) >= self.max_requests:
            retry_after = self._timestamps[0] + self.window_seconds - now
            return False, max(retry_after, 0.1)
        self._timestamps.append(now)
        return True, 0.0


def pre_guard(text: str, rate_limiter: RateLimiter | None = None) -> dict[str, Any]:
    """Run all input guards. Returns {"allowed", "reason", "message"}."""
    ok, error = validate_input(text)
    if not ok:
        return {"allowed": False, "reason": "invalid_input", "message": error}

    if rate_limiter is not None:
        allowed, retry_after = rate_limiter.allow()
        if not allowed:
            return {
                "allowed": False,
                "reason": "rate_limited",
                "message": f"Bạn gửi yêu cầu quá nhanh. Vui lòng thử lại sau {retry_after:.0f} giây.",
            }

    matches = detect_injection(text)
    if matches:
        return {
            "allowed": False,
            "reason": "injection_detected",
            "message": (
                "Yêu cầu có dấu hiệu prompt injection ("
                + ", ".join(matches)
                + ") nên không được xử lý. Bạn hãy diễn đạt lại thành một câu hỏi research thông thường nhé."
            ),
        }

    sensitive = detect_sensitive_content(text)
    if sensitive:
        return {
            "allowed": False,
            "reason": "sensitive_content",
            "message": (
                "Yêu cầu chứa nội dung nhạy cảm ("
                + ", ".join(sensitive)
                + ") nằm ngoài phạm vi của research agent nên không được xử lý. "
                "Mình chỉ hỗ trợ tìm tin tức, bài mạng xã hội và tóm tắt nguồn công khai."
            ),
        }

    return {"allowed": True, "reason": None, "message": None}


# ---------------- Post-guard ----------------

def mask_pii(text: str) -> str:
    masked = text
    for pattern, replacement in PII_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def _is_private_url(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        return True
    host = (parsed.hostname or "").strip("[]")
    return bool(PRIVATE_HOST_PATTERN.match(host)) if host else True


def check_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Verdict for one tool call: {"allowed", "reason", "args" (sanitized)}."""
    from tools import TOOL_FUNCTIONS

    if name not in TOOL_FUNCTIONS:
        return {"allowed": False, "reason": f"unknown tool {name!r}", "args": args}

    if name == "send" and args.get("confirmed"):
        return {
            "allowed": False,
            "reason": "send với confirmed=true bị chặn: chỉ người dùng xác nhận trực tiếp mới được gửi.",
            "args": args,
        }

    for key in URL_ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value and "arxiv" not in name and _is_private_url(value):
            return {
                "allowed": False,
                "reason": f"URL không hợp lệ hoặc trỏ vào mạng nội bộ: {key}={value!r}",
                "args": args,
            }

    sanitized = dict(args)
    for key in LIMIT_ARG_KEYS:
        value = sanitized.get(key)
        if isinstance(value, int) and value > MAX_LIST_LIMIT:
            sanitized[key] = MAX_LIST_LIMIT
    return {"allowed": True, "reason": None, "args": sanitized}


def enforce_confirmation_boundary(messages: list[dict[str, str]], call: ToolCall) -> ToolCall:
    """Require a yes/no clarification for a direct Telegram action request."""
    latest_user = next(
        (message.get("content", "") for message in reversed(messages) if message.get("role") == "user"),
        "",
    )
    if call.name != "clarify" or not EXTERNAL_ACTION_PATTERN.search(latest_user):
        return call
    args = dict(call.args)
    args["response_type"] = "yes_no"
    return ToolCall(name=call.name, args=args)


# ---------------- Fallback ----------------

class FallbackProvider:
    """Stand-in provider used when the real one cannot be constructed.

    Every completion raises, which routes each turn through the fallback
    response path, so the UI keeps working with default answers.
    """

    default_model = None

    def complete(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("backend unavailable (fallback mode)")


def fallback_hint(error_text: str) -> str:
    """Turn a (sanitized) backend error into an actionable hint for the UI banner."""
    lowered = error_text.lower()
    if "missing api key" in lowered or "api key env var" in lowered:
        return (
            "Nguyên nhân: thiếu API key của provider. "
            "Local: tạo starter_v0/.env từ .env.example. "
            "Streamlit Cloud: đặt OPENROUTER_API_KEY ở cấp root trong "
            "App settings > Secrets, rồi reboot app."
        )
    if any(word in lowered for word in ("connection", "timeout", "timed out", "max retries", "getaddrinfo")):
        return "Nguyên nhân: lỗi mạng khi gọi provider. Kiểm tra kết nối internet rồi thử lại."
    if any(word in lowered for word in ("401", "unauthorized", "403", "invalid api key")):
        return "Nguyên nhân: API key bị từ chối. Kiểm tra lại giá trị key trong .env."
    if any(word in lowered for word in ("429", "rate limit", "quota", "insufficient")):
        return "Nguyên nhân: provider hết quota hoặc bị rate limit. Chờ một lúc hoặc đổi key/provider."
    return "Nguyên nhân: backend gặp lỗi không xác định. Xem chi tiết trong transcript."


def fallback_response(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("làm được", "bạn là gì", "khả năng", "help", "trợ giúp")):
        body = (
            "Bình thường mình là research agent với các tool: tìm tin tức web, tìm bài mạng xã hội, "
            "lấy timeline tài khoản, đọc URL và soạn bản tin. Khi backend hoạt động trở lại, "
            "bạn hỏi lại là mình chạy đầy đủ nhé."
        )
    elif any(word in lowered for word in ("xin chào", "chào bạn", "hello", "hi ")) or lowered.strip() in ("hi", "chào"):
        body = "Chào bạn! Hiện mình chưa gọi được model backend, nhưng bạn cứ để lại câu hỏi và thử lại sau ít phút."
    elif "http://" in lowered or "https://" in lowered:
        body = (
            "Mình đã nhận được link nhưng chưa thể đọc nội dung lúc này. "
            "Bạn giữ lại link và thử lại khi hệ thống báo hoạt động bình thường nhé."
        )
    elif any(word in lowered for word in ("tweet", "twitter", "mạng xã hội", "x.com")):
        body = (
            "Mình chưa thể tìm bài mạng xã hội lúc này. Bạn có thể tự tìm tạm trên x.com "
            "và quay lại khi backend hoạt động."
        )
    elif any(word in lowered for word in ("tin tức", "tin ", "news", "bản tin")):
        body = (
            "Mình chưa thể tra cứu tin tức trực tiếp lúc này. Bạn có thể xem tạm các nguồn quen thuộc "
            "(VnExpress, TechCrunch...) và thử lại sau — yêu cầu của bạn không bị mất."
        )
    else:
        body = "Mình đã ghi nhận yêu cầu nhưng chưa xử lý được lúc này. Bạn thử lại sau ít phút nhé."
    return f"{FALLBACK_NOTICE}\n\n{body}"
