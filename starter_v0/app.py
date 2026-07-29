from __future__ import annotations

import html
import json
import os
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import streamlit as st

import guardrails
from chat import (
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from configuration import (
    PROVIDER_SECRET_NAMES,
    configured_secret_names,
    resolve_secrets,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
SYSTEM_PROMPT_PATH = ROOT / "artifacts" / "system_prompt.md"
TOOLS_PATH = ROOT / "artifacts" / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SUPPORTED_PROVIDERS = ("openrouter", "openai", "anthropic", "gemini")
PROVIDER_ENV_VARS = PROVIDER_SECRET_NAMES
QUICK_PROMPTS = (
    ("AI today", "Find 3 important AI updates today and summarize them with sources."),
    ("Latest posts", "Find the latest 3 public X posts from @OpenAI and summarize them."),
    ("Research brief", "Research AI agent safety this week and create a concise brief with sources."),
)
HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4
DEFAULT_VERSION = "v3"
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
SHOW_DEVELOPER_DETAILS_DEFAULT = False


def normalize_version_label(value: str) -> str:
    return value.strip() or DEFAULT_VERSION


def setup_template(provider_name: str) -> str:
    return "\n".join(
        f'{name} = "PASTE_VALUE_HERE"'
        for name in configured_secret_names(provider_name)
    )


def secret_status(
    provider_name: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    source = environ if environ is not None else os.environ
    return {
        name: bool(source.get(name))
        for name in configured_secret_names(provider_name)
    }


def setup_panel_payload(
    provider_name: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str] | None:
    provider_key = PROVIDER_ENV_VARS[provider_name]
    if secret_status(provider_name, environ=environ)[provider_key]:
        return None
    return {
        "provider_key": provider_key,
        "template": setup_template(provider_name),
    }


THEME_CSS = """
:root {
    --agent-bg: #f7f9f8;
    --agent-surface: #ffffff;
    --agent-surface-muted: #eef2f1;
    --agent-ink: #17211f;
    --agent-muted: #5f6d68;
    --agent-border: #cbd5d1;
    --agent-primary: #0f766e;
    --agent-primary-soft: #dcefeb;
    --agent-warning: #a15c16;
}

header[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stAppDeployButton,
#MainMenu,
footer {
    display: none !important;
}

.block-container {
    max-width: 960px;
    padding-top: 1.75rem;
    padding-bottom: 0.75rem;
}

[data-testid="stSidebar"] {
    border-right: 1px solid var(--agent-border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.25rem;
}

h1 {
    color: var(--agent-ink);
    font-size: clamp(2rem, 4vw, 2.65rem) !important;
    letter-spacing: -0.035em !important;
    line-height: 1.05 !important;
    margin-bottom: 0.35rem !important;
}

h2,
h3 {
    color: var(--agent-ink);
    letter-spacing: -0.02em;
}

.agent-kicker {
    color: var(--agent-primary) !important;
    font-size: 0.72rem;
    font-weight: 750;
    letter-spacing: 0.13em;
    margin-bottom: 0.35rem;
    text-transform: uppercase;
}

.agent-subtitle {
    color: var(--agent-muted) !important;
    font-size: 1rem;
    margin-bottom: 1rem;
    max-width: 42rem;
}

.agent-status-grid {
    border-bottom: 1px solid var(--agent-border);
    border-top: 1px solid var(--agent-border);
    display: flex;
    flex-wrap: wrap;
    margin: 1rem 0 1.25rem;
}

.agent-status {
    align-items: center;
    border-right: 1px solid var(--agent-border);
    color: var(--agent-muted) !important;
    display: inline-flex;
    font-size: 0.78rem;
    gap: 0.4rem;
    margin-right: 0.9rem;
    padding: 0.65rem 0.9rem 0.65rem 0;
}

.agent-status:last-child {
    border-right: 0;
}

.agent-status-mark {
    background: var(--agent-warning);
    border-radius: 50%;
    display: inline-block;
    height: 0.48rem;
    width: 0.48rem;
}

.agent-status-mark.ready {
    background: var(--agent-primary);
}

.agent-setup {
    background: #fff8e9;
    border: 1px solid #dfc99f;
    border-left: 4px solid var(--agent-warning);
    border-radius: 8px;
    margin: 0.75rem 0 1.25rem;
    padding: 1rem 1.1rem;
}

.agent-setup strong,
.agent-empty strong {
    color: var(--agent-ink);
    display: block;
    font-size: 1rem;
    margin-bottom: 0.25rem;
}

.agent-setup span,
.agent-empty span {
    color: var(--agent-muted) !important;
    font-size: 0.9rem;
}

.agent-empty {
    border-bottom: 1px solid var(--agent-border);
    margin: 0.75rem 0 1rem;
    padding: 0.85rem 0 1.1rem;
}

[data-testid="stChatMessage"] {
    background: var(--agent-surface);
    border: 1px solid var(--agent-border);
    border-radius: 10px;
    margin-bottom: 0.75rem;
    padding: 0.2rem 0.3rem;
}

[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid var(--agent-border);
    border-radius: 8px;
}

[data-testid="stChatInput"] {
    box-shadow: 0 10px 28px rgba(49, 58, 54, 0.10);
}

@media (max-width: 640px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1.2rem;
    }

    .agent-status {
        border-right: 0;
        padding-bottom: 0.35rem;
        padding-top: 0.35rem;
    }
}
"""


def apply_theme() -> None:
    st.markdown(f"<style>{THEME_CSS}</style>", unsafe_allow_html=True)


def provider_is_configured(provider_name: str) -> bool:
    env_name = PROVIDER_ENV_VARS[provider_name]
    return bool(os.getenv(env_name))


def sanitize_error_text(value: str) -> str:
    safe_value = value
    for env_name, env_value in os.environ.items():
        if (
            env_value
            and len(env_value) >= 4
            and any(marker in env_name.upper() for marker in SECRET_ENV_MARKERS)
        ):
            safe_value = safe_value.replace(env_value, "[redacted]")

    safe_value = re.sub(r"https?://\S+", "[redacted-url]", safe_value)
    safe_value = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*\S+",
        r"\1=[redacted]",
        safe_value,
    )
    return safe_value[:800]


def fallback_hint(error_text: str) -> str:
    hint_builder = getattr(guardrails, "fallback_hint", None)
    if callable(hint_builder):
        return hint_builder(error_text)
    return (
        "Không tải được chẩn đoán backend mới nhất. "
        "Hãy khởi động lại app rồi thử lại."
    )


def sanitize_tool_errors(value: Any) -> Any:
    if isinstance(value, list):
        return [sanitize_tool_errors(item) for item in value]
    if not isinstance(value, dict):
        return value

    has_error = bool(value.get("error"))
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, str) and (key == "error" or (has_error and key == "message")):
            sanitized[key] = sanitize_error_text(item)
        else:
            sanitized[key] = sanitize_tool_errors(item)
    return sanitized


def load_current_artifacts(version_label: str) -> dict[str, Any]:
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    artifact = build_artifact_version(
        version_label,
        SYSTEM_PROMPT_PATH,
        TOOLS_PATH,
    )
    return {
        "system_prompt": system_prompt,
        "declarations": declarations,
        "tools": to_openai_tools(declarations),
        "artifact": artifact,
    }


def create_conversation(
    provider_name: str,
    model_override: str | None,
    version_label: str,
    *,
    provider_factory: Callable[[str], Any] = make_provider,
) -> dict[str, Any]:
    artifacts = load_current_artifacts(version_label)
    provider = provider_factory(provider_name)
    selected_model = model_override or getattr(provider, "default_model", None)
    artifact = artifacts["artifact"]
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join(
        [
            safe_slug(version_label),
            safe_slug(provider_name),
            timestamp,
        ]
    )
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": selected_model,
        "system_prompt": str(SYSTEM_PROMPT_PATH.relative_to(ROOT)),
        "tools": str(TOOLS_PATH.relative_to(ROOT)),
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    return {
        "provider": provider_name,
        "model_override": model_override,
        "selected_model": selected_model,
        "version_label": version_label,
        "artifact": artifact,
        "system_prompt": artifacts["system_prompt"],
        "tools": artifacts["tools"],
        "declared_tool_count": len(artifacts["declarations"]),
        "history": [],
        "transcript": transcript,
        "transcript_path": transcript_path,
    }


def run_turn(
    conversation: dict[str, Any],
    user_text: str,
    *,
    provider_factory: Callable[[str], Any] = make_provider,
) -> dict[str, Any]:
    transcript = conversation["transcript"]
    turn_record: dict[str, Any] = {
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    rate_limiter = conversation.setdefault("rate_limiter", guardrails.RateLimiter())
    verdict = guardrails.pre_guard(user_text, rate_limiter=rate_limiter)
    if not verdict["allowed"]:
        turn_record.update(
            {
                "status": "blocked_by_guardrail",
                "guardrail_reason": verdict["reason"],
                "assistant_text": verdict["message"],
            }
        )
        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(conversation["transcript_path"], transcript)
        return turn_record

    messages = [
        {"role": "system", "content": conversation["system_prompt"]},
        *trim_history(conversation["history"], HISTORY_WINDOW),
        {"role": "user", "content": user_text},
    ]

    try:
        provider = provider_factory(conversation["provider"])
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=conversation["tools"],
            model=conversation["model_override"],
            max_tool_rounds=MAX_TOOL_ROUNDS,
            tool_guard=guardrails.check_tool_call,
        )
        sanitized_result = sanitize_tool_errors(result)
        sanitized_result["assistant_text"] = guardrails.mask_pii(
            sanitized_result.get("assistant_text") or ""
        )
        turn_record.update(sanitized_result)
        assistant_text = sanitized_result["assistant_text"]
        conversation["history"].append({"role": "user", "content": user_text})
        conversation["history"].append(
            {"role": "assistant", "content": assistant_text}
        )
    except Exception as exc:
        turn_record.update(
            {
                "status": "fallback",
                "error": sanitize_error_text(
                    f"{type(exc).__name__}: {str(exc)}"
                ),
                "assistant_text": guardrails.fallback_response(user_text),
            }
        )

    turn_record["ended_at"] = now_iso()
    transcript["turns"].append(turn_record)
    write_transcript(conversation["transcript_path"], transcript)
    return turn_record


def tool_event_summary(event: dict[str, Any]) -> str:
    tool_name = str(event.get("tool") or "unknown")
    result = event.get("result")
    if isinstance(result, dict) and result.get("error"):
        code = str(result.get("code") or result["error"])
        return f"{tool_name} · {code.replace('_', ' ').lower()}"

    parts = [tool_name, "success"]
    if isinstance(result, dict):
        items = result.get("items")
        if isinstance(items, list):
            label = "result" if len(items) == 1 else "results"
            parts.append(f"{len(items)} {label}")
        if result.get("provider"):
            parts.append(str(result["provider"]))
    return " · ".join(parts)


def render_tool_event(
    event: dict[str, Any],
    event_index: int,
    *,
    show_details: bool,
) -> None:
    st.markdown(f"**{event_index}. {tool_event_summary(event)}**")
    result = event.get("result")
    if isinstance(result, dict) and result.get("error"):
        st.warning(
            result.get("message")
            or str(result.get("code") or result["error"])
        )

    if show_details:
        st.caption("Arguments")
        st.json(event.get("args", {}))
        st.caption("Result")
        st.json(result)


def render_trace(turn: dict[str, Any]) -> None:
    rounds = turn.get("rounds", [])
    tool_count = len(turn.get("tool_events", []))
    label = f"⚡ Trace · {len(rounds)} round(s) · {tool_count} tool event(s)"
    with st.expander(label, expanded=False):
        show_details = st.toggle(
            "Show developer details",
            value=SHOW_DEVELOPER_DETAILS_DEFAULT,
            key=f"trace_details_{turn.get('started_at', '')}",
        )
        for round_position, round_record in enumerate(rounds):
            if round_position:
                st.divider()
            st.markdown(f"**Round {round_record.get('round', round_position + 1)}**")
            assistant_text = round_record.get("assistant_text")
            if assistant_text:
                st.caption("Intermediate assistant response")
                st.write(assistant_text)

            events = round_record.get("tool_results", [])
            if not events:
                st.caption("No tool call in this round.")
            for event_index, event in enumerate(events, start=1):
                render_tool_event(
                    event,
                    event_index,
                    show_details=show_details,
                )


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(turn["user"])

    with st.chat_message("assistant"):
        status = turn.get("status")
        if status == "provider_error":
            st.error(turn.get("error", "Provider request failed."))
        elif status == "fallback":
            st.warning(
                "Backend không khả dụng - phản hồi bên dưới là câu trả lời "
                "mặc định của chế độ dự phòng."
            )
            if turn.get("error"):
                st.caption(fallback_hint(turn["error"]))
            st.write(turn.get("assistant_text") or "No response text.")
        elif status == "blocked_by_guardrail":
            st.warning(turn.get("assistant_text") or "Yêu cầu bị guardrail chặn.")
            st.caption(f"Guardrail: {turn.get('guardrail_reason', 'unknown')}")
        else:
            st.markdown(turn.get("assistant_text") or "No response text.")
            status = turn.get("status", "unknown")
            tool_count = len(turn.get("tool_events", []))
            st.caption(f"● {status} · {tool_count} tool event(s)")
        render_trace(turn)


def clear_conversation() -> None:
    st.session_state.pop("conversation", None)
    st.session_state.pop("saved_notice", None)


def render_sidebar() -> tuple[str, str | None, str]:
    conversation = st.session_state.get("conversation")
    locked = conversation is not None

    with st.sidebar:
        st.header("Research run")
        if locked and st.button("＋ New conversation", use_container_width=True):
            clear_conversation()
            st.rerun()

        provider = st.selectbox(
            "Provider",
            SUPPORTED_PROVIDERS,
            disabled=locked,
            help="Credentials are read from environment variables.",
        )
        active_provider = conversation["provider"] if locked else provider
        status = secret_status(active_provider)
        provider_key = PROVIDER_ENV_VARS[active_provider]
        st.markdown(
            (
                '<div class="agent-status-grid">'
                f'<span class="agent-status"><span class="agent-status-mark {"ready" if status[provider_key] else ""}"></span>'
                f'{html.escape(active_provider)} · {"Key set" if status[provider_key] else "Missing"}</span>'
                f'<span class="agent-status"><span class="agent-status-mark {"ready" if status["TAVILY_API_KEY"] else ""}"></span>'
                f'Tavily · {"Key set" if status["TAVILY_API_KEY"] else "Missing"}</span>'
                f'<span class="agent-status"><span class="agent-status-mark {"ready" if status["FIRECRAWL_API_KEY"] else ""}"></span>'
                f'Firecrawl · {"Key set" if status["FIRECRAWL_API_KEY"] else "Optional"}</span>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "Key presence is shown here. The first tool request validates it."
        )
        with st.expander("Advanced", expanded=False):
            model_text = st.text_input(
                "Model (optional)",
                placeholder="Use provider default",
                disabled=locked,
            ).strip()
            version_label = normalize_version_label(
                st.text_input(
                    "Version",
                    value=DEFAULT_VERSION,
                    disabled=locked,
                    help=(
                        "Combined with the current prompt and tool hashes."
                    ),
                )
            )

        if locked:
            st.divider()
            st.caption("Active transcript")
            st.code(conversation["transcript"]["transcript_id"], language=None)
            st.caption(str(conversation["transcript_path"]))
            st.download_button(
                "↓ Download transcript",
                data=json.dumps(
                    conversation["transcript"],
                    ensure_ascii=False,
                    indent=2,
                ),
                file_name=conversation["transcript_path"].name,
                mime="application/json",
                use_container_width=True,
            )

    return provider, model_text or None, version_label


def render_quick_prompts() -> str | None:
    st.caption("Starter research tasks")
    selected: str | None = None
    for label, prompt in QUICK_PROMPTS:
        if st.button(
            f"{label}  ·  {prompt}",
            key=f"starter_{safe_slug(label)}",
            use_container_width=True,
        ):
            selected = prompt
    return selected


def main() -> None:
    st.set_page_config(
        page_title="Research Agent",
        page_icon="🔎",
        layout="centered",
    )
    resolve_secrets(st.secrets)
    apply_theme()

    provider, model_override, version_label = render_sidebar()
    conversation = st.session_state.get("conversation")

    try:
        if conversation:
            preview = {
                "artifact": conversation["artifact"],
                "declared_tool_count": conversation["declared_tool_count"],
            }
        else:
            current_artifacts = load_current_artifacts(version_label)
            preview = {
                **current_artifacts,
                "declared_tool_count": len(current_artifacts["declarations"]),
            }
    except (OSError, KeyError, TypeError, ValueError) as exc:
        st.error(f"Could not load the current artifacts: {type(exc).__name__}")
        st.stop()

    artifact = preview["artifact"]
    active_provider = conversation["provider"] if conversation else provider
    active_model = (
        conversation["selected_model"]
        if conversation
        else model_override or "provider default"
    )
    turn_count = len(conversation["transcript"]["turns"]) if conversation else 0
    provider_ready = provider_is_configured(active_provider)

    st.markdown(
        '<p class="agent-kicker">Team B1 · Research workspace</p>',
        unsafe_allow_html=True,
    )
    st.title("Research Agent")
    st.markdown(
        (
            '<p class="agent-subtitle">Investigate current questions with '
            "visible sources, inspectable tool traces, and replayable evidence.</p>"
        ),
        unsafe_allow_html=True,
    )
    status = secret_status(active_provider)
    st.markdown(
        (
            '<div class="agent-status-grid">'
            f'<span class="agent-status"><span class="agent-status-mark {"ready" if provider_ready else ""}"></span>'
            f'{html.escape(active_provider)} · {"Configured" if provider_ready else "Setup required"}</span>'
            f'<span class="agent-status">Model · {html.escape(str(active_model))}</span>'
            f'<span class="agent-status">Tools · {preview["declared_tool_count"]}</span>'
            f'<span class="agent-status">Turns · {turn_count}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    setup = setup_panel_payload(active_provider)
    missing_research = [
        name
        for name in ("TAVILY_API_KEY", "FIRECRAWL_API_KEY")
        if not status[name]
    ]
    if provider_ready and missing_research:
        missing_labels = ", ".join(missing_research)
        st.info(
            f"Model is ready. Research coverage is limited until {missing_labels} "
            "is configured."
        )

    saved_notice = st.session_state.pop("saved_notice", None)
    if saved_notice:
        st.toast(f"Transcript updated · {saved_notice}", icon="✅")

    quick_request: str | None = None
    if conversation:
        for turn in conversation["transcript"]["turns"]:
            render_turn(turn)
    elif setup is None:
        st.markdown(
            (
                '<div class="agent-empty">'
                "<strong>Start with a research question.</strong>"
                "<span>The workspace locks the selected artifact, records each "
                "tool round, and saves a replayable transcript automatically.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        quick_request = render_quick_prompts()

    if setup is None or conversation:
        with st.expander(f"Technical details · {artifact.artifact_version}"):
            st.json(
                {
                    "version": artifact.version,
                    "artifact_version": artifact.artifact_version,
                    "prompt_hash": artifact.prompt_hash,
                    "tools_hash": artifact.tools_hash,
                    "declared_tools": preview["declared_tool_count"],
                }
            )

    if setup:
        st.markdown(
            (
                '<div class="agent-setup">'
                "<strong>Connect the model provider</strong>"
                f'<span>Add <code>{html.escape(setup["provider_key"])}</code> '
                "at the root of Manage app &gt; Settings &gt; Secrets. "
                "Save, then reboot the app.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.code(setup["template"], language="toml")
        st.caption(
            "The chat remains available in fallback mode until the provider "
            "status changes to Configured."
        )

    request = st.chat_input("Ask a research question")
    request = request or quick_request
    if request:
        if conversation is None:
            try:
                conversation = create_conversation(
                    provider,
                    model_override,
                    version_label,
                )
                st.session_state["conversation"] = conversation
            except Exception as exc:
                st.warning(
                    "Không khởi tạo được provider - chuyển sang CHẾ ĐỘ DỰ PHÒNG. "
                    "Bạn vẫn chat được nhưng chỉ nhận câu trả lời mặc định."
                )
                try:
                    conversation = create_conversation(
                        provider,
                        model_override,
                        version_label,
                        provider_factory=lambda _: guardrails.FallbackProvider(),
                    )
                    st.session_state["conversation"] = conversation
                except Exception:
                    st.error(
                        sanitize_error_text(
                            f"Could not start the conversation: {type(exc).__name__}: {exc}"
                        )
                    )
                    st.stop()

        with st.spinner("Researching…"):
            run_turn(conversation, request)
        st.session_state["saved_notice"] = conversation["transcript"]["transcript_id"]
        st.rerun()


if __name__ == "__main__":
    main()
