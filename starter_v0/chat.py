from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def trim_history(history: list[dict[str, str]], window: int) -> list[dict[str, str]]:
    if window <= 0:
        return []
    return history[-window * 2:]


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No local implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def _emit(
    callback: Callable[[dict[str, Any]], None] | None,
    event_type: str,
    **payload: Any,
) -> None:
    if callback is None:
        return
    try:
        callback({"type": event_type, **payload})
    except Exception:
        # UI telemetry must never break the canonical agent loop.
        return


def _merge_usage(
    total: dict[str, int | float],
    update: dict[str, int | float] | None,
) -> None:
    for key, value in (update or {}).items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        total[key] = total.get(key, 0) + value


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for a digest and the items are ready, "
            "call the formatting tool. Otherwise answer the user directly with cited sources when available."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


def run_model_tool_loop(
    *,
    provider: Any,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    model: str | None,
    max_tool_rounds: int,
    event_callback: Callable[[dict[str, Any]], None] | None = None,
    blocked_tools: set[str] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    first_token_at: float | None = None
    working_messages = list(messages)
    rounds: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []
    usage_total: dict[str, int | float] = {}
    blocked = blocked_tools or set()

    _emit(event_callback, "run_started")

    def is_cancelled() -> bool:
        if should_cancel is None:
            return False
        try:
            return bool(should_cancel())
        except Exception:
            return False

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 1)
        ttft_ms = (
            round((first_token_at - started_at) * 1000, 1)
            if first_token_at is not None
            else None
        )
        result["usage"] = usage_total
        result["latency_ms"] = latency_ms
        result["ttft_ms"] = ttft_ms
        _emit(
            event_callback,
            "run_completed",
            status=result["status"],
            assistant_text=result["assistant_text"],
            usage=usage_total,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
        )
        return result

    for round_index in range(1, max_tool_rounds + 1):
        if is_cancelled():
            return finish(
                {
                    "status": "cancelled",
                    "assistant_text": "Request cancelled.",
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }
            )
        _emit(event_callback, "round_started", round=round_index)
        model_started_at = time.perf_counter()
        stream_mode = "buffered"

        def on_text_delta(delta: str) -> None:
            nonlocal first_token_at
            if first_token_at is None:
                first_token_at = time.perf_counter()
            _emit(
                event_callback,
                "assistant_delta",
                round=round_index,
                delta=delta,
            )

        complete_stream = getattr(provider, "complete_stream", None)
        if event_callback is not None and callable(complete_stream):
            stream_mode = "streaming"
            response = complete_stream(
                working_messages,
                tools,
                model=model,
                temperature=0.0,
                on_text_delta=on_text_delta,
            )
        else:
            response = provider.complete(
                working_messages,
                tools,
                model=model,
                temperature=0.0,
            )
            if event_callback is not None and response.text:
                on_text_delta(response.text)

        model_latency_ms = round(
            (time.perf_counter() - model_started_at) * 1000,
            1,
        )
        response_usage = getattr(response, "usage", {}) or {}
        _merge_usage(usage_total, response_usage)
        calls = response.tool_calls
        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
            "usage": response_usage,
            "model_latency_ms": model_latency_ms,
            "stream_mode": stream_mode,
        }
        _emit(
            event_callback,
            "model_completed",
            round=round_index,
            has_tool_calls=bool(calls),
            usage=response_usage,
            latency_ms=model_latency_ms,
            stream_mode=stream_mode,
        )

        if not calls:
            rounds.append(round_record)
            return finish(
                {
                    "status": "answered",
                    "assistant_text": response.text or "",
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }
            )

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict[str, Any]] = []

        for call_index, call in enumerate(calls, start=1):
            if is_cancelled():
                rounds.append(round_record)
                return finish(
                    {
                        "status": "cancelled",
                        "assistant_text": "Request cancelled.",
                        "rounds": rounds,
                        "tool_events": all_tool_events,
                    }
                )
            tool_id = f"r{round_index}-t{call_index}"
            print(f"🔧 {call.name}({json.dumps(call.args, ensure_ascii=False, sort_keys=True)})")
            _emit(
                event_callback,
                "tool_started",
                round=round_index,
                tool_id=tool_id,
                tool=call.name,
                args=call.args,
            )
            tool_started_at = time.perf_counter()
            if call.name in blocked:
                event = {
                    "tool": call.name,
                    "args": call.args,
                    "result": {
                        "error": "tool_disabled",
                        "message": "This tool is disabled in the public web workspace.",
                    },
                }
            else:
                event = execute_tool_call(call)
            tool_latency_ms = round(
                (time.perf_counter() - tool_started_at) * 1000,
                1,
            )
            tool_result = event.get("result", {})
            tool_status = (
                "error"
                if isinstance(tool_result, dict) and tool_result.get("error")
                else "success"
            )
            event.update(
                {
                    "tool_id": tool_id,
                    "round": round_index,
                    "status": tool_status,
                    "latency_ms": tool_latency_ms,
                }
            )
            round_record["tool_results"].append(event)
            all_tool_events.append(event)
            _emit(
                event_callback,
                "tool_completed",
                round=round_index,
                tool_id=tool_id,
                tool=call.name,
                args=call.args,
                result=tool_result,
                status=tool_status,
                latency_ms=tool_latency_ms,
            )

            # Detect the clarification/pause tool by its output flag (rename-proof),
            # not by a hard-coded tool name.
            result = event.get("result", {})
            if isinstance(result, dict) and result.get("awaiting_user"):
                question = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                rounds.append(round_record)
                return finish(
                    {
                        "status": "waiting_for_user",
                        "assistant_text": question,
                        "rounds": rounds,
                        "tool_events": all_tool_events,
                    }
                )

            non_clarification_events.append(event)

        rounds.append(round_record)
        working_messages.append(tool_results_message(non_clarification_events))

    return finish(
        {
            "status": "max_tool_rounds",
            "assistant_text": f"Stopped after {max_tool_rounds} tool rounds. Inspect the transcript for details.",
            "rounds": rounds,
            "tool_events": all_tool_events,
        }
    )


def write_transcript(path: Path, transcript: dict[str, Any]) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Research Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Student-chosen artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5, help="Keep the last N user/assistant pairs in context.")
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(args.tools)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(args.version),
        safe_slug(args.provider),
        timestamp,
    ])
    transcript_path = args.transcripts_dir / f"{transcript_id}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": args.provider,
        "model": selected_model,
        "system_prompt": str(args.system_prompt),
        "tools": str(args.tools),
        "history_window": args.history_window,
        "max_tool_rounds": args.max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    print(f"Research Agent chat. artifact_version={artifact_version.artifact_version}")
    print("Type /exit to stop.")

    history: list[dict[str, str]] = []
    turn_index = 0
    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            break

        turn_index += 1
        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            print(f"\nAgent> {assistant_text}")
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
            })
            print(f"\nERROR> {turn_record['error']}")

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(transcript_path, transcript)
        print(f"Transcript saved: {transcript_path}")

    write_transcript(transcript_path, transcript)
    print(f"Final transcript: {transcript_path}")


if __name__ == "__main__":
    main()
