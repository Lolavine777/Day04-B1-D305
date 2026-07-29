---
name: timeline
track: core
kind: live_api
provider: Tavily
requires_env: [TAVILY_API_KEY]
inputs: [screenname, limit]
outputs: [items]
side_effect: false
---
# timeline

Finds recent, publicly indexed X posts from a single account. `screenname` is
an account handle without `@`. Results come from Tavily's public web index, so
coverage may differ from the account's authoritative X timeline.
