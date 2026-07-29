from __future__ import annotations

import unittest

from tools.dedupe.tool import dedupe_items


class DedupeItemsTests(unittest.TestCase):
    def test_none_input_returns_empty_result(self) -> None:
        self.assertEqual(
            dedupe_items(None),
            {
                "tool": "dedupe",
                "items": [],
                "original_count": 0,
                "deduplicated_count": 0,
            },
        )

    def test_empty_input_returns_empty_result(self) -> None:
        self.assertEqual(dedupe_items([])["items"], [])

    def test_duplicate_urls_keep_first_and_preserve_order(self) -> None:
        first = {"title": "First", "url": "https://example.com/a"}
        second = {"title": "Second", "url": "https://example.com/b"}
        duplicate = {"title": "Duplicate", "url": "https://example.com/a"}

        result = dedupe_items([first, second, duplicate])

        self.assertEqual(result["items"], [first, second])
        self.assertEqual(result["original_count"], 3)
        self.assertEqual(result["deduplicated_count"], 2)

    def test_url_hostname_case_and_trailing_slash_are_ignored(self) -> None:
        first = {"title": "First", "url": "https://EXAMPLE.com/article/"}
        duplicate = {"title": "Duplicate", "url": "https://example.COM/article"}

        result = dedupe_items([first, duplicate])

        self.assertEqual(result["items"], [first])
        self.assertEqual(result["deduplicated_count"], 1)

    def test_titles_without_urls_ignore_case_and_collapsed_whitespace(self) -> None:
        first = {"title": "  AI   Research\nUpdate  ", "summary": "First"}
        duplicate = {"title": "ai research update", "summary": "Second"}

        result = dedupe_items([first, duplicate])

        self.assertEqual(result["items"], [first])
        self.assertEqual(result["deduplicated_count"], 1)

    def test_items_without_url_or_title_are_all_preserved(self) -> None:
        first = {"summary": "First"}
        second = {"summary": "First"}

        result = dedupe_items([first, second])

        self.assertEqual(result["items"], [first, second])
        self.assertEqual(result["deduplicated_count"], 2)

    def test_urls_take_priority_over_matching_titles(self) -> None:
        first = {"title": "Same", "url": "https://example.com/one"}
        second = {"title": "Same", "url": "https://example.com/two"}

        self.assertEqual(dedupe_items([first, second])["items"], [first, second])

    def test_unusable_urls_fall_back_to_normalized_titles(self) -> None:
        first = {"title": "Same research", "url": "not-a-url"}
        duplicate = {"title": "  SAME   RESEARCH ", "url": "also-not-a-url"}

        self.assertEqual(dedupe_items([first, duplicate])["items"], [first])

    def test_input_dictionaries_are_not_mutated_or_reused(self) -> None:
        first = {"title": "First", "url": "https://example.com/"}
        original = dict(first)

        result = dedupe_items([first])

        self.assertEqual(first, original)
        self.assertIsNot(result["items"][0], first)


if __name__ == "__main__":
    unittest.main()
