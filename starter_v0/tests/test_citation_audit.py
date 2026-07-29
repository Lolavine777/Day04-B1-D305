from __future__ import annotations

import unittest

from tools.citation_audit.tool import citation_audit


class CitationAuditTests(unittest.TestCase):
    def test_invalid_and_missing_citations_are_reported(self) -> None:
        claims = [
            {
                "text": "Claim with evidence",
                "url": "https://example.com/report",
                "source": "Example Research",
            },
            {
                "text": "Claim without source",
                "url": "https://example.com/other",
            },
            {
                "text": "Claim with unsafe URL",
                "url": "javascript:alert(1)",
                "source": "Unknown",
            },
        ]

        result = citation_audit(claims)

        self.assertEqual(result["total_claims"], 3)
        self.assertEqual(result["valid_claims"], 1)
        self.assertEqual(result["invalid_claims"], 2)
        self.assertEqual(result["coverage_percent"], 33.33)
        self.assertEqual(result["audited_claims"][0]["issues"], [])
        self.assertEqual(
            result["audited_claims"][1]["issues"],
            ["missing_source"],
        )
        self.assertEqual(
            result["audited_claims"][2]["issues"],
            ["invalid_url"],
        )


if __name__ == "__main__":
    unittest.main()
