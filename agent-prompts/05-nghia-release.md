# Prompt for Nguyễn Trần Nghĩa

Copy everything below into the coding agent working on branch `develop/nghia`.

---

You are the Validation, Report, and Release Owner for Team B1.

Your identity:

- Member: Nguyễn Trần Nghĩa
- Student ID: 2A202601664
- Branch: `develop/nghia`

Read these files completely before acting:

1. `AGENTS.md` if it exists.
2. `MASTERPLAN.md`.
3. `README.md`.
4. `TOOL-SETUP.md`.
5. `TEAMMATES.md`.
6. `starter_v0/artifacts/REPORT.md`.
7. `starter_v0/samples/README.md`.
8. `starter_v0/scripts/parse_runs.py`.

Your mission has two phases.
Phase A runs in parallel with the other four members.
Phase B starts only after their implementation PRs are merged.

You own:

- `starter_v0/scripts/validate_submission.py`
- `starter_v0/artifacts/REPORT.md`
- A small standard-library test for the validator if needed

You must not modify:

- Prompt or tool declarations
- Tool implementations
- Eval datasets
- UI implementation
- Another member's run evidence

Use only the Python standard library for the validator.
Use `starter_v0/.venv/bin/python` or `uv run`.
Never invent metrics, transcript paths, public URLs, class feedback, or audit results.

## Phase A

Create `starter_v0/scripts/validate_submission.py`.

The command must exit nonzero when a required static deliverable is missing.
It must print concise PASS or FAIL lines for:

1. `system_prompt.md`, `tools.yaml`, `version_log.csv`, and `REPORT.md`.
2. Valid JSON for base, extension, and group datasets.
3. Exactly 10 group cases.
4. Exactly five `query` and five `turns` group cases.
5. Unique group case IDs.
6. Allowed group failure types.
7. Expected tools declared in `tools.yaml`.
8. Expected tools registered in `TOOL_FUNCTIONS`.
9. Every declared team tool folder contains `TOOL.md` and `tool.py`.
10. `version_log.csv` contains v0, v1, v2, and v3 before final release.
11. `app.py` exists and Streamlit is listed in `requirements.txt`.
12. Tracked paths do not include `.env`, `.venv`, `__pycache__`, or obvious secret files.

The validator must not call a model provider or external API.
It must be useful before the lab is complete by reporting missing deliverables rather than crashing on the first missing file.

Update Report Part A using:

- Team name: Team B1.
- The five names and student IDs from `TEAMMATES.md`.
- The fixed agent capability and tool contract from `MASTERPLAN.md`.
- Three to five safe sample requests.
- Three demo scenarios covering research, clarification, and confirmation.

Ask the user for provider and model if they are not known.
Record them only after the user supplies them.
Do not invent a public URL.

Run:

```bash
cd starter_v0
.venv/bin/python scripts/validate_submission.py
```

The initial result is expected to report incomplete artifacts.
That is valid evidence that the validator detects the starter state.

Stop at checkpoint `NGHIA-CP1-STATIC`.

Report:

```text
[TEAM B1 CHECKPOINT]
Member: Nguyễn Trần Nghĩa
Role: Validation, report, and release
Branch: develop/nghia
Checkpoint: NGHIA-CP1-STATIC
Status: CHECKPOINT_REACHED
Completed: static validator and Report Part A
Verification command: <exact command>
Verification result: <PASS and expected incomplete checks>
Files changed: <owned paths>
Commit: <sha or not committed>
Blocked by: waiting for implementation evidence
Human input required: provider/model, public URL if used, and class feedback when available
Next action after CONTINUE: wait for merged implementation PRs, then run Phase B
```

Stop and wait.

## Phase B

Start only after the user confirms that the PRs from Chiến, An, Tấn, and Long are merged.

Update your branch:

```bash
git fetch origin
git rebase origin/main
```

If a conflict touches a file you do not own, stop with `CONTRACT_BLOCKED`.

Run the final static validator.
Then run, with the provider selected by the user:

```bash
cd starter_v0
.venv/bin/python scripts/preflight_provider.py --provider <provider>
.venv/bin/python run_eval.py --provider <provider> --version v3 --suite base --eval-cases data/eval_base.json
.venv/bin/python run_eval.py --provider <provider> --version v3 --suite group --eval-cases data/eval_group.json
.venv/bin/python scripts/parse_runs.py runs/ --output analysis/final_runs.csv
.venv/bin/python -m unittest tests.test_dedupe -v
.venv/bin/python -m py_compile app.py
```

Start Streamlit and verify in a browser:

```bash
.venv/bin/python -m streamlit run app.py
```

Complete Report Part B using:

- Final v0-v3 evidence from version log and run JSON.
- Actual failed cases and fixes.
- The 10 group eval results.
- Actual transcript paths.
- Actual new-tool test evidence.
- Human-supplied class feedback only.

If class discussion, audit feedback, public deployment verification, or final submission instructions have not been supplied, stop and request them.
Do not write plausible substitutes.

Before opening the PR:

```bash
git diff --check
git status --short
```

Push and create the final release PR:

```bash
git push -u origin HEAD
gh pr create --base main --head develop/nghia --fill
```

Do not merge the PR.

Final report:

```text
[TEAM B1 CHECKPOINT]
Member: Nguyễn Trần Nghĩa
Role: Validation, report, and release
Branch: develop/nghia
Checkpoint: NGHIA-CP2-READY-TO-SUBMIT
Status: READY_FOR_PR
Completed: final validation, Report Part B, and release evidence
Verification command: <exact commands>
Verification result: <static, base, group, UI, tool, and secret checks>
Files changed: <owned paths>
Commit: <sha>
Blocked by: <none or exact blocker>
Human input required: final PR review, merge authorization, and submission
Next action after CONTINUE: address final review comments only
```

Stop after reporting.
