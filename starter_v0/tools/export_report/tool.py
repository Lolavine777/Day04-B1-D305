from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from tools._shared import domain


def _source_reference(item: dict[str, Any]) -> str:
    url = str(item.get("url") or "").strip()
    source = str(item.get("source") or "").strip() or domain(url)
    if url:
        return f"[{source or url}]({url})"
    return source


def _markdown_report(title: str, items: list[dict[str, Any]]) -> str:
    parts = [f"# {title}"]
    if not items:
        return "\n\n".join([*parts, "_No items._"])

    sections: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(items):
        section = str(item.get("section") or "Research").strip() or "Research"
        sections.setdefault(section, []).append((index, item))

    for section, section_items in sections.items():
        parts.append(f"## {section}")
        for index, item in section_items:
            item_title = (
                str(item.get("title") or "").strip() or f"Item {index + 1}"
            )
            summary = str(item.get("summary") or "").strip()
            source = _source_reference(item)
            block = [f"### {item_title}"]
            if summary:
                block.append(summary)
            if source:
                block.append(f"Source: {source}")
            parts.append("\n\n".join(block))

    return "\n\n".join(parts)


def export_report(
    title: str = "",
    items: list[dict[str, Any]] | None = None,
    format: str = "markdown",
) -> dict[str, Any]:
    report_title = title.strip() or "Research Report"
    report_items = items or []
    if format == "json":
        payload = {
            "title": report_title,
            "item_count": len(report_items),
            "items": deepcopy(report_items),
        }
        return {
            "tool": "export_report",
            "format": "json",
            "content_type": "application/json",
            "content": json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            "item_count": len(report_items),
        }
    if format != "markdown":
        return {
            "tool": "export_report",
            "status": "error",
            "error": "unsupported_format",
            "supported_formats": ["markdown", "json"],
        }
    return {
        "tool": "export_report",
        "format": "markdown",
        "content_type": "text/markdown",
        "content": _markdown_report(report_title, report_items),
        "item_count": len(report_items),
    }
