---
name: dedupe
track: core
kind: local_formatter
requires_env: []
inputs: [items]
outputs: [items, original_count, deduplicated_count]
side_effect: false
---
# dedupe

Removes duplicate research items after the items have already been collected.
It preserves the first occurrence and the original order. This is a local
post-processing tool, not an initial search tool, and it does not call an
external API.
