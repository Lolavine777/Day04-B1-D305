# Team B1 Day 04 Lab Masterplan

## Mission

Build, evaluate, demonstrate, and submit the research agent in `starter_v0/`.
Five members work on separate branches during the parallel build phase.
Every member stops at the checkpoints defined in their prompt and reports evidence to their user before continuing.

## Team

| Member | Student ID | Role | Branch |
|---|---|---|---|
| Nguyễn Đăng Long | 2A202601934 | Agent quality and routing | `develop/long` |
| Lê Đăng Tấn | 2A202601916 | UI and transcripts | `develop/tan` |
| Đào Minh Chiến | 2A202601184 | New local tool | `develop/chien` |
| Vũ Hữu An | 2A202601078 | Group eval design | `develop/an` |
| Nguyễn Trần Nghĩa | 2A202601664 | Validation, report, and release | `develop/nghia` |

## Source of Truth

- `README.md` defines the lab deliverables.
- `TOOL-SETUP.md` defines provider and tool setup.
- `TEAMMATES.md` defines the official team roster.
- This file defines ownership, checkpoints, and integration order.
- Files under `agent-prompts/` contain the copy-paste prompt for each coding agent.
- Run JSON, transcript JSON, hashes, test output, and PR commits are evidence.
- Chat claims without an artifact or command output are not evidence.

## Global Rules

- Work only on the assigned branch.
- Do not merge a PR unless the user explicitly authorizes it.
- Do not modify files owned by another lane.
- Do not rename existing tools.
- Do not modify `starter_v0/data/eval_base.json`.
- Do not modify `starter_v0/data/eval_research_extension.json`.
- Never commit `.env`, API keys, `.venv`, caches, or generated secrets.
- Run Python through `starter_v0/.venv/bin/python` or `uv run`.
- Keep each v1, v2, and v3 change tied to one explicit hypothesis.
- Stop at each checkpoint and wait for the user to say `CONTINUE`.
- If a contract conflict appears, stop and report `CONTRACT_BLOCKED`.
- If a required credential or human decision is missing, stop and report `HUMAN_INPUT_REQUIRED`.

## Inputs Coding Agents Cannot Invent

Coding agents must request these inputs from their user when needed:

- Provider choice and model name.
- Provider API key and live tool API keys.
- Quota availability and provider billing state.
- Feedback from class discussion, debate, instructor audit, or another team.
- Confirmation that a public UI URL works from another device.
- Permission to merge a PR.
- Telegram confirmation or any action that changes external state.
- Final submission channel, naming rule, and deadline announced in class.

Agents must not fabricate these inputs in `REPORT.md`.

## Bootstrap

The masterplan and prompt files must be available on `main` before the parallel branches start.

