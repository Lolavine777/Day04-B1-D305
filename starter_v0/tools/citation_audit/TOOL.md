---
name: citation_audit
track: bonus
kind: local_formatter
requires_env: []
inputs: [claims]
outputs: [audited_claims, total_claims, valid_claims, invalid_claims, coverage_percent]
side_effect: false
---
# citation_audit

Checks whether each claim has non-empty text, a valid HTTP(S) URL, and a named
source. It returns per-claim issue codes and an overall citation coverage
percentage.

This is a local validation tool. It does not open URLs, judge source quality, or
prove that a citation supports the claim. Use it after claims and citations
have been assembled.
