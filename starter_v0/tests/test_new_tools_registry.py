from __future__ import annotations

import unittest
from pathlib import Path

from guardrails import check_tool_call
from tools import TOOL_FUNCTIONS, load_tool_declarations


ROOT = Path(__file__).resolve().parents[1]
NEW_TOOLS = {"compare_sources", "citation_audit", "export_report"}


class NewToolsRegistryTests(unittest.TestCase):
    def test_new_tools_are_declared_registered_and_documented(self) -> None:
        declarations = load_tool_declarations(
            ROOT / "artifacts" / "tools.yaml"
        )
        declared = {item["name"] for item in declarations}

        self.assertTrue(NEW_TOOLS <= declared)
        self.assertTrue(NEW_TOOLS <= set(TOOL_FUNCTIONS))
        for name in NEW_TOOLS:
            self.assertTrue((ROOT / "tools" / name / "TOOL.md").is_file())
            self.assertTrue((ROOT / "tools" / name / "tool.py").is_file())

    def test_system_prompt_routes_new_tools_as_post_processing(self) -> None:
        prompt = (ROOT / "artifacts" / "system_prompt.md").read_text(
            encoding="utf-8"
        )
        normalized_prompt = " ".join(prompt.split())

        for name in NEW_TOOLS:
            self.assertIn(f"`{name}`", prompt)
        self.assertIn(
            "after research items have been collected",
            normalized_prompt,
        )

    def test_product_guardrail_recognizes_new_tools(self) -> None:
        for name in NEW_TOOLS:
            verdict = check_tool_call(name, {})
            self.assertTrue(verdict["allowed"], verdict)


if __name__ == "__main__":
    unittest.main()
