from __future__ import annotations

import json
import unittest

from tools.export_report.tool import export_report


class ExportReportTests(unittest.TestCase):
    def test_markdown_report_preserves_sections_order_and_citations(self) -> None:
        items = [
            {
                "section": "AI",
                "title": "First update",
                "summary": "First summary.",
                "source": "Example",
                "url": "https://example.com/first",
            },
            {
                "section": "Research",
                "title": "Second update",
                "summary": "Second summary.",
                "source": "Paper",
                "url": "https://example.com/second",
            },
        ]

        result = export_report(
            title="Daily Research",
            items=items,
            format="markdown",
        )

        self.assertEqual(result["format"], "markdown")
        self.assertEqual(result["content_type"], "text/markdown")
        self.assertEqual(result["item_count"], 2)
        self.assertIn("# Daily Research", result["content"])
        self.assertIn("## AI", result["content"])
        self.assertIn("[Example](https://example.com/first)", result["content"])
        self.assertLess(
            result["content"].index("First update"),
            result["content"].index("Second update"),
        )

    def test_json_report_is_parseable_and_does_not_reuse_input_items(self) -> None:
        item = {"title": "Update", "url": "https://example.com/update"}

        result = export_report(
            title="Research",
            items=[item],
            format="json",
        )
        payload = json.loads(result["content"])

        self.assertEqual(result["content_type"], "application/json")
        self.assertEqual(payload["title"], "Research")
        self.assertEqual(payload["item_count"], 1)
        self.assertEqual(payload["items"], [item])
        item["title"] = "Changed later"
        self.assertEqual(payload["items"][0]["title"], "Update")


if __name__ == "__main__":
    unittest.main()
