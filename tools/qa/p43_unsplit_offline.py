#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed HOST-only consistency check of sanitized P43/P44 evidence.
No device commands, filesystem operations, UART access, or write authorization.
A valid input is never a PASS for any actual device operation.
"""
import argparse
import json
from pathlib import Path

MAX_JSON_BYTES = 65536
MAX_INT = (1 << 63) - 1
REQUIRED = (
    "disk_sectors", "logical_sector_bytes", "gpt_partition_entry_sectors",
    "last_usable_lba", "gpt_primary_valid", "gpt_backup_valid", "p43",
    "p44_present", "p43_mounted", "journal_clean", "backup_verified",
    "recovery_route_verified", "backup_evidence", "recovery_evidence",
    "ssh_state_on_p43", "source_evidence_level",
)
BOOL_FIELDS = (
    "gpt_primary_valid", "gpt_backup_valid", "p44_present", "p43_mounted",
    "journal_clean", "backup_verified", "recovery_route_verified",
    "ssh_state_on_p43",
)
P43_FIELDS = (
    "start_lba", "end_lba", "ext4_block_bytes", "ext4_total_blocks",
    "ext4_used_blocks", "ext4_minimum_blocks", "candidate_target_mib",
    "safety_margin_mib",
)
EVIDENCE_FIELDS = ("reference", "verification_method", "verified_at")


def positive_int(value):
    return type(value) is int and 0 < value <= MAX_INT


def blocked(reasons, status="BLOCKED_STORAGE_EVIDENCE"):
    return {
        "status": status,
        "reasons": sorted(set(reasons)),
        "device_success": False,
        "writes_performed": False,
        "next": "Obtain independently verifiable, sanitized evidence; never infer write permission.",
    }


def inspect(d):
    if not isinstance(d, dict):
        return blocked(["INVALID_INPUT"])
    missing = ["MISSING_" + key.upper() for key in REQUIRED if key not in d]
    if missing:
        return blocked(missing)
    p = d["p43"]
    if not isinstance(p, dict):
        return blocked(["INVALID_P43"])
    missing = ["MISSING_P43_" + key.upper() for key in P43_FIELDS if key not in p]
    if missing:
        return blocked(missing)
    bad = ["INVALID_" + key.upper() for key in BOOL_FIELDS if type(d[key]) is not bool]
    if d["source_evidence_level"] not in (
        "OBSERVED_LOCAL", "KNOWN_HISTORICAL", "SIMULATED_ONLY", "INFERRED", "NOT_TESTED"
    ):
        bad.append("INVALID_SOURCE_EVIDENCE_LEVEL")
    if not positive_int(d["disk_sectors"]) or d["logical_sector_bytes"] not in (512, 4096):
        bad.append("INVALID_DISK_GEOMETRY")
    if not positive_int(d["gpt_partition_entry_sectors"]):
        bad.append("INVALID_GPT_PARTITION_ENTRY_SIZE")
    if not positive_int(d["last_usable_lba"]):
        bad.append("INVALID_GPT_USABLE_RANGE")
    for key in P43_FIELDS:
        if not positive_int(p[key]):
            bad.append("INVALID_P43_" + key.upper())
    for key in ("backup_evidence", "recovery_evidence"):
        item = d[key]
        if not isinstance(item, dict) or any(
            not isinstance(item.get(field), str) or not item[field].strip() or len(item[field]) > 256
            for field in EVIDENCE_FIELDS
        ):
            bad.append("MISSING_OR_INVALID_" + key.upper())
    if "ssh_survives_shrink_verified" in d and type(d["ssh_survives_shrink_verified"]) is not bool:
        bad.append("INVALID_SSH_SURVIVES_SHRINK_VERIFIED")
    if bad:
        return blocked(bad)

    disk = d["disk_sectors"]
    entry = d["gpt_partition_entry_sectors"]
    last = d["last_usable_lba"]
    first_possible = 2 + entry  # protective MBR/header + primary partition array
    last_possible = disk - 2 - entry  # backup partition array + backup header
    reasons = []
    if first_possible > last_possible or last < first_possible or last > last_possible:
        reasons.append("INVALID_GPT_USABLE_RANGE")
    if p["start_lba"] < first_possible or p["start_lba"] > p["end_lba"] or p["end_lba"] >= disk:
        reasons.append("P43_OUTSIDE_DISK")
    if p["end_lba"] > last:
        reasons.append("P43_OUTSIDE_GPT_USABLE_RANGE")
    if p["ext4_block_bytes"] not in (1024, 2048, 4096, 8192, 16384, 32768, 65536):
        reasons.append("UNKNOWN_EXT4_BLOCK_SIZE")
    if (p["ext4_used_blocks"] > p["ext4_total_blocks"] or
            p["ext4_minimum_blocks"] > p["ext4_total_blocks"]):
        reasons.append("INCONSISTENT_EXT4_BLOCKS")
    if p["ext4_total_blocks"] * p["ext4_block_bytes"] > (
            p["end_lba"] - p["start_lba"] + 1) * d["logical_sector_bytes"]:
        reasons.append("EXT4_EXCEEDS_PARTITION")
    target_bytes = p["candidate_target_mib"] * 1048576
    required_bytes = (max(p["ext4_used_blocks"], p["ext4_minimum_blocks"]) *
                      p["ext4_block_bytes"] + p["safety_margin_mib"] * 1048576)
    if required_bytes > target_bytes:
        reasons.append("BLOCKED_P43_CAPACITY")
    if not d["gpt_primary_valid"] or not d["gpt_backup_valid"]:
        reasons.append("GPT_NOT_VERIFIED")
    if d["p43_mounted"] or not d["journal_clean"]:
        reasons.append("BLOCKED_STORAGE")
    if not d["backup_verified"] or not d["recovery_route_verified"]:
        reasons.append("BLOCKED_RECOVERY")
    # Evidence strings are local receipt references, not actual verification.
    # A blank/omitted reference is blocked. Nonblank strings can be falsified.
    if d["p44_present"]:
        reasons.append("P44_PRESENT_VERIFY_INSTEAD_OF_CREATE")
    if d["ssh_state_on_p43"] and d.get("ssh_survives_shrink_verified") is not True:
        reasons.append("BLOCKED_SSH_P43_DEPENDENCY")
    if d["source_evidence_level"] != "OBSERVED_LOCAL":
        reasons.append("NO_CURRENT_DEVICE_EVIDENCE")
    result = blocked(reasons, status="BLOCKED" if reasons else "INSPECT_ONLY_NO_DEVICE_PASS")
    result.update({
        "unit_target_mib": p["candidate_target_mib"],
        "required_minimum_plus_margin_mib_ceil": (required_bytes + 1048575) // 1048576,
        "p44_present": d["p44_present"],
        "evidence_attestation_only": True,
        "next": "Independent on-unit GPT/ext4/backup/recovery checks and separate approval required.",
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Sanitized host JSON; NOT a device")
    args = parser.parse_args()
    if not args.input.is_file() or args.input.stat().st_size > MAX_JSON_BYTES:
        parser.error("input file absent or too large")
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        parser.error("invalid JSON: " + str(exc))
    print(json.dumps(inspect(data), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
