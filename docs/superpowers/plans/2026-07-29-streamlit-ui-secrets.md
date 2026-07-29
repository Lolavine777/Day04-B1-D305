# Streamlit Research Cockpit And Secrets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Ship a readable Streamlit research cockpit with explicit root-level Secrets guidance and a tested, value-safe configuration resolver.

**Architecture:** Keep the existing agent loop and artifact contracts unchanged.
Add a small configuration module that resolves exact uppercase provider and tool names from the process environment or root-level Streamlit Secrets, then expose only boolean status data to the UI.
Refactor the existing `app.py` theme and layout in place so transcripts, traces, fallback behavior, and downloads continue to use the current functions.

**Tech Stack:** Python 3, Streamlit, unittest, existing `starter_v0/.venv`, HTML/CSS injected through `st.markdown`.

## Global Constraints

- Never commit or print a credential value.
- Root-level Streamlit Secrets names are case-sensitive and must match the exact uppercase environment variables.
- `RAPIDAPI_KEY` and `RAPIDAPI_TWITTER_HOST` are not supported.
- Preserve the current model-tool loop, prompt, tools, evaluations, transcripts, artifact hashes, and fallback mode.
- Do not add a frontend framework or a new UI dependency.
- Use `starter_v0/.venv/bin/python` for every Python command.
- Keep the `.env.example` file names-only.
- Run tests, compile checks, `git diff --check`, and a tracked-secret scan before claiming completion.
- Work directly on `develop/long`; do not create another branch, push, or open a PR until implementation verification is complete.

## File Map

- Create: `starter_v0/configuration.py` for exact-name secret resolution and boolean status summaries.
- Modify: `starter_v0/app.py` for Streamlit secret hydration, theme tokens, layout hierarchy, setup panel, and status rendering.
- Modify: `starter_v0/guardrails.py` for actionable setup copy that matches the UI.
- Modify: `starter_v0/tests/test_configuration.py` for resolver tests.
- Modify: `starter_v0/tests/test_guardrails.py` for setup-copy regression tests.
- Modify: `starter_v0/tests/test_app.py` only if a pure helper extracted from the UI needs coverage.
- Modify: `starter_v0/artifacts/REPORT.md` only after local E2E verification, to record the new UI behavior without claiming public deployment verification.

---

### Task 1: Add the failing configuration tests

**Files:**
- Create: `starter_v0/tests/test_configuration.py`
- Create: `starter_v0/configuration.py` as an empty module so imports resolve during test collection.

**Interfaces:**
- `configuration.resolve_secrets(secret_source: Mapping[str, Any] | None = None, environ: MutableMapping[str, str] | None = None) -> dict[str, bool]`
- `configuration.provider_secret_name(provider_name: str) -> str`
- `configuration.configured_secret_names(...) -> tuple[str, ...]`

- [ ] **Step 1: Write the failing tests**

```python
import os
import unittest
from unittest.mock import patch

from configuration import configured_secret_names, provider_secret_name, resolve_secrets


class ConfigurationTests(unittest.TestCase):
    def test_root_level_streamlit_secret_hydrates_exact_environment_name(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status = resolve_secrets({"OPENROUTER_API_KEY": "new-key"})
        self.assertTrue(status["OPENROUTER_API_KEY"])
        self.assertEqual(os.environ["OPENROUTER_API_KEY"], "new-key")

    def test_existing_environment_value_wins_over_streamlit_secret(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "local-key"}, clear=True):
            resolve_secrets({"OPENROUTER_API_KEY": "cloud-key"})
        self.assertEqual(os.environ["OPENROUTER_API_KEY"], "local-key")

    def test_lowercase_alias_is_not_accepted(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status = resolve_secrets({"openrouter_api_key": "wrong-case"})
        self.assertFalse(status["OPENROUTER_API_KEY"])
        self.assertNotIn("OPENROUTER_API_KEY", os.environ)

    def test_missing_secret_source_is_safe(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status = resolve_secrets(None)
        self.assertFalse(status["OPENROUTER_API_KEY"])

    def test_status_never_contains_secret_values(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "secret-value"}, clear=True):
            status = resolve_secrets({})
        self.assertTrue(status["OPENROUTER_API_KEY"])
        self.assertFalse(status["TAVILY_API_KEY"])
        self.assertFalse(status["FIRECRAWL_API_KEY"])
        self.assertNotIn("secret-value", repr(status))

    def test_provider_and_tool_names_are_stable(self) -> None:
        self.assertEqual(provider_secret_name("openrouter"), "OPENROUTER_API_KEY")
        self.assertEqual(configured_secret_names("openrouter"), ("OPENROUTER_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_configuration -v
```

