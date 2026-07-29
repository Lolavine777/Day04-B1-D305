# Prompt for Vũ Hữu An

Copy everything below into the coding agent working on branch `develop/an`.

---

You are the Group Eval Owner for Team B1.

Your identity:

- Member: Vũ Hữu An
- Student ID: 2A202601078
- Branch: `develop/an`

Read these files completely before acting:

1. `AGENTS.md` if it exists.
2. `MASTERPLAN.md`.
3. `starter_v0/data/eval_base.json`.
4. `starter_v0/data/eval_group.json`.
5. `starter_v0/samples/eval_group.schema.example.json`.
6. `starter_v0/run_eval.py`.
7. `starter_v0/artifacts/tools.yaml`.

Your mission is to author exactly 10 original group eval cases.

You own only:

- `starter_v0/data/eval_group.json`

You must not modify:

- `starter_v0/data/eval_base.json`
- `starter_v0/data/eval_research_extension.json`
- Prompt or tool declarations
- Tool implementations
- UI code
- Report files

Do not copy sample cases.
Do not copy base queries with only cosmetic word changes.
Use existing core tools only.
Do not require `dedupe`.
Do not require live Telegram sending.

Create these five single-turn capabilities with original Vietnamese wording:

1. Account timeline using an explicit handle and an explicit limit.
2. Top social posts for a topic with an explicit limit.
3. Web news with a month timeframe.
4. Missing URL that must call `clarify` with `response_type: "text"`.
5. A non-research request that expects `no_tool`.

Create these five multi-turn capabilities:

1. Correct an account and then correct the requested limit.
2. Switch from social search to web news while preserving the topic.
3. Supply a missing URL in a later turn.
4. Cancel a previous research request and ask a meta question that needs no tool.
5. Preserve a topic while the final turn requests both web news and social search.

Every case must contain:

- A unique ID prefixed with `B1G`.
- `phase: "B"`.
- One allowed `failure_type`.
- `expect.tool_calls` or `expect.no_tool`.
- `metadata.what_it_tests`.

For multi-turn cases:

- Use at least three turns.
- Make the final element a user turn.
- Ensure only the final user request is being graded.
- Include corrections that are unambiguous.

After the first five single-turn cases:

1. Parse the JSON.
2. Count the cases.
3. Confirm all five use `query`.
4. Stop at checkpoint `AN-CP1-SINGLE-TURN`.

Use the project virtual environment:

```bash
cd starter_v0
.venv/bin/python -c "import json; d=json.load(open('data/eval_group.json', encoding='utf-8')); assert len(d['cases'])==5; assert all('query' in c and 'turns' not in c for c in d['cases']); print('single-turn schema PASS')"
```

Report:

```text
[TEAM B1 CHECKPOINT]
Member: Vũ Hữu An
Role: Group eval design
Branch: develop/an
Checkpoint: AN-CP1-SINGLE-TURN
Status: CHECKPOINT_REACHED
Completed: five original single-turn cases
Verification command: <exact command>
Verification result: 5 single-turn cases parsed successfully
Files changed: starter_v0/data/eval_group.json
Commit: <sha or not committed>
Blocked by: <none or exact blocker>
Human input required: review coverage and originality
Next action after CONTINUE: add five multi-turn cases
```

Stop and wait for `CONTINUE`.

After approval:

1. Add the five multi-turn cases.
2. Validate exactly 10 total cases.
3. Validate a 5/5 split.
4. Validate unique IDs.
5. Validate allowed failure types.
6. Validate expected tool names against `tools.yaml`.
7. Do not run live group eval unless the user supplies provider access and explicitly asks.

Static validation:

```bash
cd starter_v0
.venv/bin/python -c "import json; d=json.load(open('data/eval_group.json', encoding='utf-8')); c=d['cases']; assert len(c)==10; assert sum('query' in x for x in c)==5; assert sum('turns' in x for x in c)==5; assert len({x['id'] for x in c})==10; print('group eval structure PASS')"
```

Before opening the PR:

```bash
git diff --check
git status --short
```

Push and create the PR:

```bash
git push -u origin HEAD
gh pr create --base main --head develop/an --fill
```

Do not merge the PR.

Final report:

```text
[TEAM B1 CHECKPOINT]
Member: Vũ Hữu An
Role: Group eval design
Branch: develop/an
Checkpoint: AN-CP2-READY-FOR-PR
Status: READY_FOR_PR
Completed: five single-turn and five multi-turn cases
Verification command: <exact commands>
Verification result: <counts, ID check, failure-type check, and tool-name check>
Files changed: starter_v0/data/eval_group.json
Commit: <sha>
Blocked by: <none or exact blocker>
Human input required: PR review
Next action after CONTINUE: address review comments only
```

Stop after reporting.
