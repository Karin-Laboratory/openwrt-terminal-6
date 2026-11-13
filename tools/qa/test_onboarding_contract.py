#!/usr/bin/env python3
"""Host-only consistency checks for first-time owner / agent onboarding."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
start = (ROOT / "START-HERE.ja.md").read_text(encoding="utf-8")
release = (ROOT / "docs/RELEASE-GATES.md").read_text(encoding="utf-8")
data = json.loads((ROOT / "docs/TERMINAL6-PREPARATION-AGENT-WORKFLOW.json").read_text(encoding="utf-8"))

assert data["schema_version"] == "1.0.0"
assert "START-HERE.ja.md" in readme
assert "TERMINAL6-PREPARATION-AGENT-WORKFLOW.json" in readme
assert "2026-11-11" in readme and "sba6d-nora2-rc16-20261110-r1" in readme
assert "sba6d-nora2-rc16-20261110-r1" in release
assert "Public distribution remains source-only today" not in readme
assert "no installable release" not in readme
assert "START-HERE.ja.md" in start
assert data["release_reconciliation"]["p44_required"]
assert not data["release_reconciliation"]["p43_p44_split_tool_in_release"]
assert not data["release_reconciliation"]["ready_for_unprepared_device"]
assert data["release_reconciliation"]["do_not_flash_during_this_workflow"]
assert len(data["stages"]) == 8
assert len({x["id"] for x in data["stages"]}) == 8
assert data["permission_policy"]["gpt_mutation_and_format"] == "EXPLICIT_APPROVAL"
assert data["permission_policy"]["persistent_ssh_change"] == "EXPLICIT_APPROVAL"
assert "NOT_TESTED" in data["observational_levels"]
for stage in data["stages"]:
    assert stage["required_evidence"] and stage["stop_conditions"]
    assert "PASS" in stage["states"] and "BLOCKED" in stage["states"]
for item in data["entry_documents"]:
    if item["repository"] == "Karin-Laboratory/openwrt-terminal-6":
        assert (ROOT / item["path"]).is_file(), item["path"]

# Explicitly guard contradictory completion language.
assert "未完成" in start
assert "再起動後" in start
assert "事前" in start or "承認" in start
assert re.search(r"P43.*P44", start, re.S)
print("ONBOARDING_DOCS_JSON_CONSISTENCY_PASS")