Expected: collection or import failure because the resolver functions do not exist yet.

### Task 2: Implement the minimal secret resolver

**Files:**
- Modify: `starter_v0/configuration.py`
- Modify: `starter_v0/app.py` to safely read `st.secrets` and call the resolver before rendering status or creating a provider.

**Interfaces:**
- The resolver returns only `{secret_name: bool}` status data.
- It accepts a plain mapping in tests and can safely receive `st.secrets` in the Streamlit process.

- [ ] **Step 1: Implement exact-name resolution**

```python
import os
from collections.abc import Mapping, MutableMapping
from typing import Any

PROVIDER_SECRET_NAMES = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
TOOL_SECRET_NAMES = ("TAVILY_API_KEY", "FIRECRAWL_API_KEY")


def provider_secret_name(provider_name: str) -> str:
    return PROVIDER_SECRET_NAMES[provider_name]


def configured_secret_names(provider_name: str) -> tuple[str, ...]:
    return (provider_secret_name(provider_name), *TOOL_SECRET_NAMES)


def resolve_secrets(
    secret_source: Mapping[str, Any] | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, bool]:
    target = environ if environ is not None else os.environ
    names = ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", *TOOL_SECRET_NAMES)
    for name in names:
        if target.get(name):
            continue
        if secret_source is None:
            continue
        value = secret_source.get(name)
        if isinstance(value, str) and value.strip():
            target[name] = value.strip()
    return {name: bool(target.get(name)) for name in names}
```

The production caller in `app.py` must wrap access to `st.secrets` in a narrow exception handler so a missing local secrets file remains a normal state.

- [ ] **Step 2: Call resolution in the Streamlit import path**

`app.py` will call a helper that safely obtains `st.secrets` and passes it to `resolve_secrets`, while CLI and tests continue to use `.env` and explicit environment patches.

- [ ] **Step 3: Run the focused tests and verify they pass**

Run:

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_configuration -v
```

Expected: all configuration tests pass with no secret value in the output.

- [ ] **Step 4: Commit**

```bash
git add starter_v0/configuration.py starter_v0/chat.py starter_v0/tests/test_configuration.py
git commit -m "fix: resolve exact Streamlit secret names"
```

### Task 3: Add setup-copy and status helpers

**Files:**
- Modify: `starter_v0/app.py`
- Modify: `starter_v0/guardrails.py`
- Modify: `starter_v0/tests/test_guardrails.py`
- Modify: `starter_v0/tests/test_app.py`

**Interfaces:**
- `app.secret_status(provider_name: str) -> dict[str, bool]` returns booleans only.
- `app.setup_template(provider_name: str) -> str` returns names-only TOML.
- `guardrails.fallback_hint(...)` names local `.env` and root-level Streamlit Secrets without exposing values.

- [ ] **Step 1: Write failing helper tests**

```python
def test_setup_template_contains_names_only(self) -> None:
    template = app.setup_template("openrouter")
    self.assertIn('OPENROUTER_API_KEY = "PASTE_VALUE_HERE"', template)
    self.assertIn('TAVILY_API_KEY = "PASTE_VALUE_HERE"', template)
    self.assertNotIn("sk-", template)


def test_setup_status_excludes_values(self) -> None:
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "secret-value"}, clear=True):
        status = app.secret_status("openrouter")
    self.assertEqual(status["OPENROUTER_API_KEY"], True)
    self.assertNotIn("secret-value", repr(status))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_app tests.test_guardrails -v
```

Expected: missing helper or assertion failures.

- [ ] **Step 3: Implement helpers and safe setup copy**

Use exact uppercase names and return a template with placeholder values only.

Update fallback copy to say:

`Local: tạo starter_v0/.env từ .env.example. Streamlit Cloud: đặt OPENROUTER_API_KEY ở cấp root trong App settings > Secrets, rồi reboot app.`

- [ ] **Step 4: Run focused tests**

```bash
cd starter_v0
.venv/bin/python -m unittest tests.test_app tests.test_guardrails -v
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

```bash
git add starter_v0/app.py starter_v0/guardrails.py starter_v0/tests/test_app.py starter_v0/tests/test_guardrails.py
git commit -m "feat: add safe Streamlit setup guidance"
```