Each member runs:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c develop/<member>
```

For the existing `develop/long` branch, Long updates it after the planning commit reaches `main`:

```bash
git fetch origin
git switch develop/long
git rebase origin/main
```

## Shared Contract

### Existing Tools

Existing tool names remain unchanged:

```text
clarify
timeline
social_search
lookup
fetch
format
send
policy
papers
paper_text
```

### New Tool

The required team-authored tool is named `dedupe`.

Purpose:

- Remove duplicate research items after items have already been collected.
- Preserve the first occurrence and original order.
- Match duplicates by normalized URL first.
- Fall back to normalized title when a usable URL is absent.
- Use no external API and create no external side effect.

Input:

```python
{"items": list[dict]}
```

Output:

```python
{
    "tool": "dedupe",
    "items": list[dict],
    "original_count": int,
    "deduplicated_count": int,
}
```

The declaration must say that `dedupe` is never an initial search tool.

### UI Contract

The UI must reuse `run_model_tool_loop` from `starter_v0/chat.py`.
It must display:

- Current artifact version.
- User request.
- Final assistant response.
- Round number.
- Tool name and arguments.
- Tool result or error.
- Transcript path or transcript identifier.

### Eval Contract

`starter_v0/data/eval_group.json` must contain exactly:

- 10 cases total.
- 5 single-turn cases using `query`.
- 5 multi-turn cases using `turns`.
- Unique IDs.
- `phase: "B"` for every case.
- An allowed `failure_type`.
- Either `expect.tool_calls` or `expect.no_tool`.
- `metadata.what_it_tests`.

## File Ownership

| Path | Owner |
|---|---|
| `starter_v0/artifacts/system_prompt.md` | Long |
| Existing core declarations in `starter_v0/artifacts/tools.yaml` | Long |
| `starter_v0/artifacts/version_log.csv` | Long |
| `starter_v0/runs/` and `starter_v0/analysis/` | Long during v0-v3 |
| `starter_v0/app.py` | Tấn |
| Streamlit line in `starter_v0/requirements.txt` | Tấn |
| `starter_v0/tools/dedupe/` | Chiến |
| `dedupe` registry entry in `starter_v0/tools/__init__.py` | Chiến |
| Appended `dedupe` block in `starter_v0/artifacts/tools.yaml` | Chiến |
| `starter_v0/data/eval_group.json` | An |
| `starter_v0/scripts/validate_submission.py` | Nghĩa |
| `starter_v0/artifacts/REPORT.md` | Nghĩa |

Only Long and Chiến modify `starter_v0/artifacts/tools.yaml`.
Long edits existing declarations only.
Chiến appends the `dedupe` declaration only.

## Parallel Build Phase

### Lane 1: Agent Quality

Long runs provider preflight and base v0.
After checkpoint approval, Long implements v1 and v2.
Long pauses before v3 until the new tool PR is merged.
Long then rebases on `main`, runs final v3 with the final tool set, and records final hashes.

### Lane 2: UI

Tấn builds and verifies the Streamlit UI independently.
The UI reads the current prompt and tool declarations at runtime.
The UI lane does not wait for prompt optimization or the new tool.

### Lane 3: New Tool

Chiến implements and tests `dedupe`.
The tool contract is frozen in this file.
Chiến does not wait for the UI, eval, or prompt lane.

### Lane 4: Group Eval

An authors and statically validates the 10 group cases.
The cases use existing core tools only.
The group eval lane does not wait for the new tool.

### Lane 5: Validation and Report

Nghĩa builds a standard-library submission validator and completes Report Part A.
Nghĩa pauses Report Part B until real runs, transcripts, and class feedback exist.
Nghĩa never invents missing evidence.

## Checkpoint Protocol

At every checkpoint, the coding agent must stop and return:

```text
[TEAM B1 CHECKPOINT]
Member:
Role:
Branch:
Checkpoint:
Status:
Completed:
Verification command:
Verification result:
Files changed:
Commit:
Blocked by:
Human input required:
Next action after CONTINUE:
```

Allowed statuses:

```text
CHECKPOINT_REACHED
READY_FOR_PR
CONTRACT_BLOCKED
HUMAN_INPUT_REQUIRED
READY_FOR_INTEGRATION
READY_TO_SUBMIT
```

## Chronological Flow

### Block 0: Planning

1. Merge this masterplan and the five prompts into `main`.
2. Confirm the five branch names.
3. Each member copies their prompt into their coding agent.

### Block 1: Parallel Start

1. Long checks provider access and runs v0.
2. Tấn builds the UI shell.
3. Chiến implements `dedupe`.
4. An writes the first five single-turn cases.
5. Nghĩa builds the validator and Report Part A.

### Block 2: First Stop

All five agents reach their first checkpoint.
Each agent reports evidence and stops.
Each member posts the concise status to the team process channel.

### Block 3: Parallel Completion

1. Long runs v1 and v2, then waits for the new tool merge.
2. Tấn completes trace rendering and transcript persistence.
3. Chiến registers and smoke-tests `dedupe`.
4. An completes all 10 cases and validates the 5/5 split.
5. Nghĩa completes the static validator and marks missing human evidence.

### Block 4: Initial PRs

Open PRs for:

1. `develop/chien`.
2. `develop/an`.
3. `develop/tan`.

The user reviews and authorizes merges.
Merge the new tool PR before Long starts v3.

### Block 5: Final v3

Long rebases `develop/long` on the updated `main`.
Long resolves only the expected `tools.yaml` integration if required.
Long runs final v3 and records the final prompt and tools hashes.
Long opens the agent-quality PR.

### Block 6: Report and Release

After the first four implementation PRs are merged, Nghĩa rebases on `main`.
Nghĩa runs static validation, base v3, group eval, UI smoke test, and the new tool smoke test.
Nghĩa fills Report Part B only from real evidence.
Nghĩa opens the release PR.

### Block 7: Final Gate

The final gate requires:

- Provider preflight passes.
- Core API smoke tests used by the demo pass.
- `v0`, `v1`, `v2`, and final `v3` evidence exists.
- Final v3 has zero provider-error cases for the reported suite.
- Group eval contains exactly 10 valid cases.
- Group eval run evidence exists.
- UI opens and shows tool traces.
- `dedupe` direct smoke test passes.
- Transcript evidence exists.
- Report Parts A and B contain no fabricated evidence.
- Secrets scan passes.
- Human class feedback is included only when supplied by a teammate.

## PR Rules

Each member commits only owned files.

Each member pushes:

```bash
git push -u origin HEAD
```

Each member creates a PR:

```bash
gh pr create --base main --head "$(git branch --show-current)" --fill
```

If GitHub CLI is unavailable or unauthenticated, the agent prints the push result and the exact compare URL.
The agent must not claim a PR exists without verifying its URL.

## Prompt Files

- Long: `agent-prompts/01-long-agent-quality.md`
- Tấn: `agent-prompts/02-tan-ui.md`
- Chiến: `agent-prompts/03-chien-new-tool.md`
- An: `agent-prompts/04-an-group-eval.md`
- Nghĩa: `agent-prompts/05-nghia-release.md`
