from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit


def _is_valid_citation_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    url = value.strip()
    if any(character.isspace() for character in url):
        return False
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError:
        return False
    return parsed.scheme.casefold() in {"http", "https"} and bool(
        parsed.hostname
    )


def citation_audit(
    claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_claims = claims or []
    audited_claims: list[dict[str, Any]] = []
    valid_count = 0

    for claim in source_claims:
        issues: list[str] = []
        text = claim.get("text")
        url = claim.get("url")
        source = claim.get("source")

        if not isinstance(text, str) or not text.strip():
            issues.append("missing_claim_text")
        if not isinstance(url, str) or not url.strip():
            issues.append("missing_url")
        elif not _is_valid_citation_url(url):
            issues.append("invalid_url")
        if not isinstance(source, str) or not source.strip():
            issues.append("missing_source")

        valid = not issues
        valid_count += int(valid)
        audited_claims.append(
            {
                **deepcopy(claim),
                "valid": valid,
                "issues": issues,
            }
        )

    total = len(source_claims)
    return {
        "tool": "citation_audit",
        "audited_claims": audited_claims,
        "total_claims": total,
        "valid_claims": valid_count,
        "invalid_claims": total - valid_count,
        "coverage_percent": round(valid_count * 100 / total, 2)
        if total
        else 0.0,
    }