### Task 4: Replace the conflicting Streamlit theme

**Files:**
- Modify: `starter_v0/app.py:52-210`

**Interfaces:**
- Keep `apply_theme() -> None`.
- Keep all existing render function signatures unchanged.

- [ ] **Step 1: Add CSS contract checks**

Extract the CSS string into a module constant named `THEME_CSS`.

Add a test that asserts `THEME_CSS` contains `--agent-bg:`, `--agent-ink:`, and `color: var(--agent-ink)` and does not contain `radial-gradient`.

- [ ] **Step 2: Implement the minimal CSS refactor**

Use explicit foreground and background declarations for the app, sidebar, native buttons, selectboxes, text inputs, expanders, chat messages, and chat input.

Use a warm off-white page background, dark ink text, teal accent, a 960px content width, and restrained 8px to 12px radii.

Do not style native controls with dark backgrounds unless their text color is explicitly light.

Keep Streamlit accessibility affordances such as focus rings and hover states.

- [ ] **Step 3: Run compile and focused UI helper tests**

```bash
cd starter_v0
.venv/bin/python -m py_compile app.py configuration.py guardrails.py
.venv/bin/python -m unittest tests.test_app -v
```

Expected: exit 0 and all focused tests pass.

- [ ] **Step 4: Commit**

```bash
git add starter_v0/app.py
git commit -m "style: refine Streamlit research cockpit theme"
```

### Task 5: Add the configuration alert and rebalance layout

**Files:**
- Modify: `starter_v0/app.py` in `render_sidebar`, `render_quick_prompts`, and `main`.

**Interfaces:**
- Existing conversation creation, turn rendering, artifact expander, and transcript download behavior remain unchanged.

- [ ] **Step 1: Add pure layout assertions**

Test that the setup template is shown only for missing credentials and that the quick-prompt labels remain stable.

- [ ] **Step 2: Implement the UI hierarchy**

Render a compact `Configuration` alert when the selected model provider is missing.

Show the exact names-only TOML in a code block, a reboot instruction, and separate model and research-tool status rows.

Keep fallback chat enabled and label it as fallback mode.

Replace the three equal-width starter buttons with concise task rows that preserve the same prompt strings.

Move artifact hashes into a collapsed technical-details expander with monospace labels.

- [ ] **Step 3: Run the full unit suite**

```bash
cd starter_v0
.venv/bin/python -m unittest discover -s tests -v
```

Expected: zero failures and zero errors.

- [ ] **Step 4: Commit**

```bash
git add starter_v0/app.py starter_v0/tests/test_app.py
git commit -m "feat: clarify Streamlit configuration state"
```

### Task 6: Verify local E2E and final hygiene

**Files:**
- Modify: `starter_v0/artifacts/REPORT.md` only if verification facts change.

- [ ] **Step 1: Run static and repository checks**

```bash
git diff --check
cd starter_v0
.venv/bin/python -m py_compile app.py configuration.py guardrails.py
```

Scan tracked files for key-shaped values without printing matches:

```bash
if git grep -nE 'sk-or-v1-|tvly-|fc-[0-9a-f]{20,}' -- ':!starter_v0/.env.example'; then
  exit 1
fi
```

Expected: compile succeeds and the tracked-secret scan returns no matches.

- [ ] **Step 2: Run configured local Streamlit E2E**

Start the app with the ignored local `.env`, open the page, and verify:

- provider and Tavily status are `Configured` without showing values;
- the page has readable light controls;
- the setup alert is absent when required keys exist;
- a starter prompt creates a conversation and preserves the existing artifact version.

- [ ] **Step 3: Run missing-key local Streamlit E2E**

Start with `DAY04_ENV_FILE` pointing to a nonexistent file and unset provider/tool variables.

Verify:

- the setup alert shows exact uppercase names;
- the names-only TOML contains placeholders rather than values;
- chat remains available and fallback output is labelled;
- no secret value appears in the DOM, logs, or transcript.

- [ ] **Step 4: Re-read the spec and report every requirement**

Confirm the UI, resolver, security boundary, RapidAPI exclusion, tests, and public-deployment limitation are all represented in the implementation.

- [ ] **Step 5: Commit the verified implementation**

```bash
git status --short
git add starter_v0
git commit -m "feat: ship Streamlit research cockpit"
```

Do not push or open a PR in this task until the user explicitly requests the integration handoff.
