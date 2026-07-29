#!/usr/bin/env python3
"""
Static Submission Validator for Team B1 (Day 04 Lab v2)
Owner: Nguyễn Trần Nghĩa (Student ID: 2A202601664)

This script validates static deliverables, JSON schemas, eval group cases,
tool declarations, registry setups, and git tracking rules using ONLY
the Python standard library.
"""

from pathlib import Path
import csv
import json
import os
import re
import subprocess
import sys


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    os.chdir(base_dir)

    print("==================================================")
    print("      Team B1 Submission Static Validator         ")
    print("==================================================")
    print(f"Working Directory: {base_dir}\n")

    all_passed = True

    def report(name: str, passed: bool, detail: str = ""):
        nonlocal all_passed
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        msg = f"{status} {name}"
        if detail:
            msg += f" - {detail}"
        print(msg)

    # 1. Required static files
    required_files = [
        "artifacts/system_prompt.md",
        "artifacts/tools.yaml",
        "artifacts/version_log.csv",
        "artifacts/REPORT.md",
    ]
    for rel_path in required_files:
        fpath = base_dir / rel_path
        report(
            f"Deliverable File: {rel_path}",
            fpath.is_file(),
            f"Found at {rel_path}" if fpath.is_file() else "File missing",
        )

    # 2. Valid JSON datasets
    json_datasets = [
        "data/eval_base.json",
        "data/eval_research_extension.json",
        "data/eval_group.json",
    ]
    loaded_jsons = {}
    for rel_path in json_datasets:
        fpath = base_dir / rel_path
        if not fpath.is_file():
            report(f"Valid JSON: {rel_path}", False, "File missing")
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded_jsons[rel_path] = data
            report(f"Valid JSON: {rel_path}", True, "Syntax valid")
        except Exception as exc:
            report(f"Valid JSON: {rel_path}", False, f"JSON parse error: {exc}")

    # 3-6. Group Eval dataset validations (data/eval_group.json)
    group_data = loaded_jsons.get("data/eval_group.json")
    if group_data and isinstance(group_data, dict):
        cases = group_data.get("cases", [])
        
        # Check total count = 10
        case_count = len(cases)
        report(
            "Group Eval Count",
            case_count == 10,
            f"Found {case_count} cases (Expected 10)",
        )

        # Check 5 query and 5 turns
        query_cases = [c for c in cases if "query" in c and "turns" not in c]
        turns_cases = [c for c in cases if "turns" in c]
        report(
            "Group Eval Structure",
            len(query_cases) == 5 and len(turns_cases) == 5,
            f"Single-turn (query): {len(query_cases)}/5, Multi-turn (turns): {len(turns_cases)}/5",
        )

        # Check unique IDs
        case_ids = [c.get("id") for c in cases if "id" in c]
        unique_ids = set(case_ids)
        report(
            "Group Eval Unique IDs",
            len(case_ids) == len(cases) and len(unique_ids) == len(cases),
            f"Unique IDs: {len(unique_ids)}/{len(cases)}",
        )

        # Check allowed failure types
        allowed_types = {
            "wrong_tool",
            "wrong_arg_value",
            "wrong_boundary",
            "unnecessary_tool",
            "out_of_scope",
            "missing_info",
        }
        invalid_failures = [
            c.get("id") for c in cases if c.get("failure_type") not in allowed_types
        ]
        report(
            "Group Eval Failure Types",
            len(invalid_failures) == 0,
            "All failure types allowed"
            if len(invalid_failures) == 0
            else f"Invalid failure types in cases: {invalid_failures}",
        )
    else:
        report("Group Eval Count", False, "eval_group.json missing or invalid")
        report("Group Eval Structure", False, "eval_group.json missing or invalid")
        report("Group Eval Unique IDs", False, "eval_group.json missing or invalid")
        report("Group Eval Failure Types", False, "eval_group.json missing or invalid")

    # 7. Expected tools declared in tools.yaml
    tools_yaml = base_dir / "artifacts/tools.yaml"
    declared_tools = []
    if tools_yaml.is_file():
        content = tools_yaml.read_text(encoding="utf-8")
        declared_tools = re.findall(r"^\s*-\s*name:\s*([a-zA-Z0-9_]+)", content, re.MULTILINE)
        if not declared_tools:
            declared_tools = re.findall(r"name:\s*([a-zA-Z0-9_]+)", content)
        core_expected = {"clarify", "timeline", "social_search", "lookup", "fetch", "format"}
        missing_core = core_expected - set(declared_tools)
        report(
            "Declared Tools in tools.yaml",
            len(missing_core) == 0,
            f"Declared: {declared_tools}" if not missing_core else f"Missing core tools: {missing_core}",
        )
    else:
        report("Declared Tools in tools.yaml", False, "tools.yaml missing")

    # 8. Expected tools registered in TOOL_FUNCTIONS
    init_py = base_dir / "tools/__init__.py"
    registered_tools = []
    if init_py.is_file():
        content = init_py.read_text(encoding="utf-8")
        # Match dict keys in TOOL_FUNCTIONS
        match = re.search(r"TOOL_FUNCTIONS\s*(?::\s*[^=]+)?=\s*\{([^}]+)\}", content, re.DOTALL)
        if match:
            registered_tools = re.findall(r"\"([a-zA-Z0-9_]+)\"\s*:", match.group(1))
        core_expected = {"clarify", "timeline", "social_search", "lookup", "fetch", "format"}
        missing_reg = core_expected - set(registered_tools)
        report(
            "Registered Tools in TOOL_FUNCTIONS",
            len(missing_reg) == 0,
            f"Registered: {registered_tools}" if not missing_reg else f"Missing registrations: {missing_reg}",
        )
    else:
        report("Registered Tools in TOOL_FUNCTIONS", False, "tools/__init__.py missing")

    # 9. Tool folders contain TOOL.md and tool.py
    tools_dir = base_dir / "tools"
    all_tools_valid = True
    tool_errors = []
    if tools_dir.is_dir():
        for tool_folder in tools_dir.iterdir():
            if tool_folder.is_dir() and not tool_folder.name.startswith(("_", ".")):
                has_md = (tool_folder / "TOOL.md").is_file()
                has_py = (tool_folder / "tool.py").is_file()
                if not (has_md and has_py):
                    all_tools_valid = False
                    tool_errors.append(f"{tool_folder.name} (TOOL.md: {has_md}, tool.py: {has_py})")
        report(
            "Tool Folders Structure",
            all_tools_valid,
            "All tool folders contain TOOL.md and tool.py"
            if all_tools_valid
            else f"Incomplete tool folders: {', '.join(tool_errors)}",
        )
    else:
        report("Tool Folders Structure", False, "tools/ directory missing")

    # 10. version_log.csv contains v0, v1, v2, v3
    vlog_path = base_dir / "artifacts/version_log.csv"
    versions_found = set()
    if vlog_path.is_file():
        try:
            with open(vlog_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("version"):
                        versions_found.add(row["version"].strip())
            required_versions = {"v0", "v1", "v2", "v3"}
            has_all_v = required_versions.issubset(versions_found)
            report(
                "Version Log Coverage (v0-v3)",
                has_all_v,
                f"Found versions: {sorted(list(versions_found))} (Required: v0, v1, v2, v3)",
            )
        except Exception as exc:
            report("Version Log Coverage (v0-v3)", False, f"CSV read error: {exc}")
    else:
        report("Version Log Coverage (v0-v3)", False, "version_log.csv missing")

    # 11. app.py exists and Streamlit in requirements.txt
    app_py = base_dir / "app.py"
    req_txt = base_dir / "requirements.txt"
    app_exists = app_py.is_file()
    has_streamlit = False
    if req_txt.is_file():
        req_content = req_txt.read_text(encoding="utf-8").lower()
        has_streamlit = "streamlit" in req_content
    report(
        "UI Deliverables (app.py & requirements.txt)",
        app_exists and has_streamlit,
        f"app.py: {app_exists}, streamlit in requirements.txt: {has_streamlit}",
    )

    # 12. Git tracked files check for secrets / forbidden paths
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = res.stdout.splitlines()
        forbidden_patterns = [r"\.env$", r"\.venv", r"__pycache__", r"\.pem$", r"\.key$"]
        forbidden_tracked = []
        for tf in tracked_files:
            for pattern in forbidden_patterns:
                if re.search(pattern, tf):
                    forbidden_tracked.append(tf)
        report(
            "Git Secret & Ignored File Rule",
            len(forbidden_tracked) == 0,
            "Clean tracking"
            if len(forbidden_tracked) == 0
            else f"Forbidden files tracked in git: {forbidden_tracked}",
        )
    except Exception as exc:
        report("Git Secret & Ignored File Rule", False, f"Git ls-files check failed: {exc}")

    print("\n--------------------------------------------------")
    if all_passed:
        print("RESULT: ALL STATIC CHECKS PASSED!")
        print("--------------------------------------------------")
        return 0
    else:
        print("RESULT: STATIC CHECKS FAILED (Deliverables incomplete)")
        print("--------------------------------------------------")
        return 1


if __name__ == "__main__":
    sys.exit(main())
