---
name: export_report
track: bonus
kind: local_formatter
requires_env: []
inputs: [title, items, format]
outputs: [format, content_type, content, item_count]
side_effect: false
---
# export_report

Renders already-collected research items as a complete Markdown or JSON report.
Markdown output preserves section and item order and includes source links.
JSON output is a deterministic, parseable report object.

The tool returns content to the caller and never writes files. Use it only at
the final presentation/export stage; it does not search, verify citations, or
send the report externally.
