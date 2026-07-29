---
name: social_search
track: core
kind: live_api
provider: Tavily domain-scoped search fallback
requires_env: [TAVILY_API_KEY]
inputs: [query, search_type, limit]
outputs: [items]
side_effect: false
---
# social_search

Finds indexed X posts by keyword.

`search_type=Top` requests popular posts and uses Tavily relevance ranking.

`search_type=Latest` requests recent posts, but cannot guarantee X's native chronological ordering.
