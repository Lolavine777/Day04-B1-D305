from __future__ import annotations

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
HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


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
    st.markdown(f"**Tool {event_index}: `{tool_name}`**")
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
        st.caption("Result")
        st.json(result)


def render_trace(turn: dict[str, Any]) -> None:
    rounds = turn.get("rounds", [])
    tool_count = len(turn.get("tool_events", []))
    label = f"Trace · {len(rounds)} round(s) · {tool_count} tool event(s)"
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
            st.write(turn.get("assistant_text") or "No response text.")
            st.caption(f"Status: {status or 'unknown'}")
        render_trace(turn)


def clear_conversation() -> None:
    st.session_state.pop("conversation", None)


def render_sidebar() -> tuple[str, str | None, str]:
    conversation = st.session_state.get("conversation")
    locked = conversation is not None

    with st.sidebar:
        st.header("Settings")
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

        st.caption("API keys stay in `.env` and are never displayed here.")
        if locked:
            st.divider()
            st.caption("Transcript")
            st.code(conversation["transcript"]["transcript_id"], language=None)
            st.caption(str(conversation["transcript_path"]))

    return provider, model_text or None, version_label


def main() -> None:
    st.set_page_config(
        page_title="Research Agent",
        page_icon="🔎",
        layout="centered",
    )

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
    st.title("Research Agent")
    st.caption(f"Artifact `{artifact.artifact_version}`")

    with st.expander("Artifact details"):
        st.json(
            {
                "version": artifact.version,
                "artifact_version": artifact.artifact_version,
                "prompt_hash": artifact.prompt_hash,
                "tools_hash": artifact.tools_hash,
                "declared_tools": preview["declared_tool_count"],
            }
        )

    if conversation:
        for turn in conversation["transcript"]["turns"]:
            render_turn(turn)
    else:
        st.info(
            "Choose a provider, then ask a question. The conversation settings "
            "will be locked after the first message."
        )

    request = st.chat_input("Ask a research question")
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
        st.rerun()


if __name__ == "__main__":
    main()
