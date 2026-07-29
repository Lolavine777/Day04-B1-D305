# Prompt for Đào Minh Chiến

Copy everything below into the coding agent working on branch `develop/chien`.

---

You are the New Tool Owner for Team B1.

Your identity:

- Member: Đào Minh Chiến
- Student ID: 2A202601184
- Branch: `develop/chien`

Read these files completely before acting:

1. `AGENTS.md` if it exists.
2. `MASTERPLAN.md`.
3. `starter_v0/tools/README.md`.
4. `starter_v0/tools/format/TOOL.md`.
5. `starter_v0/tools/format/tool.py`.
6. `starter_v0/tools/__init__.py`.
7. `starter_v0/artifacts/tools.yaml`.

Your mission is to add the required team-authored local tool named `dedupe`.

You own:

- `starter_v0/tools/dedupe/TOOL.md`
- `starter_v0/tools/dedupe/tool.py`
- The `dedupe` import and registry entry in `starter_v0/tools/__init__.py`
- The appended `dedupe` declaration in `starter_v0/artifacts/tools.yaml`
- `starter_v0/tests/test_dedupe.py`

You must not modify:

- Existing tool implementations
- Existing declarations in `starter_v0/artifacts/tools.yaml`
- `starter_v0/artifacts/system_prompt.md`
- Eval datasets
- UI code
- Report files

Use only the Python standard library.
Do not add dependencies.
Use `starter_v0/.venv/bin/python` or `uv run`.

Implement this exact contract:

```python
def dedupe_items(items: list[dict] | None = None) -> dict:
    ...
```

The returned object must contain:

```python
{
    "tool": "dedupe",
    "items": deduplicated_items,
    "original_count": original_count,
    "deduplicated_count": deduplicated_count,
}
```

Behavior:

1. Treat `None` as an empty list.
2. Preserve the first occurrence and input order.
3. Prefer normalized URL as the duplicate key.
4. Ignore a trailing slash when normalizing URLs.
5. Lowercase URL hostnames.
6. Use a whitespace-collapsed, case-insensitive title key when URL is missing.
7. Keep items that have neither URL nor title because no stable duplicate key exists.
8. Do not mutate input dictionaries.

Write `TOOL.md` with:

- `name: dedupe`
- `track: core`
- `kind: local_formatter`
- No required environment variables
- `side_effect: false`

Write standard-library `unittest` cases for:

- Duplicate URLs.
- URLs differing only by hostname case or trailing slash.
- Duplicate titles without URLs.
- Preservation of first occurrence and order.
- Empty and `None` input.
- Items without URL or title.

Run:

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_dedupe -v
```

Stop at checkpoint `CHIEN-CP1-IMPLEMENTED` before editing the registry or `tools.yaml`.

Report:

```text
[TEAM B1 CHECKPOINT]
Member: Đào Minh Chiến
Role: New local tool
Branch: develop/chien
Checkpoint: CHIEN-CP1-IMPLEMENTED
Status: CHECKPOINT_REACHED
Completed: dedupe implementation, TOOL.md, and unit tests
Verification command: <exact command>
Verification result: <test count and result>
Files changed: <paths>
Commit: <sha or not committed>
Blocked by: <none or exact blocker>
Human input required: contract review
Next action after CONTINUE: register and declare dedupe
```

Stop and wait for `CONTINUE`.

After approval:

1. Import `dedupe_items` in `starter_v0/tools/__init__.py`.
2. Add `"dedupe": dedupe_items` to `TOOL_FUNCTIONS`.
3. Append the `dedupe` declaration to the end of `starter_v0/artifacts/tools.yaml`.
4. State clearly that the tool is used only after research items already exist.
5. State clearly that it is not an initial search tool.
6. Run the unit tests again.
7. Run a direct registry smoke test.

Direct smoke test:

```bash
cd starter_v0
.venv/bin/python -c "from tools import TOOL_FUNCTIONS as T; r=T['dedupe']([{'title':'A','url':'https://example.com/'},{'title':'A copy','url':'https://example.com'}]); assert r['original_count']==2; assert r['deduplicated_count']==1; print(r)"
```

Before opening the PR:

```bash
git diff --check
git status --short
```

Push and create the PR:

```bash
git push -u origin HEAD
gh pr create --base main --head develop/chien --fill
```

Do not merge the PR.

Final report:

```text
[TEAM B1 CHECKPOINT]
Member: Đào Minh Chiến
Role: New local tool
Branch: develop/chien
Checkpoint: CHIEN-CP2-READY-FOR-PR
Status: READY_FOR_PR
Completed: implementation, tests, registry, declaration, and smoke test
Verification command: <exact commands>
Verification result: <test and smoke-test evidence>
Files changed: <owned paths>
Commit: <sha>
Blocked by: <none or exact blocker>
Human input required: PR review and merge authorization before Long runs v3
Next action after CONTINUE: address review comments only
```

Stop after reporting.
