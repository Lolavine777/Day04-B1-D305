# Streamlit Native Theme And Tool Errors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Streamlit app consistently light and make Tavily and Firecrawl failures safe, actionable, and visible without overwhelming the answer.

**Architecture:** Streamlit's native theme configuration owns widget colors, while repository-owned CSS handles only product layout and semantic elements.
The shared tool error helper converts upstream HTTP failures before they reach the model loop, transcript, or UI.
The trace renders a compact pure-text summary and reveals safe JSON only through an explicit developer-details toggle.

**Tech Stack:** Python 3.11+, Streamlit 1.60, Requests, standard-library `unittest`, and standard-library `tomllib`.

## Global Constraints

The system prompt, tool declarations, artifact hashes, transcript schema, fallback mode, and public deployment workflow must remain unchanged.

The implementation must not add a paid service-health request during Streamlit reruns.

The implementation must not add a frontend framework or dependency.

The implementation must not reintroduce RapidAPI.

No upstream URL, response body, authorization header, or credential value may enter a normalized HTTP error.

The two Streamlit theme files must remain identical.

---

### Task 1: Normalize Tavily And Firecrawl HTTP Failures

**Files:**

- Create: `starter_v0/tests/test_tool_http_errors.py`
- Modify: `starter_v0/tools/_shared.py`
- Modify: `starter_v0/tools/lookup/tool.py`
- Modify: `starter_v0/tools/fetch/tool.py`
- Modify: `starter_v0/tools/social_search/tool.py`
- Modify: `starter_v0/tools/timeline/tool.py`
- Modify: `starter_v0/tests/test_social_fallback.py`

**Interfaces:**

- Consumes: `requests.HTTPError.response.status_code`.
- Produces: `err(tool, exc, *, service=None, secret_name=None) -> dict[str, Any]`.
- Produces: normalized HTTP dictionaries with `tool`, `error`, `code`, `status_code`, and `message`.

- [ ] **Step 1: Write failing HTTP-boundary tests**

Create `starter_v0/tests/test_tool_http_errors.py` with this content:

```python
from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

import requests

from tools.fetch.tool import read_url
from tools.lookup.tool import web_search


def rejected_response(status_code: int, secret: str) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} failure for https://upstream.example/search?key={secret}",
        response=response,
    )
    return response


class ToolHttpErrorTests(unittest.TestCase):
    def test_tavily_401_is_actionable_and_safe(self) -> None:
        secret = "tavily-secret-value"
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(401, secret)),
        ):
            result = web_search("Myanmar", topic="news", timeframe="day")

        self.assertEqual(result["error"], "HTTPError")
        self.assertEqual(result["code"], "authentication_failed")
        self.assertEqual(result["status_code"], 401)
        self.assertIn("TAVILY_API_KEY", result["message"])
        self.assertIn("reboot", result["message"].lower())
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))

    def test_tavily_429_is_classified_without_leaking_url(self) -> None:
        secret = "tavily-secret-value"
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(429, secret)),
        ):
            result = web_search("AI")

        self.assertEqual(result["code"], "rate_limited")
        self.assertEqual(result["status_code"], 429)
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))

    def test_firecrawl_401_names_its_streamlit_secret(self) -> None:
        secret = "firecrawl-secret-value"
        with (
            patch.dict(os.environ, {"FIRECRAWL_API_KEY": secret}, clear=True),
            patch("requests.post", return_value=rejected_response(401, secret)),
        ):
            result = read_url("https://example.com")

        self.assertEqual(result["code"], "authentication_failed")
        self.assertEqual(result["status_code"], 401)
        self.assertIn("FIRECRAWL_API_KEY", result["message"])
        self.assertNotIn("https://", repr(result))
        self.assertNotIn(secret, repr(result))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest tests.test_tool_http_errors -v
```

Expected result: three failures because `code` and `status_code` are absent and raw HTTP messages contain the upstream URL.

- [ ] **Step 3: Add the minimal shared normalization**

Update `starter_v0/tools/_shared.py` so `err` imports Requests and contains:

```python
import requests


def err(
    tool: str,
    exc: Exception,
    *,
    service: str | None = None,
    secret_name: str | None = None,
) -> dict[str, Any]:
    if not isinstance(exc, requests.HTTPError):
        return {
            "tool": tool,
            "error": type(exc).__name__,
            "message": str(exc),
        }

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    service_name = service or "Upstream service"
    if status_code in {401, 403}:
        code = "authentication_failed"
        if secret_name:
            message = (
                f"{service_name} authentication failed. Replace "
                f"{secret_name} in Streamlit Secrets, save, and reboot the app."
            )
        else:
            message = f"{service_name} authentication failed."
    elif status_code == 429:
        code = "rate_limited"
        message = f"{service_name} rate limit reached. Wait before retrying."
    else:
        code = "upstream_http_error"
        status = f" with HTTP status {status_code}" if status_code else ""
        message = f"{service_name} request failed{status}."

    return {
        "tool": tool,
        "error": "HTTPError",
        "code": code,
        "status_code": status_code,
        "message": message,
    }
```

