#!/usr/bin/env python3
"""Static, standard-library-only release checks for Team B1."""

from __future__ import annotations

import ast
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXPECTED_TOOLS = {
    "clarify", "timeline", "social_search", "lookup", "fetch", "format",
    "send", "policy", "papers", "paper_text", "dedupe",
}
ALLOWED_FAILURE_TYPES = {
    "wrong_tool", "wrong_arg_value", "wrong_boundary", "unnecessary_tool",
    "out_of_scope", "missing_info",
}


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def declared_tool_names(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return set(re.findall(r"^\s*-\s*name:\s*([A-Za-z0-9_]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE))


def registered_tool_names(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "TOOL_FUNCTIONS" for target in node.targets):
            if isinstance(node.value, ast.Dict):
                return {key.value for key in node.value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    return set()


def load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as error:
        return None, str(error)


def git_tracked_paths(root: Path) -> list[str] | None:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.splitlines()


def forbidden_paths(paths: Iterable[str]) -> list[str]:
    bad: list[str] = []
    for path in paths:
        parts = [part.lower() for part in Path(path).parts]
        name = parts[-1] if parts else ""
        if ".venv" in parts or "__pycache__" in parts or name == ".env":
            bad.append(path)
        elif name.endswith((".pem", ".key", ".p12", ".pfx")) or any(word in name for word in ("secret", "credential", "api_key")):
            bad.append(path)
    return bad


def validate(root: Path, tracked_paths: list[str] | None = None) -> list[Check]:
    checks: list[Check] = []
    required = ("artifacts/system_prompt.md", "artifacts/tools.yaml", "artifacts/version_log.csv", "artifacts/REPORT.md")
    for relative in required:
        exists = (root / relative).is_file()
        checks.append(Check(f"deliverable {relative}", exists, "present" if exists else "missing"))

    datasets: dict[str, object | None] = {}
    for relative in ("data/eval_base.json", "data/eval_research_extension.json", "data/eval_group.json"):
        path = root / relative
        data, error = load_json(path)
        datasets[relative] = data
        checks.append(Check(f"valid JSON {relative}", error is None, "valid" if error is None else error))

    group = datasets["data/eval_group.json"]
    cases = group.get("cases") if isinstance(group, dict) else None
    if not isinstance(cases, list):
        cases = []
    checks.append(Check("group case count", len(cases) == 10, f"found {len(cases)}; expected 10"))
    query_cases = [case for case in cases if isinstance(case, dict) and "query" in case and "turns" not in case]
    turn_cases = [case for case in cases if isinstance(case, dict) and "turns" in case and "query" not in case]
    checks.append(Check("group case shape", len(query_cases) == 5 and len(turn_cases) == 5, f"query={len(query_cases)}/5, turns={len(turn_cases)}/5"))
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    checks.append(Check("unique group case IDs", len(ids) == len(cases) and None not in ids and len(set(ids)) == len(ids), f"unique={len(set(ids))}/{len(cases)}"))
    invalid_types = [case.get("id", "<missing id>") for case in cases if not isinstance(case, dict) or case.get("failure_type") not in ALLOWED_FAILURE_TYPES]
    checks.append(Check("allowed group failure types", not invalid_types, "valid" if not invalid_types else f"invalid: {', '.join(map(str, invalid_types))}"))

    declared = declared_tool_names(root / "artifacts/tools.yaml")
    missing_declared = sorted(EXPECTED_TOOLS - declared)
    checks.append(Check("expected tools declared", not missing_declared, "all declared" if not missing_declared else f"missing: {', '.join(missing_declared)}"))
    registered = registered_tool_names(root / "tools/__init__.py")
    missing_registered = sorted(EXPECTED_TOOLS - registered)
    checks.append(Check("expected tools registered in TOOL_FUNCTIONS", not missing_registered, "all registered" if not missing_registered else f"missing: {', '.join(missing_registered)}"))

    incomplete_folders = [name for name in sorted(declared) if not (root / "tools" / name / "TOOL.md").is_file() or not (root / "tools" / name / "tool.py").is_file()]
    checks.append(Check("declared tool folders", not incomplete_folders, "complete" if not incomplete_folders else f"missing TOOL.md/tool.py: {', '.join(incomplete_folders)}"))

    versions: set[str] = set()
    try:
        with (root / "artifacts/version_log.csv").open(encoding="utf-8", newline="") as file:
            versions = {row.get("version", "").strip() for row in csv.DictReader(file)}
    except OSError:
        pass
    missing_versions = sorted({"v0", "v1", "v2", "v3"} - versions)
    checks.append(Check("version log v0-v3", not missing_versions, "complete" if not missing_versions else f"missing: {', '.join(missing_versions)}"))

    requirements = (root / "requirements.txt").read_text(encoding="utf-8").lower() if (root / "requirements.txt").is_file() else ""
    has_ui = (root / "app.py").is_file() and any(line.strip().startswith("streamlit") for line in requirements.splitlines())
    checks.append(Check("UI deliverables", has_ui, "app.py and Streamlit requirement present" if has_ui else "need app.py and a Streamlit requirement"))

    paths = git_tracked_paths(root) if tracked_paths is None else tracked_paths
    invalid_paths = forbidden_paths(paths or [])
    checks.append(Check("tracked-path secret rule", paths is not None and not invalid_paths, "clean" if paths is not None and not invalid_paths else (f"forbidden: {', '.join(invalid_paths)}" if paths is not None else "git ls-files unavailable")))
    return checks


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    checks = validate(root)
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
