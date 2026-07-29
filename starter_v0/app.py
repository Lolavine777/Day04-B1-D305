from __future__ import annotations

import html
import json
import os
import re
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
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
SYSTEM_PROMPT_PATH = ROOT / "artifacts" / "system_prompt.md"
TOOLS_PATH = ROOT / "artifacts" / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SUPPORTED_PROVIDERS = ("openrouter", "openai", "anthropic", "gemini")
PROVIDER_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
QUICK_PROMPTS = (
    ("AI today", "Find 3 important AI updates today and summarize them with sources."),
    ("Latest posts", "Find the latest 3 public X posts from @OpenAI and summarize them."),
    ("Research brief", "Research AI agent safety this week and create a concise brief with sources."),
)
HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --agent-ink: #172033;
            --agent-muted: #667085;
            --agent-border: rgba(97, 114, 146, 0.16);
            --agent-card: rgba(255, 255, 255, 0.84);
            --agent-primary: #5b5bd6;
            --agent-accent: #0f9f8f;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(91, 91, 214, 0.11), transparent 28rem),
                radial-gradient(circle at 92% 8%, rgba(15, 159, 143, 0.10), transparent 25rem),
                #f7f8fc;
            color: var(--agent-ink);
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
            max-width: 940px;
            padding-top: 2.6rem;
            padding-bottom: 7rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(244, 246, 251, 0.95);
            border-right: 1px solid var(--agent-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.5rem;
        }

        h1 {
            color: var(--agent-ink);
            font-size: clamp(2rem, 5vw, 3.2rem) !important;
            letter-spacing: -0.045em !important;
            margin-bottom: 0.25rem !important;
        }

        .agent-kicker {
            color: var(--agent-primary);
            font-size: 0.75rem;
            font-weight: 750;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.3rem;
        }

        .agent-subtitle {
            color: var(--agent-muted);
            font-size: 1.02rem;
            margin-bottom: 1rem;
        }

        .agent-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.25rem 0 1.4rem;
        }

        .agent-chip {
            align-items: center;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid var(--agent-border);
            border-radius: 999px;
            color: #46516a;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 650;
            gap: 0.4rem;
            padding: 0.38rem 0.72rem;
        }

        .agent-dot {
            background: #f59e0b;
            border-radius: 50%;
            height: 0.48rem;
            width: 0.48rem;
        }

        .agent-dot.ready {
            background: #12b76a;
            box-shadow: 0 0 0 3px rgba(18, 183, 106, 0.12);
        }

        .agent-empty {
            background: linear-gradient(145deg, rgba(255,255,255,0.94), rgba(246,248,255,0.86));
            border: 1px solid var(--agent-border);
            border-radius: 1.25rem;
            box-shadow: 0 18px 55px rgba(37, 51, 84, 0.07);
            margin: 1rem 0;
            padding: 1.35rem 1.45rem;
        }

        .agent-empty strong {
            color: var(--agent-ink);
            display: block;
            font-size: 1.05rem;
            margin-bottom: 0.3rem;
        }

        .agent-empty span {
            color: var(--agent-muted);
            font-size: 0.9rem;
        }

        [data-testid="stChatMessage"] {
            background: var(--agent-card);
            border: 1px solid var(--agent-border);
            border-radius: 1.1rem;
            box-shadow: 0 10px 30px rgba(45, 55, 90, 0.045);
            margin-bottom: 0.85rem;
            padding: 0.25rem 0.35rem;
        }

        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.66);
            border: 1px solid var(--agent-border);
            border-radius: 0.9rem;
        }

        [data-testid="stChatInput"] {
            background: rgba(255,255,255,0.92);
            border: 1px solid rgba(91, 91, 214, 0.22);
            border-radius: 1rem;
            box-shadow: 0 16px 44px rgba(52, 59, 112, 0.12);
        }

        .stButton > button,
        .stDownloadButton > button {
            border-color: var(--agent-border);
            border-radius: 0.8rem;
            min-height: 2.65rem;
            transition: border-color 150ms ease, transform 150ms ease, box-shadow 150ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: rgba(91, 91, 214, 0.48);
            box-shadow: 0 8px 24px rgba(91, 91, 214, 0.10);
            transform: translateY(-1px);
        }

        div[data-testid="stStatusWidget"] {
            border-radius: 1rem;
        }

        @media (max-width: 640px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.6rem;
            }

            .agent-chips {
                gap: 0.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def render_tool_event(event: dict[str, Any], event_index: int) -> None:
    tool_name = event.get("tool", "unknown")
    with st.container(border=True):
        st.markdown(f"**⚙️ Tool {event_index} · `{tool_name}`**")
        st.caption("Arguments")
        st.json(event.get("args", {}))

        result = event.get("result")
        if isinstance(result, dict) and result.get("error"):
            message = result.get("message")
            error_text = str(result["error"])
            if message:
                error_text = f"{error_text}: {message}"
            st.error(error_text)
        else:
            if isinstance(result, dict) and result.get("provider"):
                st.caption(
                    f"Provider: {result['provider']} · "
                    f"Coverage: {result.get('coverage', 'direct API')}"
                )
            st.caption("Result")
            st.json(result)


def render_trace(turn: dict[str, Any]) -> None:
    rounds = turn.get("rounds", [])
    tool_count = len(turn.get("tool_events", []))
    label = f"⚡ Trace · {len(rounds)} round(s) · {tool_count} tool event(s)"
    with st.expander(label):
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
                render_tool_event(event, event_index)


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(turn["user"])

    with st.chat_message("assistant"):
        status = turn.get("status")
        if status == "provider_error":
            st.error(turn.get("error", "Provider request failed."))
        elif status == "fallback":
            st.warning(
                "Backend không khả dụng — phản hồi bên dưới là câu trả lời "
                "mặc định của chế độ dự phòng."
            )
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
        st.markdown('<p class="agent-kicker">Workspace</p>', unsafe_allow_html=True)
        st.header("Run settings")
        if locked and st.button("＋ New conversation", use_container_width=True):
            clear_conversation()
            st.rerun()

        provider = st.selectbox(
            "Provider",
            SUPPORTED_PROVIDERS,
            disabled=locked,
            help="Credentials are read from .env.",
        )
        model_text = st.text_input(
            "Model (optional)",
            placeholder="Use provider default",
            disabled=locked,
        ).strip()
        version_label = (
            st.text_input(
                "Version",
                value="v0",
                disabled=locked,
                help="Combined with the current prompt and tool hashes.",
            ).strip()
            or "v0"
        )

        active_provider = conversation["provider"] if locked else provider
        configured = provider_is_configured(active_provider)
        state_class = "ready" if configured else ""
        state_label = "Ready" if configured else "Missing API key"
        st.markdown(
            (
                '<div class="agent-chips">'
                f'<span class="agent-chip"><span class="agent-dot {state_class}"></span>'
                f'{html.escape(active_provider)} · {state_label}</span>'
                f'<span class="agent-chip"><span class="agent-dot {"ready" if os.getenv("TAVILY_API_KEY") else ""}"></span>'
                f'Tavily · {"Ready" if os.getenv("TAVILY_API_KEY") else "Missing key"}</span>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.caption("API keys stay in `.env` and are never displayed.")
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
    st.caption("Try a starter")
    columns = st.columns(len(QUICK_PROMPTS))
    selected: str | None = None
    for column, (label, prompt) in zip(columns, QUICK_PROMPTS):
        with column:
            if st.button(label, use_container_width=True, help=prompt):
                selected = prompt
    return selected


def main() -> None:
    st.set_page_config(
        page_title="Research Agent",
        page_icon="🔎",
        layout="centered",
    )
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

    st.markdown('<p class="agent-kicker">Team B1 · Live research workspace</p>', unsafe_allow_html=True)
    st.title("Research Agent")
    st.markdown(
        '<p class="agent-subtitle">Research with visible tool traces, versioned artifacts, and replayable evidence.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="agent-chips">'
            f'<span class="agent-chip"><span class="agent-dot {"ready" if provider_ready else ""}"></span>'
            f'{html.escape(active_provider)} · {"Ready" if provider_ready else "Key required"}</span>'
            f'<span class="agent-chip">Model · {html.escape(str(active_model))}</span>'
            f'<span class="agent-chip">Tools · {preview["declared_tool_count"]}</span>'
            f'<span class="agent-chip">Turns · {turn_count}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    saved_notice = st.session_state.pop("saved_notice", None)
    if saved_notice:
        st.toast(f"Transcript updated · {saved_notice}", icon="✅")

    with st.expander(f"Artifact · {artifact.artifact_version}"):
        st.json(
            {
                "version": artifact.version,
                "artifact_version": artifact.artifact_version,
                "prompt_hash": artifact.prompt_hash,
                "tools_hash": artifact.tools_hash,
                "declared_tools": preview["declared_tool_count"],
            }
        )

    quick_request: str | None = None
    if conversation:
        for turn in conversation["transcript"]["turns"]:
            render_turn(turn)
    else:
        st.markdown(
            (
                '<div class="agent-empty">'
                "<strong>Start with a question, not a configuration maze.</strong>"
                "<span>Choose a provider once. This workspace will lock the artifact, "
                "show every tool round, and save the transcript automatically.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        quick_request = render_quick_prompts()

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
                    "Không khởi tạo được provider — chuyển sang CHẾ ĐỘ DỰ PHÒNG. "
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
