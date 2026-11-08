#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed boot/P26 pairing and UART stage evidence checker (offline only)."""
import argparse
import hashlib
import json
from pathlib import Path
import re

P26_BYTES = 134_217_728
STAGES = ("KERNEL_HANDOFF", "RAM_INIT_ENTER", "P26_RO_VERIFIED",
          "SWITCH_ROOT_COMPLETE", "PROCD_PID1", "UBUSD_READY", "NETIFD_READY")
SHA = re.compile(r"^[0-9a-f]{64}$")


def bound_pair(p26_receipt, initramfs_binding):
    """Verify a genuine 128MiB receipt is bound to the initramfs expected hash."""
    actual = p26_receipt.get("p26_sha256")
    pinned = initramfs_binding.get("expected_p26_sha256")
    if (p26_receipt.get("partition_bytes") != P26_BYTES or
        not isinstance(actual, str) or not SHA.fullmatch(actual) or
        not isinstance(pinned, str) or pinned != actual):
        raise ValueError("P26_INITRAMFS_SHA_MISMATCH")
    if initramfs_binding.get("policy") != "read-only-sha256-before-switch-root":
        raise ValueError("P26_VERIFY_POLICY_INVALID")
    return actual


def validate_trace(records, mode="normal"):
    """Review *observed* trace, not a plan. Missing/duplicate markers fail."""
    if mode not in ("normal", "ram-only"):
        raise ValueError("BOOT_MODE")
    required = STAGES if mode == "normal" else STAGES[:2]
    if not isinstance(records, list) or not all(isinstance(x, str) for x in records):
        raise ValueError("BOOT_TRACE_TYPE")
    hits = []
    for marker in required:
        matched = [i for i, line in enumerate(records) if
                   re.search(r"(?<![A-Z_])AIR6_" + marker + r"(?![A-Z_])", line)]
        if len(matched) != 1:
            raise ValueError("BOOT_MISSING_OR_DUPLICATE_" + marker)
        hits.append(matched[0])
    if hits != sorted(hits) or len(hits) != len(set(hits)):
        raise ValueError("BOOT_MARKER_ORDER")
    if mode == "normal":
        # A string mentioning procd is not proof; trace must explicitly say PID=1.
        procd_line = records[hits[4]]
        if not re.search(r"\bPID=1\b", procd_line):
            raise ValueError("BOOT_PROCD_PID1_UNPROVEN")
        if any("AIR6_RAM_ONLY" in line for line in records):
            raise ValueError("BOOT_UNEXPECTED_RAM_ONLY")
        if sum("AIR6_CONFIG_GENERATE_OK" in line for line in records) != 1:
            raise ValueError("BOOT_CONFIG_GENERATE_ONCE")
        if sum("AIR6_MOUNT_ROOT_CALLED" in line for line in records) > 1:
            raise ValueError("BOOT_DOUBLE_MOUNT_ROOT")
    return {"status": "OFFLINE_TRACE_ORDER_PASS", "mode": mode,
            "observed_stages": list(required), "device_boot_proven": False}


def required_applets(argv_text, required=("sh", "sha256sum", "mount", "switch_root",
                                         "cat", "grep", "awk")):
    """Parse the output of target-built /bin/busybox --list, never the host."""
    found = set(argv_text.splitlines())
    absent = sorted(set(required) - found)
    if absent:
        raise ValueError("TARGET_BUSYBOX_MISSING_APPLETS: " + ",".join(absent))
    return sorted(set(required))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--p26-receipt", type=Path, required=True)
    ap.add_argument("--p25-binding", type=Path, required=True)
    ap.add_argument("--uart-trace", type=Path, required=True)
    ap.add_argument("--target-busybox-list", type=Path, required=True)
    args = ap.parse_args()
    p26_sha = bound_pair(json.loads(args.p26_receipt.read_text()),
                         json.loads(args.p25_binding.read_text()))
    required_applets(args.target_busybox_list.read_text())
    observed = validate_trace(args.uart_trace.read_text().splitlines())
    print(json.dumps({"p26_sha256": p26_sha, **observed}, sort_keys=True))


if __name__ == "__main__":
    main()
