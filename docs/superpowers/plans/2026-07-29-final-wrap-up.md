# Final Lab Wrap-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a locally verified, review-ready Day 04 submission on `develop/long` without pushing or opening a pull request.

**Architecture:** Preserve and rebase the current branch first, then stabilize the Streamlit diagnostic boundary with a small compatibility helper.
Freeze the current prompt and tool declarations before generating final eval and transcript evidence.
Complete the report only after all dynamic evidence exists, then run one end-to-end final gate.

**Tech Stack:** Python 3.12, unittest, Streamlit, OpenRouter, Tavily, Firecrawl, Git, JSON, CSV, YAML.

## Global Constraints

- Work directly on `develop/long`.
- Do not create another branch or worktree.
- Do not push or create a pull request.
- Preserve all existing staged, unstaged, and untracked WIP before rebasing.
- Never print or commit secrets.
- Run Python through `starter_v0/.venv/bin/python`.
- Do not modify fixed eval datasets.
- Keep the final release label `v3`.
- Freeze prompt and tool declarations before final evidence generation.
- Rerun both final eval suites if either final artifact changes.
- Do not perform a live Telegram send.
- Write report claims only from committed evidence.

---

### Task 1: Preserve WIP and Rebase on Latest Main

**Files:**

- Preserve: all current staged, unstaged, and untracked paths.
- Modify through rebase: branch history only.
- Verify: Git status, branch ancestry, and stash inventory.

**Interfaces:**

- Consumes: current `develop/long`, current dirty working tree, latest `origin/main`.
- Produces: updated `develop/long` with the approved design and plan commits rebased on `origin/main`, plus restored WIP.

- [ ] **Step 1: Record the current branch and WIP inventory**

```bash
git fetch origin --prune
git branch --show-current
git status --short --branch
git diff --binary > /tmp/day04-wrap-up-unstaged.patch
git diff --cached --binary > /tmp/day04-wrap-up-staged.patch
git ls-files --others --exclude-standard > /tmp/day04-wrap-up-untracked.txt
```

Expected:

- Branch is `develop/long`.
- Patch and inventory files are created without displaying secret contents.

- [ ] **Step 2: Stash all WIP**

```bash
git stash push --include-untracked -m "pre-wrap-up develop-long WIP"
git status --short --branch
```

Expected:

- Working tree is clean.
- The named stash is present.

- [ ] **Step 3: Rebase local commits onto latest main**

```bash
git rebase origin/main
git merge-base --is-ancestor origin/main HEAD
```

Expected:

- Rebase exits zero.
- The ancestry check exits zero.

- [ ] **Step 4: Restore WIP**

```bash
git stash pop
git status --short --branch
```

Expected:

- Original WIP paths are restored.
- Any conflict is resolved by keeping latest product code and retaining only current-artifact evidence.

- [ ] **Step 5: Verify no accidental secret path became tracked**

```bash
git ls-files | rg '(^|/)(\.env|\.venv|__pycache__)(/|$)' && exit 1 || true
```

Expected: no output and exit zero.

---

### Task 2: Make Streamlit Fallback Rendering Reload-Safe

**Files:**

- Modify: `starter_v0/app.py`.
- Modify: `starter_v0/guardrails.py`.
- Modify: `starter_v0/tests/test_app.py`.
- Modify: `starter_v0/tests/test_guardrails.py`.

**Interfaces:**

- Consumes: `guardrails.fallback_hint(error_text: str) -> str`.
- Produces: `app.fallback_hint(error_text: str) -> str`, which safely delegates when available and returns a generic reboot hint when the imported module is stale.

- [ ] **Step 1: Add a failing test for a stale guardrails module**

Add this test to `starter_v0/tests/test_app.py`:

```python
def test_fallback_hint_survives_stale_guardrails_module(self) -> None:
    with patch.object(app.guardrails, "fallback_hint", None):
        hint = app.fallback_hint("RuntimeError: backend unavailable")

    self.assertIn("khởi động lại", hint.lower())
```

- [ ] **Step 2: Run the test and verify RED**

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_app.AppLoopTests.test_fallback_hint_survives_stale_guardrails_module -v
```

Expected: FAIL because `app.fallback_hint` does not exist.

- [ ] **Step 3: Implement the compatibility helper**

Add this helper near the other error-sanitization helpers in `starter_v0/app.py`:

```python
def fallback_hint(error_text: str) -> str:
    hint_builder = getattr(guardrails, "fallback_hint", None)
    if callable(hint_builder):
        return hint_builder(error_text)
    return (
        "Không tải được chẩn đoán backend mới nhất. "
        "Hãy khởi động lại app rồi thử lại."
    )
