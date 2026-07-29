# Final Lab Wrap-Up Design

## Goal

Bring `develop/long` to a locally verified, review-ready state against the fixed Day 04 lab rubric without creating another branch, pushing commits, or opening a pull request.

## Scope

The wrap-up covers the current committed `origin/main` product plus the uncommitted evidence already present on `develop/long`.

The final state must include:

- A current-artifact base v3 run.
- A current-artifact group v3 run.
- Version log entries that point to real committed run files.
- Three current-artifact live transcripts covering research, clarification, and confirmation.
- A completed `REPORT.md` based only on real evidence.
- A Streamlit UI that does not crash while rendering fallback diagnostics.
- Cloud-appropriate secret guidance.
- Reproducible dependency installation for every discovered Python test.
- Passing static validation, tests, compile checks, and local Streamlit E2E checks.

## Working Strategy

All work happens directly on `develop/long`.

Before updating the branch, the existing staged, unstaged, and untracked WIP is preserved in two ways:

1. A named Git stash including untracked files.
2. A patch and file inventory stored under `/tmp`.

The branch commits are then rebased onto the latest `origin/main`, and the WIP is restored.

Conflicts are resolved by preserving the latest committed product code and retaining only evidence that matches the final prompt and tool hashes.

No push or pull request is created during this wrap-up.

## Final Artifact Contract

The current prompt and tool declarations on the updated branch are frozen before the final evals begin.

The release label remains `v3` because the fixed rubric requires v0, v1, v2, and final v3 evidence.

The final base run, group run, version log, transcripts, and report must all reference the same prompt and tool hashes.

If any prompt or tool declaration changes after a final run, both final eval suites must be rerun.

## Streamlit Stabilization

The public failure has two distinct layers:

1. The provider falls back when its credential or upstream request fails.
2. The fallback renderer can crash when Streamlit hot reloads `app.py` while retaining an older imported `guardrails` module.

The UI must render a safe generic hint even when `guardrails.fallback_hint` is unavailable.

The normal path continues to use `guardrails.fallback_hint` when present.

Fallback copy must describe both local `.env` configuration and Streamlit Community Cloud root-level Secrets.

Secret names remain case-sensitive and must match the environment variables used by providers and tools.

The minimal deployed secret is `OPENROUTER_API_KEY`.

Research tools additionally use `TAVILY_API_KEY` and `FIRECRAWL_API_KEY`.

Telegram secrets remain optional.

## Dependency Contract

The documented `starter_v0` setup must be sufficient to run all tests discovered under `starter_v0/tests`.

Dependencies required only by the root Next.js and FastAPI deployment may remain in the root requirements, but any dependency imported by a test under `starter_v0/tests` must also be available through the documented test installation path.

The wrap-up must avoid duplicate or conflicting version pins.

## Evidence Generation

Provider preflight runs before live evidence generation.

The base suite runs exactly 20 fixed cases.

The group suite runs exactly 10 cases with the committed five single-turn and five multi-turn split.

Both final suites must satisfy:

- `provider_error_cases == 0`.
- `measured_cases == total_cases`.
- Every tool result containing an error receives manual review.
- The artifact hash matches the frozen current prompt and tools.

Three live conversations produce transcript evidence:

1. A research request that uses a research tool and returns a final response.
2. A request missing required information that routes to `clarify(response_type="text")`.
3. A sensitive delivery request that routes to `clarify(response_type="yes_no")` before any `send` call.

No live Telegram send is performed.

## Report Completion

`REPORT.md` is updated from the final committed artifacts rather than copied from the stale `develop/nghia` branch.

The report includes:

- Team, provider, and model.
- The current public Streamlit URL.
- All 14 tools and the four team-authored tools.
- The v0 through v3 metric history.
- Concrete failure analysis from run JSON.
- All 10 group cases and their final outcomes.
- The three live transcript paths and observed tool calls.
- Mandatory tool evidence and bonus eligibility.
- Known limitations of Tavily-based social search.
- A reflection grounded in observed failures.

Public deployment status is recorded truthfully.

Local E2E evidence may be completed before a pull request.

The public URL cannot be marked verified for the new local commits until those commits are deployed and tested from the public site.

## Verification

The final local gate consists of:

1. Provider preflight.
2. Static submission validator.
3. Full Python unit-test discovery.
4. Direct tests for every team-authored tool.
5. `py_compile` for the Streamlit entrypoint and provider/tool modules.
6. `git diff --check`.
7. Secret and tracked-path scan.
8. Local Streamlit startup and browser E2E.
9. Manual inspection of final base and group run summaries.
10. Cross-check that run, version log, transcript, report, prompt, and tool hashes agree.

The wrap-up is review-ready only when all locally controllable checks pass.

The final handoff must explicitly identify public redeployment verification as an external post-merge gate if the new commits have not yet been deployed.

## Commit Strategy

Commits are local and scoped:

1. Design and implementation plan.
2. Streamlit fallback and dependency stabilization.
3. Final v3 base and group evidence.
4. Current live transcript evidence.
5. Final report and analysis updates.

Existing unrelated WIP is never included accidentally.

No commit includes secrets, `.env`, `.venv`, caches, or generated deployment credentials.
