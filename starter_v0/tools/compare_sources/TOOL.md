---
name: compare_sources
track: bonus
kind: local_formatter
requires_env: []
inputs: [items]
outputs: [comparisons, conflicts, source_count, compared_claim_count, conflict_count, agreement_count, skipped_item_count]
side_effect: false
---
# compare_sources

Compares structured claims from research items and reports agreements and
conflicts without calling an external API.

Each item should contain `source`, optional `url`, and a `claims` object whose
keys are claim names and whose values are the source's reported values. Claim
names and text values are compared case-insensitively after whitespace
normalization. Use this only after research items have been collected and their
claims have been structured; it is not a search or fact-verification tool.