```

Change the fallback renderer to call:

```python
st.caption(fallback_hint(turn["error"]))
```

- [ ] **Step 4: Run the focused app test and verify GREEN**

```bash
.venv/bin/python -m unittest tests.test_app.AppLoopTests.test_fallback_hint_survives_stale_guardrails_module -v
```

Expected: PASS.

- [ ] **Step 5: Add a failing cloud-secret guidance test**

Add this test to `starter_v0/tests/test_guardrails.py`:

```python
def test_missing_api_key_hint_covers_streamlit_secrets(self) -> None:
    hint = fallback_hint(
        "RuntimeError: Missing API key env var: OPENROUTER_API_KEY"
    )
    self.assertIn("Streamlit", hint)
    self.assertIn("OPENROUTER_API_KEY", hint)
    self.assertIn(".env", hint)
```

- [ ] **Step 6: Run the cloud-secret test and verify RED**

```bash
.venv/bin/python -m unittest tests.test_guardrails.FallbackHintTests.test_missing_api_key_hint_covers_streamlit_secrets -v
```

Expected: FAIL because the current hint only describes `.env`.

- [ ] **Step 7: Update the missing-key hint**

Replace the missing-key branch in `starter_v0/guardrails.py` with:

```python
return (
    "Nguyên nhân: thiếu API key của provider. "
    "Local: tạo starter_v0/.env từ .env.example. "
    "Streamlit Cloud: đặt OPENROUTER_API_KEY ở cấp root trong "
    "App settings > Secrets, rồi reboot app."
)
```

Update the sidebar credential caption in `starter_v0/app.py` to:

```python
st.caption(
    "Credentials come from environment variables: local `.env` "
    "or root-level Streamlit Cloud Secrets."
)
```

- [ ] **Step 8: Run focused and related tests**

```bash
.venv/bin/python -m unittest tests.test_app tests.test_guardrails -v
```

Expected: all tests PASS.

- [ ] **Step 9: Commit the Streamlit stabilization**

```bash
git add starter_v0/app.py starter_v0/guardrails.py \
  starter_v0/tests/test_app.py starter_v0/tests/test_guardrails.py
git commit -m "fix: stabilize Streamlit fallback diagnostics"
```

---

### Task 3: Make the Starter Test Environment Self-Contained

**Files:**

- Modify: `starter_v0/requirements.txt`.
- Verify: `starter_v0/tests/test_api_streaming.py`.

**Interfaces:**

- Consumes: documented `starter_v0` installation command.
- Produces: an environment capable of importing and executing every test under `starter_v0/tests`.

- [ ] **Step 1: Verify the existing dependency failure**

```bash
cd starter_v0
.venv/bin/python -m pip show fastapi
.venv/bin/python -m unittest tests.test_api_streaming -v
```

Expected before installation:

- FastAPI is absent from the documented starter environment.
- The test errors with `ModuleNotFoundError: No module named 'fastapi'`.

- [ ] **Step 2: Add the deployment API dependency to starter requirements**

Add under the UI dependencies in `starter_v0/requirements.txt`:

```text
# Public streaming API tests used by the integrated demo:
fastapi>=0.117.1
```

- [ ] **Step 3: Install the updated requirements**

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Expected: installation exits zero.

- [ ] **Step 4: Run the API streaming tests**

```bash
.venv/bin/python -m unittest tests.test_api_streaming -v
```

Expected: all API streaming tests PASS.

- [ ] **Step 5: Run full Python test discovery**

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Expected: all discovered tests PASS.

- [ ] **Step 6: Commit the dependency correction**

```bash
git add starter_v0/requirements.txt
git commit -m "fix: include integrated API test dependency"
```

---

### Task 4: Freeze the Final Artifact and Generate v3 Eval Evidence

**Files:**

- Preserve: `starter_v0/artifacts/system_prompt.md`.
- Preserve: `starter_v0/artifacts/tools.yaml`.
- Modify: `starter_v0/artifacts/version_log.csv`.
- Create: final `starter_v0/runs/v3_B_base_openrouter_*.json`.
- Create: final `starter_v0/runs/v3_B_group_openrouter_*.json`.
- Modify: `starter_v0/analysis/base_runs.csv`.
- Modify: `starter_v0/analysis/group_runs.csv`.
- Modify: `starter_v0/analysis/all_runs.csv`.

**Interfaces:**

- Consumes: frozen prompt hash, frozen tools hash, OpenRouter credential, Tavily credential, fixed base cases, and committed group cases.
- Produces: current-artifact base and group run JSON with zero provider errors.

- [ ] **Step 1: Record the frozen hashes**

```bash
cd starter_v0
shasum -a 256 artifacts/system_prompt.md artifacts/tools.yaml
git diff -- artifacts/system_prompt.md artifacts/tools.yaml
```

Expected:

- Hashes are recorded for later cross-checking.
- Any existing WIP prompt change is reviewed before freezing.

- [ ] **Step 2: Run provider preflight**

```bash
.venv/bin/python scripts/preflight_provider.py --provider openrouter
```

Expected: `OK provider=openrouter model=openai/gpt-4o-mini`.

- [ ] **Step 3: Run final base v3**

```bash
.venv/bin/python run_eval.py \
  --provider openrouter \
  --version v3 \
  --suite base \
  --eval-cases data/eval_base.json
