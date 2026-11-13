#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, read-only classifier for SANITIZED SBA6D P43/P44 observations.

Never reads block devices, executes system utilities, probes UART or writes GPT.
Input is a JSON report prepared separately on the owner's machine; it is NOT
an authorization to modify a device. The output is never a device-level PASS.
"""
import argparse
import json
from pathlib import Path

REQUIRED = ("disk_sectors", "logical_sector_bytes", "gpt_primary_valid",
            "gpt_backup_valid", "p43", "p44_present", "p43_mounted",
            "journal_clean", "backup_verified", "recovery_route_verified")
MAX_JSON_BYTES = 65536

def positive_int(value):
    return type(value) is int and 0 < value < (1 << 63)

def inspect(d):
    reasons = []
    if not isinstance(d, dict):
        return {"status": "BLOCKED_STORAGE_EVIDENCE", "reasons": ["INVALID_INPUT"]}
    for name in REQUIRED:
        if name not in d:
            reasons.append("MISSING_" + name.upper())
    if reasons:
        return {"status": "BLOCKED_STORAGE_EVIDENCE", "reasons": reasons}
    disk = d["disk_sectors"]
    sector_bytes = d["logical_sector_bytes"]
    if not positive_int(disk) or sector_bytes not in (512, 4096):
        reasons.append("INVALID_DISK_GEOMETRY")
    for name in ("gpt_primary_valid", "gpt_backup_valid", "p44_present",
                 "p43_mounted", "journal_clean", "backup_verified",
                 "recovery_route_verified"):
        if type(d[name]) is not bool:
            reasons.append("INVALID_" + name.upper())
    p = d["p43"]
    required_p43 = ("start_lba", "end_lba", "ext4_block_bytes", "ext4_total_blocks",
                    "ext4_used_blocks", "ext4_minimum_blocks", "candidate_target_mib",
                    "safety_margin_mib")
    if not isinstance(p, dict):
        return {"status": "BLOCKED_STORAGE_EVIDENCE", "reasons": reasons+["INVALID_P43"]}
    for name in required_p43:
        if name not in p:
            reasons.append("MISSING_P43_" + name.upper())
    if reasons:
        return {"status": "BLOCKED_STORAGE_EVIDENCE", "reasons": sorted(set(reasons))}
    for name in required_p43:
        if not positive_int(p[name]):
            reasons.append("INVALID_P43_" + name.upper())
    if reasons:
        return {"status": "BLOCKED_STORAGE_EVIDENCE", "reasons": sorted(set(reasons))}
    if p["start_lba"] > p["end_lba"] or p["end_lba"] >= disk:
        reasons.append("P43_OUTSIDE_DISK")
    if p["ext4_block_bytes"] not in (1024, 2048, 4096, 8192, 16384, 32768, 65536):
        reasons.append("UNKNOWN_EXT4_BLOCK_SIZE")
    if not (p["ext4_used_blocks"] <= p["ext4_total_blocks"] and
            p["ext4_minimum_blocks"] <= p["ext4_total_blocks"]):
        reasons.append("INCONSISTENT_EXT4_BLOCKS")
    partition_bytes = (p["end_lba"] - p["start_lba"] + 1) * sector_bytes
    fs_bytes = p["ext4_total_blocks"] * p["ext4_block_bytes"]
    if fs_bytes > partition_bytes:
        reasons.append("EXT4_EXCEEDS_PARTITION")
    target_bytes = p["candidate_target_mib"] * 1024 * 1024
    required_bytes = (max(p["ext4_used_blocks"], p["ext4_minimum_blocks"]) *
                      p["ext4_block_bytes"] +
                      p["safety_margin_mib"] * 1024 * 1024)
    if required_bytes > target_bytes:
        reasons.append("BLOCKED_P43_CAPACITY")
    if not d["gpt_primary_valid"] or not d["gpt_backup_valid"]:
        reasons.append("GPT_NOT_VERIFIED")
    if d["p43_mounted"] or not d["journal_clean"]:
        reasons.append("BLOCKED_STORAGE")
    if not d["backup_verified"] or not d["recovery_route_verified"]:
        reasons.append("BLOCKED_RECOVERY")
    if d["p44_present"]:
        reasons.append("P44_PRESENT_VERIFY_INSTEAD_OF_CREATE")
    if d.get("ssh_state_on_p43") is True and d.get("ssh_survives_shrink_verified") is not True:
        reasons.append("BLOCKED_SSH_P43_DEPENDENCY")
    if d.get("source_evidence_level") != "OBSERVED_LOCAL":
        reasons.append("NO_CURRENT_DEVICE_EVIDENCE")
    return {
        "status": "BLOCKED" if reasons else "INSPECT_ONLY_NO_DEVICE_PASS",
        "reasons": sorted(set(reasons)),
        "unit_target_mib": p["candidate_target_mib"],
        "required_minimum_plus_margin_mib_ceil": (required_bytes + (1<<20)-1)//(1<<20),
        "p44_present": d["p44_present"],
        "device_success": False,
        "writes_performed": False,
        "next": "Independent on-unit GPT/ext4 verification and separate approval are still required."
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Sanitized host JSON file; NOT a device")
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
