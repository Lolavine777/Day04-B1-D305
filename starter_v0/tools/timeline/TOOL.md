---
name: timeline
track: core
kind: live_api
provider: Tavily domain-scoped search fallback
requires_env: [TAVILY_API_KEY]
inputs: [screenname, limit]
outputs: [items]
side_effect: false
---
# timeline

Finds indexed recent X posts from a single account.

`screenname` is an account handle without `@`.

Results are limited to `x.com` and `twitter.com`, but may not be a complete or strictly chronological timeline.
