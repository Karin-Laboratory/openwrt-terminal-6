#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
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

# Agent-entry contract checks (host-only; deliberately never connects to UART).
entry = json.loads((ROOT / "agent-entry.json").read_text(encoding="utf-8"))
assert entry["schema_version"] == data["schema_version"]
assert entry["canonical_workflow"] == "docs/TERMINAL6-PREPARATION-AGENT-WORKFLOW.json"
assert entry["human_entry"] == "START-HERE.ja.md"
assert len(entry["initial_agent_actions"]) >= 6
assert [a["order"] for a in entry["initial_agent_actions"]] == list(range(1, len(entry["initial_agent_actions"]) + 1))
assert len(entry["machine_decisions"]) >= 7
assert len(entry["audit_scenarios"]) >= 7
assert entry["write_policy"]["default"] == "DENY"
assert data["permission_policy"]["gpt_mutation_and_format"] == "EXPLICIT_APPROVAL"
assert "S05" in " ".join(entry["completion"]["required"])
assert "S08" in " ".join(entry["completion"]["required"])
assert entry["concrete_tool_status"]["p43_p44_v04_r3"]["distribution"].startswith("Private")
assert "intentionally rejects" in entry["concrete_tool_status"]["p43_p44_v04_r3"]["guarded_apply"]
assert entry["evidence_provenance"]["publication_rule"].startswith("Never require")
assert entry["security_addendum"]["network"].find("strict host-key") != -1
assert set(entry["agent_modes"]) == {"OFFLINE_AUDIT", "HOST_PREFLIGHT", "DEVICE_READONLY", "OWNER_APPROVED_MUTATION"}
assert len({s["id"] for s in entry["audit_scenarios"]}) == len(entry["audit_scenarios"])
for p in entry["required_reading"]:
    assert (ROOT / p).is_file(), p
for s in entry["audit_scenarios"]:
    assert s["expected"] in {d["result"] for d in entry["machine_decisions"]}
assert "agent-entry.json" in (ROOT / "AGENT-START.ja.md").read_text(encoding="utf-8")
# Offline P43 evidence classifier tests (no devices, shell execution or write APIs).
import runpy
inspector = runpy.run_path(str(ROOT / "tools/qa/p43_unsplit_offline.py"))["inspect"]
fixture = {
    "disk_sectors": 9000000, "logical_sector_bytes": 512,
    "gpt_primary_valid": True, "gpt_backup_valid": True,
    "p43": {"start_lba": 1500000, "end_lba": 7600000,
            "ext4_block_bytes": 4096, "ext4_total_blocks": 750000,
            "ext4_used_blocks": 50000, "ext4_minimum_blocks": 70000,
            "candidate_target_mib": 600, "safety_margin_mib": 100},
    "p44_present": False, "p43_mounted": False, "journal_clean": True,
    "backup_verified": True, "recovery_route_verified": True,
    "source_evidence_level": "OBSERVED_LOCAL", "ssh_state_on_p43": False
}
assert inspector(fixture)["status"] == "INSPECT_ONLY_NO_DEVICE_PASS"
assert inspector(fixture)["device_success"] is False
import copy
bad = copy.deepcopy(fixture); bad["p43"]["candidate_target_mib"] = 100
assert "BLOCKED_P43_CAPACITY" in inspector(bad)["reasons"]
bad = copy.deepcopy(fixture); bad["p43_mounted"] = True
assert "BLOCKED_STORAGE" in inspector(bad)["reasons"]
bad = copy.deepcopy(fixture); bad["journal_clean"] = False
assert "BLOCKED_STORAGE" in inspector(bad)["reasons"]
bad = copy.deepcopy(fixture); bad["ssh_state_on_p43"] = True
assert "BLOCKED_SSH_P43_DEPENDENCY" in inspector(bad)["reasons"]
bad = copy.deepcopy(fixture); bad["p44_present"] = True
assert "P44_PRESENT_VERIFY_INSTEAD_OF_CREATE" in inspector(bad)["reasons"]
bad = copy.deepcopy(fixture); del bad["p43"]["ext4_minimum_blocks"]
assert inspector(bad)["status"] == "BLOCKED_STORAGE_EVIDENCE"
bad = copy.deepcopy(fixture); bad["source_evidence_level"] = "SIMULATED_ONLY"
assert "NO_CURRENT_DEVICE_EVIDENCE" in inspector(bad)["reasons"]
assert len(entry["stage_readiness"]["stages"]) == 8
assert entry["stage_readiness"]["first_public_documentation_blocker"] == "S03"
assert {s["id"] for s in entry["audit_scenarios"]} >= {"T08","T09","T10"}
assert "ext4_minimum_blocks" in (ROOT / "tools/qa/p43_unsplit_offline.py").read_text()
print("UNSPLIT_OFFLINE_CLASSIFIER_PASS")
# Third-party audit remediation: canonical stage identity and fail-closed FW table.
fw = json.loads((ROOT / "docs/TERMINAL6-FW-COMPATIBILITY.json").read_text(encoding="utf-8"))
workflow_stage_ids = {item["id"]: item["name"] for item in data["stages"]}
assert entry["stage_identity_contract"]["stage_ids"] == workflow_stage_ids
assert entry["stage_identity_contract"]["preflight"].find("not S01 PASS") != -1
assert fw["validated_profiles"] == []
assert fw["policy"]["write_default"] == "DENY"
assert fw["machine_results"]["no_validated_profile"] == "BLOCKED_NO_VALIDATED_MUTATION_PROFILE"
assert entry["compatibility_gate"]["reference"] in entry["required_reading"]
assert entry["compatibility_gate"]["no_validated_mutation_profile"] == "BLOCKED_NO_VALIDATED_MUTATION_PROFILE"
assert {"T11", "T12"} <= {x["id"] for x in entry["audit_scenarios"]}
assert "S05" in (ROOT / "docs/AB-FALLBACK-RESEARCH.md").read_text(encoding="utf-8")
assert "デフォルト固定" in (ROOT / "START-HERE.ja.md").read_text(encoding="utf-8")
for required_path in ["docs/AB-FALLBACK-RESEARCH.md", "docs/TERMINAL6-FW-COMPATIBILITY.json"]:
    assert (ROOT / required_path).is_file()
print("EXTERNAL_AUDIT_CORRECTION_PASS")
print("AGENT_ENTRY_OFFLINE_AUDIT_PASS")

print("ONBOARDING_DOCS_JSON_CONSISTENCY_PASS")
