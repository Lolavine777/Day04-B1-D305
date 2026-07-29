from __future__ import annotations

import unittest

from tools.compare_sources.tool import compare_sources


class CompareSourcesTests(unittest.TestCase):
    def test_conflicting_claim_values_are_reported(self) -> None:
        items = [
            {
                "source": "Source A",
                "url": "https://a.example/report",
                "claims": {"Launch date": "June 1", "Price": 20},
            },
            {
                "source": "Source B",
                "url": "https://b.example/report",
                "claims": {"Launch date": "June 2", "Price": 20},
            },
        ]

        result = compare_sources(items)

        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["conflict_count"], 1)
        self.assertEqual(result["agreement_count"], 1)
        self.assertEqual(result["conflicts"][0]["claim"], "Launch date")
        self.assertEqual(
            [observation["value"] for observation in result["conflicts"][0]["observations"]],
            ["June 1", "June 2"],
        )

    def test_claim_names_text_values_and_equivalent_numbers_are_normalized(self) -> None:
        result = compare_sources(
            [
                {
                    "source": "A",
                    "claims": {" Revenue ": "  Strong   Growth ", "Users": 20},
                },
                {
                    "source": "B",
                    "claims": {"revenue": "strong growth", "users": 20.0},
                },
            ]
        )

        self.assertEqual(result["conflict_count"], 0)
        self.assertEqual(result["agreement_count"], 2)

    def test_one_source_cannot_create_a_conflict_with_itself(self) -> None:
        result = compare_sources(
            [
                {
                    "source": "A",
                    "claims": {"Price": 20, " price ": 21},
                }
            ]
        )

        self.assertEqual(result["conflict_count"], 0)
        self.assertEqual(result["agreement_count"], 0)
        self.assertEqual(result["comparisons"][0]["status"], "single_source")


if __name__ == "__main__":
    unittest.main()
