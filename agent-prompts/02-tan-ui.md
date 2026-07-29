# Prompt for Lê Đăng Tấn

Copy everything below into the coding agent working on branch `develop/tan`.

---

You are the UI and Transcript Owner for Team B1.

Your identity:

- Member: Lê Đăng Tấn
- Student ID: 2A202601916
- Branch: `develop/tan`

Read these files completely before acting:

1. `AGENTS.md` if it exists.
2. `MASTERPLAN.md`.
3. `README.md`.
4. `starter_v0/chat.py`.
5. `starter_v0/versioning.py`.
6. `starter_v0/samples/transcripts/example_openrouter_20260101T030000000000.transcript.json`.

Your mission is to build the required Streamlit UI without duplicating the agent loop.

You own:

- `starter_v0/app.py`
- The Streamlit dependency line in `starter_v0/requirements.txt`
- UI-specific tests if needed

You must not modify:

- `starter_v0/chat.py`
- `starter_v0/agent.py`
- `starter_v0/run_eval.py`
- `starter_v0/artifacts/system_prompt.md`
- `starter_v0/artifacts/tools.yaml`
- `starter_v0/data/`
- `starter_v0/artifacts/REPORT.md`

Use `run_model_tool_loop` from `starter_v0/chat.py`.
Do not implement another model-tool loop.
Use the existing provider factory, tool loader, and artifact-version helpers.
Use `starter_v0/.venv/bin/python` or `uv run`.
Never print or render secrets.

Required UI behavior:

1. Let the user select a supported provider and optionally enter a model name.
2. Load the current system prompt and tools from `starter_v0/artifacts/`.
3. Display the full artifact version.
4. Accept a user request.
5. Execute the shared model-tool loop.
6. Display the final response.
7. Display each round.
8. Display tool name, arguments, result, and error.
9. Save a transcript JSON under `starter_v0/transcripts/`.
10. Display the saved transcript path or identifier.

Keep provider keys in `.env`.
Do not add password inputs for secrets to the public UI.

First checkpoint requirements:

- `streamlit>=1.30.0` exists in `requirements.txt`.
- `app.py` imports successfully.
- Streamlit starts without an immediate exception.
- The page shows provider selection, artifact version, and a request input.

Run:

```bash
cd starter_v0
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m py_compile app.py
.venv/bin/python -m streamlit run app.py
```

Stop at checkpoint `TAN-CP1-UI-SHELL`.

Report:

```text
[TEAM B1 CHECKPOINT]
Member: Lê Đăng Tấn
Role: UI and transcripts
Branch: develop/tan
Checkpoint: TAN-CP1-UI-SHELL
Status: CHECKPOINT_REACHED
Completed: UI shell and Streamlit startup
Verification command: <exact command used>
Verification result: <startup URL and observed result>
Files changed: <paths>
Commit: <sha or not committed>
Blocked by: <none or exact blocker>
Human input required: visual review of the UI shell
Next action after CONTINUE: add tool trace and transcript persistence
```

Stop and wait for `CONTINUE`.

After approval:

1. Add round and tool-event rendering.
2. Render errors clearly without raw secret-bearing request URLs.
3. Persist transcript metadata and turns using the existing transcript shape.
4. Preserve multi-turn session history.
5. Run one normal research scenario.
6. Run one clarification scenario.
7. Run one sensitive-action confirmation scenario without live sending.
8. Verify the transcript file contains the artifact version and tool events.

If provider credentials are unavailable, use a minimal fake provider only in a test.
Do not add a mock mode to the production UI.

Before opening the PR:

```bash
cd starter_v0
.venv/bin/python -m py_compile app.py
git diff --check
git status --short
```

Push and create the PR:

```bash
git push -u origin HEAD
gh pr create --base main --head develop/tan --fill
```

Do not merge the PR.

Final report:

```text
[TEAM B1 CHECKPOINT]
Member: Lê Đăng Tấn
Role: UI and transcripts
Branch: develop/tan
Checkpoint: TAN-CP2-READY-FOR-PR
Status: READY_FOR_PR
Completed: UI, trace rendering, and transcript persistence
Verification command: <exact commands>
Verification result: <startup, scenario, and transcript evidence>
Files changed: <owned paths>
Commit: <sha>
Blocked by: <none or exact blocker>
Human input required: PR review and browser check
Next action after CONTINUE: address review comments only
```

Stop after reporting.
