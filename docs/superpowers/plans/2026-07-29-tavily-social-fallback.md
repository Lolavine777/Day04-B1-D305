# Tavily Social Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace RapidAPI with Tavily for the existing social tools without changing their public contracts.

**Architecture:** Each social tool makes a Tavily `/search` request with a domain filter for X/Twitter and then maps the results into the current research-item shape.

The registry, tool names, declaration schemas, and fixed evaluations remain unchanged.

**Tech Stack:** Python 3.12, `requests`, `unittest`, Tavily Search API.

## Global Constraints

- Retain `timeline(screenname, limit)` and `social_search(query, search_type, limit)`.
- Do not change `starter_v0/data/eval_base.json` or `starter_v0/data/eval_group.json`.
- Do not reveal or commit credentials.
- Use `starter_v0/.venv/bin/python` for every Python command.
- Do not add a dependency.

---

### Task 1: Cover social fallback behavior

**Files:**

- Create: `starter_v0/tests/test_social_fallback.py`
- Modify: `starter_v0/tools/timeline/tool.py`
- Modify: `starter_v0/tools/social_search/tool.py`

**Interfaces:**

- Consumes: `TAVILY_API_KEY` and Tavily's `/search` JSON `results` array.
- Produces: `get_user_tweets(screenname: str = "", limit: int = 5) -> dict[str, Any]` and `search_tweets(query: str = "", search_type: str = "Latest", limit: int = 5) -> dict[str, Any]`.

- [ ] **Step 1: Write failing unit tests**

```python
@patch("tools.timeline.tool.requests.post")
def test_timeline_uses_tavily_x_domain_and_normalizes_results(mock_post):
    mock_post.return_value.json.return_value = {"results": [{"title": "Post", "url": "https://x.com/sama/status/1", "content": "Body", "score": 0.9}]}
    mock_post.return_value.raise_for_status.return_value = None
    with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
        result = get_user_tweets("sama", limit=3)
    assert result["items"][0]["url"] == "https://x.com/sama/status/1"
    assert mock_post.call_args.kwargs["json"]["include_domains"] == ["x.com", "twitter.com"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd starter_v0 && .venv/bin/python -m unittest tests.test_social_fallback -v`

Expected: FAIL because the existing implementation sends RapidAPI GET requests.

- [ ] **Step 3: Implement the minimal Tavily calls**

```python
body = {"query": query, "topic": "general", "max_results": limit, "search_depth": "basic", "include_domains": ["x.com", "twitter.com"]}
response = requests.post("https://api.tavily.com/search", json=body, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT)
```

Normalize `results` using the existing item keys and keep standard `err()` handling.

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `cd starter_v0 && .venv/bin/python -m unittest tests.test_social_fallback -v`

Expected: PASS with tests for timeline, social search, and Tavily failure behavior.

- [ ] **Step 5: Commit**

```bash
git add starter_v0/tests/test_social_fallback.py starter_v0/tools/timeline/tool.py starter_v0/tools/social_search/tool.py
git commit -m "feat: use Tavily for social research tools"
```

### Task 2: Update tool documentation and verify live behavior

**Files:**

- Modify: `starter_v0/tools/timeline/TOOL.md`
- Modify: `starter_v0/tools/social_search/TOOL.md`
- Modify: `TOOL-SETUP.md`

**Interfaces:**

- Consumes: the `TAVILY_API_KEY` documented by the repository.
- Produces: accurate operator documentation for both social tools.

- [ ] **Step 1: Update provider and environment requirements**

Document Tavily as the provider and `TAVILY_API_KEY` as the only required variable for both social tools.

Document the fallback's domain-scoped search behavior and its recency/ranking limitation.

- [ ] **Step 2: Run live smoke tests**

Run: `cd starter_v0 && .venv/bin/python -c "from pathlib import Path; from env_loader import load_lab_env; load_lab_env(Path.cwd()); from tools import TOOL_FUNCTIONS as T; print(T['timeline']('sama', limit=1)); print(T['social_search']('OpenAI', limit=1))"`

Expected: Both responses have `error` equal to `None` and contain a list under `items`.

- [ ] **Step 3: Run verification checks**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and only the intended implementation, tests, documentation, and planning files changed.

- [ ] **Step 4: Commit**

```bash
git add starter_v0/tools/timeline/TOOL.md starter_v0/tools/social_search/TOOL.md TOOL-SETUP.md
git commit -m "docs: document Tavily social fallback"
```