Pass `service="Tavily", secret_name="TAVILY_API_KEY"` from `web_search`.

Pass `service="Firecrawl", secret_name="FIRECRAWL_API_KEY"` from `read_url`.

Preserve `code` and `status_code` in the error dictionaries returned by `search_tweets` and `get_user_tweets`.

Update the existing social fallback HTTP test to expect `upstream_http_error` and a safe Tavily request failure message instead of the raw exception text.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest \
  tests.test_tool_http_errors \
  tests.test_social_fallback \
  tests.test_tavily_social_tools -v
```

Expected result: all focused tests pass and no test output contains a credential value.

### Task 2: Move Widget Colors To Native Streamlit Theme

**Files:**

- Create: `.streamlit/config.toml`
- Create: `starter_v0/.streamlit/config.toml`
- Create: `starter_v0/tests/test_theme_config.py`
- Modify: `starter_v0/app.py`
- Modify: `starter_v0/tests/test_app.py`

**Interfaces:**

- Consumes: Streamlit native `[theme]` configuration.
- Produces: two equal TOML theme dictionaries with a light base.
- Produces: custom CSS without BaseWeb or React Aria implementation selectors.

- [ ] **Step 1: Write failing theme-contract tests**

Create `starter_v0/tests/test_theme_config.py` with this content:

```python
from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "starter_v0"


