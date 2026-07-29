---
name: social_search
track: core
kind: live_api
provider: Tavily
requires_env: [TAVILY_API_KEY]
inputs: [query, search_type, limit]
outputs: [items]
side_effect: false
---
# social_search

Finds publicly indexed X posts by keyword through Tavily. `Latest` uses a
shorter search window while `Top` uses Tavily relevance over a broader window.
