#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate observed QEMU P26/RAM-overlay stage transitions in actual order.

Only verbatim QEMU serial-console evidence is accepted. This never makes
device-specific LK, MMC, P44 or Ethernet/Wi-Fi claims.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

KERNEL_PID1 = "Run /init as init process"
POSITIVE = (
    "AIR6_RAM_INIT_ENTER",
    "AIR6_P26_RO_VERIFIED",
    "AIR6_P26_ROM_MOUNT_PASS",
    "AIR6_P26_RAM_OVERLAY_DEFAULT",
    "AIR6_OVERLAY_MOUNT_PASS",
    "AIR6_SWITCH_ROOT_BEGIN",
    "procd: - early -",
)
NO_P26 = ("AIR6_RAM_INIT_ENTER", "AIR6_BOOT_BLOCKED_P26_NOT_BLOCK")
SHA_REJECT = ("AIR6_RAM_INIT_ENTER", "AIR6_BOOT_BLOCKED_P26_SHA_MISMATCH")
FATAL = ("Kernel panic", "Failed to execute /init",
         "ALTERNATIVE_QEMU_RAM_INIT_FAIL", "QEMU_VIRTIO_POSITIVE_FAIL")


def _exactly_one(lines, marker):
    match = [i for i, row in enumerate(lines) if marker in row]
    if len(match) != 1:
        raise ValueError(f"QEMU_BOOT_MARKER_CARDINALITY:{marker}:{len(match)}")
    return match[0]


def check_trace(output, mode):
    if mode not in ("positive", "missing-p26", "sha-mismatch"):
        raise ValueError("QEMU_BOOT_MODE")
    if not isinstance(output, str) or not output:
        raise ValueError("QEMU_BOOT_LOG_EMPTY")
    lines = output.splitlines()
    if any(fatal in row for fatal in FATAL for row in lines):
        raise ValueError("QEMU_BOOT_PANIC_OR_LAUNCH_FAIL")
    pid = _exactly_one(lines, KERNEL_PID1)
    markers = POSITIVE if mode == "positive" else (
        NO_P26 if mode == "missing-p26" else SHA_REJECT)
    positions = [pid] + [_exactly_one(lines, marker) for marker in markers]
    if positions != sorted(set(positions)):
        raise ValueError("QEMU_BOOT_MARKER_ORDER")
    for row in lines:
        if "AIR6_BOOT_BLOCKED_" in row and row.strip().split("AIR6_BOOT_BLOCKED_", 1)[1]:
            observed = "AIR6_BOOT_BLOCKED_" + row.split("AIR6_BOOT_BLOCKED_", 1)[1].split()[0]
            if mode == "positive" or observed != markers[-1]:
                raise ValueError("QEMU_BOOT_UNEXPECTED_BLOCKER:" + observed)
    if mode != "positive":
        forbidden = ("AIR6_P26_RO_VERIFIED", "AIR6_P26_ROM_MOUNT_PASS",
                     "AIR6_OVERLAY_MOUNT_PASS", "AIR6_SWITCH_ROOT_BEGIN",
                     "procd: - early -")
        if any(marker in row for marker in forbidden for row in lines):
            raise ValueError("QEMU_BOOT_FAILED_CLOSED_BUT_ADVANCED")
    return {"status": "QEMU_OBSERVED_" + mode.upper().replace("-", "_") + "_PASS",
            "mode": mode, "observed_steps": len(positions),
            "serial_log_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "guest_procd_after_switch_root": mode == "positive",
            "air6_hardware_boot_proven": False,
            "p44_persistence_proven": False}


def verify_actual_p26(path, receipt):
    image, rec = Path(path), Path(receipt)
    if (not image.is_file() or image.is_symlink() or
        not rec.is_file() or rec.is_symlink() or
        image.stat().st_size != 134217728):
        raise ValueError("QEMU_P26_MEDIA_IDENTITY")
    record = json.loads(rec.read_text())
    with image.open("rb") as stream:
        observed = hashlib.file_digest(stream, "sha256").hexdigest()
    if record.get("partition_bytes") != 134217728 or record.get("p26_sha256") != observed:
        raise ValueError("QEMU_P26_SHA_IDENTITY")
    return observed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("positive", "missing-p26", "sha-mismatch"), required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--p26", type=Path)
    ap.add_argument("--p26-receipt", type=Path)
    args = ap.parse_args()
    if (args.p26 is None) != (args.p26_receipt is None):
        ap.error("--p26 and --p26-receipt must be supplied together")
    if args.mode == "positive" and args.p26 is None:
        ap.error("positive mode requires exact same-run p26 and receipt")
    p26_digest = verify_actual_p26(args.p26, args.p26_receipt) if args.p26 else None
    result = check_trace(args.log.read_text(), args.mode)
    if p26_digest:
        result["p26_sha256"] = p26_digest
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
