# Streamlit Native Theme And Tool Error Design

## Goal

Remove the mixed light and dark Streamlit surfaces shown in the deployed app and replace raw upstream HTTP errors with concise, actionable tool diagnostics.

The change must preserve the existing agent loop, artifact hashes, tool declarations, transcript schema, fallback mode, and public deployment workflow.

## Observed Evidence

The deployed app is running the code merged through PR #21.

The page background and custom status elements use the intended light palette, but the provider selector, code blocks, and fixed chat footer inherit Streamlit's dark native theme.

The current CSS targets a BaseWeb selector that is no longer present in the provider selector rendered by Streamlit 1.60.

The deployed provider selector is implemented with React Aria and therefore ignores that selector.

The fixed chat input itself is light, but its Streamlit-owned parent container remains dark.

The screenshot also shows a Tavily `401 Unauthorized` response from `lookup`.

The code uses the documented Tavily endpoint and Bearer header.

The same `lookup(query="Myanmar", topic="news", timeframe="day")` request succeeds with the local credential, so the deployed 401 is a rejected or stale Streamlit Cloud secret rather than an incorrect URL.

## Selected Approach

Use Streamlit's supported theme configuration for native widgets and keep custom CSS only for product-specific layout and semantic elements.

Normalize upstream HTTP failures before they enter the model loop, transcript, and UI.

Render tool traces as compact summaries, with raw arguments and results hidden behind an explicit developer-details control.

Replacing Streamlit with another frontend is outside scope because it would add deployment and integration risk without improving the lab deliverables.

## Theme Contract

The project will define the same light theme in:

- `.streamlit/config.toml` for Streamlit Community Cloud and root-level launch commands.
- `starter_v0/.streamlit/config.toml` for the documented `cd starter_v0 && streamlit run app.py` workflow.

Both files will be covered by a test that parses them with `tomllib` and asserts equality.

The theme will use:

- A cool near-white application background.
- A slightly darker cool-gray sidebar.
- White or light-gray interactive surfaces.
- Dark ink text.
- One emerald accent.
- An 8px radius system.
- Visible widget borders and focus states.
- Light code backgrounds rather than dark code islands.

The custom CSS will stop styling Streamlit's internal BaseWeb or React Aria implementation classes.

It will retain only stable `data-testid` selectors when necessary and custom `.agent-*` classes owned by this repository.

## Information Architecture

The main heading, chat history, and chat input remain in their current order.

The sidebar will show:

1. Provider selection.
2. A compact service-status summary.
3. A collapsed `Advanced` section containing optional model and artifact version controls.
4. Transcript download controls only after a conversation starts.

The repeated uppercase `Configuration` and `System status` eyebrows will be removed.

Provider, Tavily, and Firecrawl state will remain visible because those dots represent real service configuration.

Artifact hashes remain under `Technical details`.

## Trace Design

The outer trace remains collapsed by default.

When opened, each tool event will show one concise line containing:

- Tool name.
- Success or failure state.
- Result count when available.
- Provider name when available.

Tool arguments and raw results will not render by default.

A `Show developer details` toggle inside the trace will reveal the existing JSON payloads.

Authentication errors will use an inline warning rather than a large raw red error block.

The visible assistant answer keeps priority over trace data.

## HTTP Error Contract

HTTP failures from Tavily and Firecrawl will be normalized at the tool boundary.

The normalized dictionary will preserve `error: "HTTPError"` for compatibility and add:

- `code`: a stable machine-readable classification.
- `status_code`: the upstream numeric HTTP status when available.
- `message`: a safe actionable sentence without a URL or credential value.

The classifications are:

- `authentication_failed` for 401 and 403.
- `rate_limited` for 429.
- `upstream_http_error` for other HTTP status codes.

For a Tavily authentication failure, the safe message will tell the operator to replace `TAVILY_API_KEY` in Streamlit Secrets and reboot the app.

For a Firecrawl authentication failure, the safe message will name `FIRECRAWL_API_KEY`.

No upstream URL, response body, authorization header, or credential value will enter the normalized result.

Generic non-HTTP exceptions will continue through the existing sanitizer.

## Data Flow

The tool calls the upstream API.

If the response succeeds, the existing result transformation remains unchanged.

If `raise_for_status()` raises `requests.HTTPError`, the tool converts it to the normalized error dictionary before returning.

The model receives the safe classification and actionable message in `TOOL_RESULTS_JSON`.

The transcript stores the same safe payload.

The UI renders the classification as a concise summary and reveals the safe raw dictionary only when developer details are enabled.

## External Configuration Gate

Code cannot make a rejected Tavily key valid.

The operator must rotate the compromised key, store the replacement as root-level `TAVILY_API_KEY` in Streamlit Secrets, save the settings, and reboot the app.

The UI may report that a key is configured when the variable exists.

It will not perform a paid Tavily health check on every Streamlit rerun.

The first real tool request remains the authoritative validity check.

## Testing

Implementation will start with failing tests for:

- Matching root and `starter_v0` theme files.
- A light theme base and light code background.
- Tavily 401 normalization.
- Tavily 429 normalization.
- Firecrawl 401 normalization.
- Absence of upstream URLs and credential values from normalized errors.
- Compact tool-event summary text.
- Developer details being disabled by default.

The complete unit suite, compile checks, submission validator, diff check, and tracked-secret scan must pass.

Local browser E2E will verify:

- The provider selector uses a light surface.
- The fixed chat footer uses a light surface.
- The trace starts collapsed.
- A mocked authentication failure produces the actionable Tavily message without a URL.
- No horizontal overflow appears at the default viewport.

Public verification occurs only after merge, replacement of the Streamlit secret, and app reboot.

## Non-Goals

This change will not modify the system prompt or tool declarations.

It will not add a live health-check request on every render.

It will not add a new frontend framework.

It will not reintroduce RapidAPI.

It will not expose or commit any API key.
