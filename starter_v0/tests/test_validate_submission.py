import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_submission import validate


EXPECTED_TOOLS = {
    "clarify", "timeline", "social_search", "lookup", "fetch", "format",
    "send", "policy", "papers", "paper_text", "dedupe",
}


class ValidateSubmissionTests(unittest.TestCase):
    def test_reports_incomplete_group_and_accepts_complete_static_submission(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "artifacts").mkdir()
            (root / "data").mkdir()
            (root / "tools").mkdir()
            (root / "artifacts/system_prompt.md").touch()
            (root / "artifacts/REPORT.md").touch()
            (root / "artifacts/version_log.csv").write_text("version\nv0\nv1\nv2\nv3\n", encoding="utf-8")
            (root / "artifacts/tools.yaml").write_text(
                "tools:\n" + "".join(f"  - name: {name}\n" for name in sorted(EXPECTED_TOOLS)),
                encoding="utf-8",
            )
            (root / "tools/__init__.py").write_text(
                "TOOL_FUNCTIONS = {" + ", ".join(f"'{name}': None" for name in sorted(EXPECTED_TOOLS)) + "}\n",
                encoding="utf-8",
            )
            for name in EXPECTED_TOOLS:
                folder = root / "tools" / name
                folder.mkdir()
                (folder / "TOOL.md").touch()
                (folder / "tool.py").touch()
            for name in ("eval_base.json", "eval_research_extension.json"):
                (root / "data" / name).write_text("{}", encoding="utf-8")
            (root / "data/eval_group.json").write_text(json.dumps({"cases": []}), encoding="utf-8")
            (root / "app.py").touch()
            (root / "requirements.txt").write_text("streamlit>=1.30\n", encoding="utf-8")

            failed = {check.name for check in validate(root, tracked_paths=[] ) if not check.passed}
            self.assertTrue({"group case count", "group case shape"}.issubset(failed))

            cases = [
                {"id": f"q{index}", "query": "x", "failure_type": "wrong_tool"}
                for index in range(5)
            ] + [
                {"id": f"t{index}", "turns": [], "failure_type": "wrong_tool"}
                for index in range(5)
            ]
            (root / "data/eval_group.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
            self.assertTrue(all(check.passed for check in validate(root, tracked_paths=[])))


if __name__ == "__main__":
    unittest.main()
