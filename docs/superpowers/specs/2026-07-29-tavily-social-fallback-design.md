# Tavily Social Fallback Design

## Goal

Replace the unavailable RapidAPI backend for the existing `timeline` and `social_search` tools with Tavily while preserving the public tool contract required by the lab.

## Scope

Keep the `timeline(screenname, limit)` and `social_search(query, search_type, limit)` names, schemas, registry keys, and evaluation cases unchanged.

Use Tavily's existing API key to search only `x.com` and `twitter.com` results.

Do not modify the fixed base or group evaluation datasets.

## Data Flow

`timeline` issues a Tavily query for posts from the requested handle and requests the caller's limit.

`social_search` issues a Tavily query for X posts matching the supplied topic and requests the caller's limit.

Both implementations normalize Tavily results into the repository's existing item shape with `title`, `summary`, `url`, `source`, and `score`.

`Top` is represented by Tavily's relevance ranking while `Latest` adds a recency-oriented query phrase.

## Error Handling

Missing `TAVILY_API_KEY`, HTTP failures, and malformed responses return the repository's standard error object.

The implementations must not expose credentials in errors or logs.

## Verification

Unit tests mock Tavily's HTTP request and assert the domain restriction, query construction, result normalization, error behavior, and request limits.

Live smoke tests invoke both tools with the configured Tavily key and confirm a non-error response.