class ThemeConfigTests(unittest.TestCase):
    def test_root_and_local_streamlit_themes_match(self) -> None:
        root_theme = tomllib.loads(
            (PROJECT_ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        )
        local_theme = tomllib.loads(
            (APP_ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(root_theme, local_theme)

    def test_theme_uses_light_native_surfaces(self) -> None:
        config = tomllib.loads(
            (APP_ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        )
        theme = config["theme"]

        self.assertEqual(theme["base"], "light")
        self.assertEqual(theme["backgroundColor"], "#F7F9F8")
        self.assertEqual(theme["secondaryBackgroundColor"], "#EEF2F1")
        self.assertEqual(theme["codeBackgroundColor"], "#F1F5F4")
        self.assertEqual(theme["textColor"], "#17211F")
        self.assertTrue(theme["showWidgetBorder"])
```

Add these assertions to the existing CSS test in `starter_v0/tests/test_app.py`:

```python
self.assertNotIn('data-baseweb', css)
self.assertNotIn('react-aria', css.lower())
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest \
  tests.test_theme_config \
  tests.test_app.AppLoopTests.test_theme_uses_readable_research_cockpit_tokens -v
```

Expected result: the theme files are missing and the CSS still contains `data-baseweb`.

- [ ] **Step 3: Add matching native theme files and simplify CSS**

Create both `.streamlit/config.toml` and `starter_v0/.streamlit/config.toml` with identical content:

```toml
[theme]
base = "light"
primaryColor = "#0F766E"
backgroundColor = "#F7F9F8"
secondaryBackgroundColor = "#EEF2F1"
textColor = "#17211F"
codeBackgroundColor = "#F1F5F4"
borderColor = "#CBD5D1"
baseRadius = "8px"
buttonRadius = "8px"
showWidgetBorder = true
```

Remove the `data-baseweb` rules from `THEME_CSS`.

Remove widget background, widget foreground, button, and code rules now owned by the native theme.

Keep the repository-owned `.agent-*` rules and stable `data-testid` layout rules.

Set the remaining custom surface tokens to the same cool light palette used by the native theme.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest \
  tests.test_theme_config \
  tests.test_app.AppLoopTests.test_theme_uses_readable_research_cockpit_tokens -v
```

Expected result: all theme-contract tests pass.

### Task 3: Compact The Sidebar And Tool Trace

**Files:**

- Modify: `starter_v0/app.py`
- Modify: `starter_v0/tests/test_app.py`

**Interfaces:**

- Produces: `tool_event_summary(event: dict[str, Any]) -> str`.
- Produces: `SHOW_DEVELOPER_DETAILS_DEFAULT = False`.
- Consumes: the existing tool-event dictionary and Streamlit rendering functions.

- [ ] **Step 1: Write failing summary and default-state tests**

Add these tests to `starter_v0/tests/test_app.py`:

```python
def test_tool_event_summary_reports_success_count_and_provider(self) -> None:
    summary = app.tool_event_summary(
        {
            "tool": "social_search",
            "result": {
                "provider": "tavily",
                "items": [{"url": "https://x.com/example/status/1"}],
            },
        }
    )

    self.assertEqual(summary, "social_search · success · 1 result · tavily")

def test_tool_event_summary_reports_safe_failure_code(self) -> None:
    summary = app.tool_event_summary(
        {
            "tool": "lookup",
            "result": {
                "error": "HTTPError",
                "code": "authentication_failed",
            },
        }
    )

    self.assertEqual(summary, "lookup · authentication failed")

def test_developer_details_are_hidden_by_default(self) -> None:
    self.assertIs(app.SHOW_DEVELOPER_DETAILS_DEFAULT, False)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest \
  tests.test_app.AppLoopTests.test_tool_event_summary_reports_success_count_and_provider \
  tests.test_app.AppLoopTests.test_tool_event_summary_reports_safe_failure_code \
  tests.test_app.AppLoopTests.test_developer_details_are_hidden_by_default -v
```

Expected result: the helper and constant do not exist.

- [ ] **Step 3: Implement compact trace rendering**

Add `SHOW_DEVELOPER_DETAILS_DEFAULT = False`.

Implement `tool_event_summary` as a pure helper that:

- Uses the tool name from the event.
- Returns the normalized code with underscores replaced by spaces for failures.
- Returns `success`, a singular or plural result count, and the provider for successful dictionary results.

Change `render_tool_event` to accept `show_details: bool`.

Always render the compact summary.

Render an inline `st.warning` with the safe error message for failures.

Render arguments and results only when `show_details` is true.

In `render_trace`, add a toggle with `value=SHOW_DEVELOPER_DETAILS_DEFAULT` and a key derived from the turn's existing `started_at` value.

Keep the outer trace expander collapsed by default.

- [ ] **Step 4: Simplify sidebar information architecture**

Keep provider selection visible.

Move the optional model and version inputs into a collapsed `Advanced` expander.

Place the compact provider, Tavily, and Firecrawl service status immediately after provider selection.

Remove the repeated `Configuration` and `System status` eyebrow labels.

Keep transcript controls after conversation creation.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest tests.test_app -v
```

Expected result: all app tests pass.

### Task 4: Verify The Release And Browser Experience

**Files:**

- Modify only files required to correct failures found by the checks below.

**Interfaces:**

- Consumes: the completed implementation.
- Produces: test, validator, secret-scan, and browser evidence.

- [ ] **Step 1: Run the full automated verification**

Run:

```bash
cd starter_v0
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m compileall -q .
./.venv/bin/python scripts/validate_submission.py
```

Expected result: every test and validator check passes with exit code 0.

- [ ] **Step 2: Run repository hygiene checks**

Run from the repository root:

```bash
git diff --check
git status --short
git grep -nE '(sk-or-v1-|tvly-|fc-[0-9a-f]{16}|[0-9a-f]{32}msh)' -- . \
  ':(exclude)docs/superpowers/specs/*' \
  ':(exclude)docs/superpowers/plans/*'
```

Expected result: `git diff --check` exits 0 and the secret scan prints no matches.

- [ ] **Step 3: Verify the local browser E2E**

Start Streamlit from `starter_v0` with its virtual environment.

Open the local app at a desktop viewport.

Confirm the provider selector, sidebar, code blocks, and chat footer use light surfaces.

Confirm the trace begins collapsed.

Confirm opening the trace shows compact tool summaries and developer details remain hidden.

Confirm a normalized authentication failure shows the actionable secret name without an upstream URL.

Confirm the page has no horizontal overflow.

- [ ] **Step 4: Review the implementation against the approved spec**

Confirm each section in `docs/superpowers/specs/2026-07-29-streamlit-native-theme-tool-errors-design.md` is implemented or explicitly listed as an external deployment gate.

Confirm the system prompt, `artifacts/tools.yaml`, artifact hashes, transcript schema, and dependencies have not changed.

- [ ] **Step 5: Commit and push without opening a pull request**

Run:

```bash
git add \
  .streamlit/config.toml \
  starter_v0/.streamlit/config.toml \
  starter_v0/app.py \
  starter_v0/tools/_shared.py \
  starter_v0/tools/lookup/tool.py \
  starter_v0/tools/fetch/tool.py \
  starter_v0/tools/social_search/tool.py \
  starter_v0/tools/timeline/tool.py \
  starter_v0/tests/test_app.py \
  starter_v0/tests/test_social_fallback.py \
  starter_v0/tests/test_theme_config.py \
  starter_v0/tests/test_tool_http_errors.py \
  docs/superpowers/plans/2026-07-29-streamlit-native-theme-tool-errors.md
git commit -m "fix: stabilize Streamlit tools and theme"
git push origin develop/long
```

Expected result: the commit and push succeed, and no pull request is created.