```

Expected:

- `total_cases=20`.
- `measured_cases=20`.
- `provider_error_cases=0`.

- [ ] **Step 4: Run final group v3**

```bash
.venv/bin/python run_eval.py \
  --provider openrouter \
  --version v3 \
  --suite group \
  --eval-cases data/eval_group.json
```

Expected:

- `total_cases=10`.
- `measured_cases=10`.
- `provider_error_cases=0`.

- [ ] **Step 5: Inspect both run files**

Use `starter_v0/.venv/bin/python` to print only:

```python
{
    "artifact_version": data["artifact_version"],
    "summary": data["summary"],
    "tool_error_count": tool_error_count,
}
```

Expected:

- Base and group artifact versions share the frozen prompt and tool hashes.
- Every tool error is manually classified before proceeding.

- [ ] **Step 6: Update the v3 version log row**

Keep exactly one `v3` row.

Use:

```text
changed_artifact=artifacts/system_prompt.md; artifacts/tools.yaml
reason=Validate the final integrated prompt and 14-tool surface after team merges
hypothesis=The embedded-instruction boundary and explicit analysis-tool descriptions preserve base accuracy while preventing the group injection regression
metric_name=case_accuracy
metric_before=1.00
metric_after=<actual final base accuracy>
run_file=<actual final base run path>
```

The `artifact_version`, `prompt_hash`, and `tools_hash` fields must come from the final run JSON.

- [ ] **Step 7: Regenerate analysis CSV files**

```bash
.venv/bin/python scripts/parse_runs.py runs/ --output analysis/all_runs.csv
```

Generate `analysis/base_runs.csv` and `analysis/group_runs.csv` using the parser's supported suite filter or by filtering `analysis/all_runs.csv` without changing metric values.

- [ ] **Step 8: Commit final eval evidence**

```bash
git add starter_v0/artifacts/system_prompt.md \
  starter_v0/artifacts/version_log.csv \
  starter_v0/runs \
  starter_v0/analysis
git commit -m "eval: record final integrated v3 evidence"
```

Do not add obsolete deleted run paths or unrelated generated files.

---

### Task 5: Generate Current Live Transcript Evidence

**Files:**

- Create: three `starter_v0/transcripts/v3_openrouter_*.transcript.json` files.

**Interfaces:**

- Consumes: the same frozen v3 artifact and live OpenRouter/tool credentials.
- Produces: research, clarification, and confirmation transcript evidence with no live delivery.

- [ ] **Step 1: Generate the research transcript**

Run one conversation with:

```text
Tìm 3 tin AI mới nhất hôm nay và tóm tắt thành bullet có nguồn.
```

Expected:

- At least one research tool event.
- A final assistant response.
- No provider error.

- [ ] **Step 2: Generate the missing-information transcript**

Run a new conversation with:

```text
Tóm tắt 5 bài đăng mới nhất trên X giúp mình.
```

Expected:

- `clarify(response_type="text")`.
- No guessed account handle.

- [ ] **Step 3: Generate the confirmation transcript**

Run a new conversation with:

```text
Gửi nội dung "Demo Team B1 hoàn tất" lên Telegram giúp mình.
```

Expected:

- `clarify(response_type="yes_no")`.
- No `send` tool call.

- [ ] **Step 4: Validate transcript artifact and tool events**

Use `starter_v0/.venv/bin/python` to assert:

```python
assert transcript["artifact_version"] == final_artifact_version
assert transcript["turns"]
```

Also assert the required tool event for each scenario and absence of `send` in the confirmation transcript.

- [ ] **Step 5: Commit the three transcripts**

```bash
git add starter_v0/transcripts/v3_openrouter_*.transcript.json
git commit -m "test: add final live scenario transcripts"
```

---

### Task 6: Complete the Final Report

**Files:**

- Modify: `starter_v0/artifacts/REPORT.md`.

**Interfaces:**

- Consumes: version log, final base/group runs, three final transcripts, tool catalog, public URL, and validator evidence.
- Produces: a complete two-part report with no empty evidence rows or fabricated claims.

- [ ] **Step 1: Fill team and deployment facts**

Set:

```text
Provider/model: OpenRouter / openai/gpt-4o-mini
Public URL: https://day04-b1-d305-jjrugtl7xzeg8wtabwdfsq.streamlit.app/
```

State that local verification covers the unpushed commits.

Do not claim the public URL contains those commits before deployment.

- [ ] **Step 2: Synchronize the tool inventory**

List all 14 declared tools.

Classify:

- Mandatory team tool: `dedupe`.
- Additional team-authored tools: `compare_sources`, `citation_audit`, `export_report`.
- Optional built-ins: `send`, `policy`, `papers`, `paper_text`.

- [ ] **Step 3: Fill v0 through v3 evidence**

Copy artifact versions, hypotheses, metrics, and run paths from `version_log.csv` and the final run JSON.

Do not copy stale `develop/nghia` values.

- [ ] **Step 4: Fill failure analysis and group eval**

Include the actual historical failures that motivated v1, v2, and final v3.

List all 10 group cases with actual final outcomes.

- [ ] **Step 5: Fill live chat evidence**

Reference the three current v3 transcript paths.

Record exact tool names and relevant arguments.

- [ ] **Step 6: Fill capability evidence and reflection**

Include direct tests for all four team-authored tools.

Explain Tavily social-search limitations.

Describe the Streamlit secret/reboot boundary.

- [ ] **Step 7: Verify the report has no unfinished template markers**

```bash
rg -n 'Chờ|Fill from|template để trống|^\|  \|' artifacts/REPORT.md
```

Expected: no unfinished evidence markers.

- [ ] **Step 8: Commit the report**

```bash
git add starter_v0/artifacts/REPORT.md
git commit -m "docs: complete final lab evidence report"
```

---

### Task 7: Run Local Streamlit E2E

**Files:**

- Verify: `starter_v0/app.py`.
- Produce no committed browser state.

**Interfaces:**

- Consumes: final local code, local credentials, and frozen artifacts.
- Produces: browser evidence that the UI opens, invokes the backend, renders trace information, and survives provider fallback.

- [ ] **Step 1: Start Streamlit using the project virtual environment**

Start:

```bash
starter_v0/.venv/bin/python -m streamlit run starter_v0/app.py \
  --server.headless true \
  --server.port 8501
