from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal
from typing import Any

from tools._shared import domain


def _normalized_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _normalized_value(value: Any) -> tuple[str, str]:
    if isinstance(value, str):
        return ("string", _normalized_text(value))
    if isinstance(value, bool):
        return ("boolean", str(value).lower())
    if isinstance(value, (int, float)):
        return ("number", str(Decimal(str(value)).normalize()))
    if value is None:
        return ("null", "")
    return (
        type(value).__name__,
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str),
    )


def _source_label(item: dict[str, Any], index: int) -> str:
    return (
        str(item.get("source") or "").strip()
        or domain(str(item.get("url") or ""))
        or str(item.get("title") or "").strip()
        or f"Source {index + 1}"
    )


def compare_sources(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source_items = items or []
    grouped: dict[str, dict[str, Any]] = {}
    skipped_item_count = 0

    for index, item in enumerate(source_items):
        claims = item.get("claims")
        if not isinstance(claims, dict) or not claims:
            skipped_item_count += 1
            continue

        source = _source_label(item, index)
        url = str(item.get("url") or "").strip()
        for claim, value in claims.items():
            claim_text = str(claim).strip()
            if not claim_text:
                continue
            key = _normalized_text(claim_text)
            group = grouped.setdefault(
                key,
                {
                    "claim": claim_text,
                    "observations": [],
                    "_values": set(),
                    "_source_indexes": set(),
                },
            )
            group["observations"].append(
                {
                    "source": source,
                    "url": url,
                    "value": deepcopy(value),
                }
            )
            group["_values"].add(_normalized_value(value))
            group["_source_indexes"].add(index)

    comparisons: list[dict[str, Any]] = []
    for group in grouped.values():
        distinct_value_count = len(group.pop("_values"))
        distinct_source_count = len(group.pop("_source_indexes"))
        if distinct_source_count > 1 and distinct_value_count > 1:
            status = "conflict"
        elif distinct_source_count > 1:
            status = "agreement"
        else:
            status = "single_source"
        comparisons.append({**group, "status": status})

    conflicts = [
        comparison
        for comparison in comparisons
        if comparison["status"] == "conflict"
    ]
    return {
        "tool": "compare_sources",
        "comparisons": comparisons,
        "conflicts": conflicts,
        "source_count": len(source_items),
        "compared_claim_count": len(comparisons),
        "conflict_count": len(conflicts),
        "agreement_count": sum(
            comparison["status"] == "agreement"
            for comparison in comparisons
        ),
        "skipped_item_count": skipped_item_count,
    }
