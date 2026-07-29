# Streamlit Research Cockpit And Secrets Design

## Goal

Redesign the current Streamlit interface into a calm, readable research cockpit and make provider configuration explicit without exposing credentials.

The result must preserve the existing agent loop, tool traces, artifact versioning, transcript persistence, and fallback behavior.

## Current Problems

The current page mixes a light application background with Streamlit controls that can inherit a dark theme.

This creates low-contrast combinations such as dark buttons with dark text.

The page also gives similar visual weight to the title, status chips, artifact metadata, starter prompts, and chat, so the primary research action is not clear.

Missing credentials are represented only by status chips.

The user is told that Streamlit Secrets exist, but the UI does not provide the exact required TOML or distinguish model, search, and page-fetching capabilities.

## Design Direction

The interface will use a light editorial research-cockpit direction.

The visual language will use warm off-white surfaces, dark ink text, a restrained teal accent, and monospace styling only for technical metadata.

The design will avoid decorative gradients, excessive rounded pills, and a card around every section.

The Streamlit theme and custom CSS will be aligned so native controls maintain readable foreground and background colors in every supported state.

The main content will remain centered and readable on a laptop while adapting to narrow mobile screens.

## Information Architecture

The sidebar will contain two compact sections.

`Run configuration` will contain provider, optional model, and version controls.

`System status` will show the selected model provider and the research services required by the declared tools.

The main page will contain:

1. A compact product header and short capability description.
2. A configuration alert only when one or more relevant secrets are missing.
3. A concise status line for provider, model, tool count, and turn count.
4. The conversation or a focused empty state with starter research tasks.
5. A collapsed technical-details section for artifact hashes and transcript metadata.
6. The persistent chat input.

Tool traces will remain collapsed by default.

Answer text will receive more visual weight than raw tool arguments and JSON results.

## Credential Contract

The application will never render, log, persist, or include a credential value in a transcript.

Local development may load credentials from `starter_v0/.env`.

Streamlit Community Cloud will load credentials from root-level Secrets with case-sensitive environment-variable names.

The supported root-level TOML names are:

```toml
OPENROUTER_API_KEY = "..."
TAVILY_API_KEY = "..."
FIRECRAWL_API_KEY = "..."
```

`OPENROUTER_API_KEY` enables the recommended model provider.

`TAVILY_API_KEY` enables web, news, timeline, and social discovery.

`FIRECRAWL_API_KEY` enables direct page fetching and is not required for the initial chat request.

`RAPIDAPI_KEY` and `RAPIDAPI_TWITTER_HOST` are not part of the supported architecture and will not appear in the setup UI.

Alternative model-provider names remain supported when the corresponding provider is selected:

```toml
OPENAI_API_KEY = "..."
ANTHROPIC_API_KEY = "..."
GEMINI_API_KEY = "..."
```

Lowercase aliases such as `openrouter_api_key` will not be accepted because they hide configuration mistakes and do not match the provider contract.

## Secret Resolution

The app will expose one small, testable configuration resolver.

The resolver will preserve an already configured process environment value.

When running under Streamlit, it will safely inspect root-level `st.secrets` for the exact uppercase name and hydrate the corresponding environment variable only when needed.

The resolver will tolerate the absence of a local Streamlit secrets file.

Only boolean configured or missing state will be returned to UI code.

## Missing-Key Experience

When the selected model provider is missing its key, the main page will show an actionable setup panel before the empty state.

The panel will show the exact required variable name and the path `Manage app > Settings > Secrets`.

It will include a copyable names-only TOML template and tell the operator to reboot the app after saving.

Research-service status will separately explain that Tavily and Firecrawl affect tool coverage rather than provider initialization.

The chat input will remain available so the existing fallback mode can demonstrate safe degradation.

Every fallback response will remain visibly labelled as fallback output.

## Security Boundaries

No password input will be added to the application.

No credential will be stored in `st.session_state`.

No credential value will be passed to HTML, Markdown, exceptions, logs, or download artifacts.

Error sanitization will continue masking environment-backed secret values.

The committed `.env.example` will contain names only.

The ignored local `.env` will never be staged.

Any credential pasted into chat or another recorded channel must be rotated before deployment.

## Testing

Implementation will begin with failing tests for:

- Resolving an exact uppercase root-level Streamlit secret.
- Preserving an existing environment value.
- Treating a lowercase-only secret as missing.
- Tolerating an absent Streamlit secrets file.
- Returning status data without exposing a credential value.
- Rendering names-only configuration guidance for a missing provider key.

The existing unit suite must remain green.

Local E2E verification will cover a configured environment and an environment with no keys.

Visual checks will cover the default desktop viewport and one narrow viewport.

The final verification will also include `git diff --check`, Python compilation, and a tracked-secret scan.

## Non-Goals

This redesign will not change the model-tool loop, prompt, tool declarations, evaluation data, or artifact hashes.

It will not add a frontend framework or a new UI dependency.

It will not restore RapidAPI.

It will not automatically modify Streamlit Cloud settings or commit live credentials.