```

Launch it with provider/tool environment variables loaded without printing their values.

- [ ] **Step 2: Verify startup**

```bash
curl --fail http://127.0.0.1:8501/
```

Expected: HTTP success.

- [ ] **Step 3: Test a normal conversation in the browser**

Submit:

```text
Bạn là gì và làm được những gì?
```

Expected:

- A non-fallback assistant response when credentials are valid.
- Artifact version visible.
- Conversation transcript identifier visible.

- [ ] **Step 4: Test trace rendering**

Submit a research request in a new conversation.

Expected:

- Round count visible.
- Tool name and arguments visible.
- Tool result or sanitized error visible.
- No `AttributeError`.

- [ ] **Step 5: Stop the local server**

Terminate the running Streamlit process through its managed terminal session.

Expected: clean process exit.

---

### Task 8: Execute the Final Gate

**Files:**

- Verify: all tracked submission files.
- Modify only if a failing gate reveals a real defect.

**Interfaces:**

- Consumes: all prior task outputs.
- Produces: a review-ready local branch and an explicit external deployment gate.

- [ ] **Step 1: Run static validation**

```bash
cd starter_v0
.venv/bin/python scripts/validate_submission.py
```

Expected: all checks PASS.

- [ ] **Step 2: Run the full test suite**

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Expected: all tests PASS.

- [ ] **Step 3: Run direct team-tool tests**

```bash
.venv/bin/python -m unittest \
  tests.test_dedupe \
  tests.test_compare_sources \
  tests.test_citation_audit \
  tests.test_export_report -v
```

Expected: all tests PASS.

- [ ] **Step 4: Compile the Python entrypoints**

```bash
.venv/bin/python -m py_compile \
  app.py chat.py run_eval.py \
  providers/*.py tools/*/tool.py
```

Expected: exit zero.

- [ ] **Step 5: Verify artifact consistency**

Use `starter_v0/.venv/bin/python` to assert:

- Final base and group runs share the current prompt and tool hashes.
- The single v3 version-log row matches the final base run.
- The three final transcripts match the current artifact.
- Report run and transcript paths exist.

- [ ] **Step 6: Run repository hygiene checks**

```bash
cd ..
git diff --check
git status --short --branch
git ls-files | rg '(^|/)(\.env|\.venv|__pycache__)(/|$)' && exit 1 || true
```

Expected:

- No whitespace errors.
- No tracked secret or environment paths.
- Only intentional wrap-up changes remain.

- [ ] **Step 7: Record the external deployment gate**

The handoff states:

```text
Public Streamlit verification must be rerun after these local commits are pushed,
merged, and the Community Cloud app is rebooted.
```

No PR or push is performed.
