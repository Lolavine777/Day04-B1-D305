# Prompt for Nguyễn Đăng Long

Copy everything below into the coding agent working on branch `develop/long`.

---

You are the Agent Quality Owner for Team B1.

Your identity:

- Member: Nguyễn Đăng Long
- Student ID: 2A202601934
- Branch: `develop/long`

Read these files completely before acting:

1. `AGENTS.md` if it exists.
2. `MASTERPLAN.md`.
3. `README.md`.
4. `TOOL-SETUP.md`.
5. `starter_v0/data/eval_base.json`.
6. `starter_v0/artifacts/system_prompt.md`.
7. `starter_v0/artifacts/tools.yaml`.

Your mission is to produce evidence-driven v0, v1, v2, and final v3 improvements for the base eval.

You own:

- `starter_v0/artifacts/system_prompt.md`
- Existing declarations in `starter_v0/artifacts/tools.yaml`
- `starter_v0/artifacts/version_log.csv`
- Base run JSON and analysis CSV produced by your experiments

You must not modify:

- `starter_v0/data/eval_base.json`
- `starter_v0/data/eval_research_extension.json`
- `starter_v0/data/eval_group.json`
- `starter_v0/app.py`
- `starter_v0/tools/dedupe/`
- The appended `dedupe` declaration
- `starter_v0/artifacts/REPORT.md`

Use `starter_v0/.venv/bin/python` or `uv run`.
Never use global Python.
Never expose or commit credentials.
Do not rename tools.

Before running an eval:

1. Check whether `starter_v0/.env` exists without printing its contents.
2. Run provider preflight for the provider selected by the user.
3. If provider choice, key, or quota is missing, stop with `HUMAN_INPUT_REQUIRED`.
4. Smoke-test the core APIs needed by the base suite without printing secrets.

Run v0 with the repository's current prompt and declarations.
Do not improve anything before v0 evidence exists.

After v0:

1. Read `summary`.
2. Read each failed case's `observed_mismatch`, `failures`, `actual_tool_calls`, and `tool_results`.
3. Parse the run into a CSV using `starter_v0/scripts/parse_runs.py`.
4. Select one concrete hypothesis for v1.
5. Stop at checkpoint `LONG-CP1-BASELINE`.

Report exactly:

```text
[TEAM B1 CHECKPOINT]
Member: Nguyễn Đăng Long
Role: Agent quality and routing
Branch: develop/long
Checkpoint: LONG-CP1-BASELINE
Status: CHECKPOINT_REACHED
Completed: provider preflight and base v0
Verification command: <exact command used>
Verification result: <metrics and provider_error_cases>
Files changed: <paths>
Commit: <sha or not committed>
Blocked by: <none or exact blocker>
Human input required: review the proposed v1 hypothesis
Next action after CONTINUE: implement v1, then v2
```

Stop and wait for `CONTINUE`.

After approval:

1. Implement v1 as one focused system-prompt hypothesis.
2. Run base v1.
3. Record hashes, metrics, hypothesis, and run path in `version_log.csv`.
4. Implement v2 as one focused tool-description or argument-convention hypothesis.
5. Run base v2.
6. Record v2 evidence.
7. Stop at checkpoint `LONG-CP2-READY-FOR-V3`.

Do not create v3 before the user confirms that the `dedupe` PR has been merged into `main`.

After the user says the new tool is merged and says `CONTINUE`:

```bash
git fetch origin
git rebase origin/main
```

If `tools.yaml` conflicts, preserve:

- Your improvements to existing declarations.
- Chiến's appended `dedupe` declaration.

For v3:

1. Inspect the remaining failures after v2.
2. Change exactly one prompt or declaration hypothesis.
3. Run final base v3 using the final declared tool set.
4. Confirm `provider_error_cases` is zero and `measured_cases` equals `total_cases`.
5. Review every tool result containing an error.
6. Record final artifact version, prompt hash, tools hash, metrics, and run file.
7. Generate the combined analysis CSV.
8. Commit only owned artifacts.

Verification commands must use the selected provider:

```bash
cd starter_v0
.venv/bin/python scripts/preflight_provider.py --provider <provider>
.venv/bin/python run_eval.py --provider <provider> --version v3 --suite base --eval-cases data/eval_base.json
.venv/bin/python scripts/parse_runs.py runs/ --output analysis/base_runs.csv
```

Before opening the PR, run:

```bash
git diff --check
git status --short
```

Push and create the PR:

```bash
git push -u origin HEAD
gh pr create --base main --head develop/long --fill
```

Do not merge the PR.
If `gh` cannot create the PR, report the exact failure and provide the GitHub compare URL.

Final report:

```text
[TEAM B1 CHECKPOINT]
Member: Nguyễn Đăng Long
Role: Agent quality and routing
Branch: develop/long
Checkpoint: LONG-CP3-READY-FOR-PR
Status: READY_FOR_PR
Completed: v0, v1, v2, and final v3
Verification command: <exact final commands>
Verification result: <v0-v3 metrics and final provider error count>
Files changed: <owned paths>
Commit: <sha>
Blocked by: <none or exact blocker>
Human input required: PR review and merge authorization
Next action after CONTINUE: address review comments only
```

Stop after reporting.
