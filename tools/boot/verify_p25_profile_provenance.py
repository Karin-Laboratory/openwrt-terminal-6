#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a candidate boot-v2 input profile with owner-audited P25 evidence.

This is a byte/field consistency gate. It cannot certify LK behavior, board
memory placement, OEM intellectual property rights or firmware distribution.
Private inputs and observed OEM prefix bytes are never printed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

HEADERS = (
    ("kernel_addr", "kernel_addr"),
    ("ramdisk_addr", "ramdisk_addr"),
    ("second_addr", "second_addr"),
    ("tags_addr", "tags_addr"),
    ("dtb_addr", "dtb_addr"),
    ("page_size", "page_size"),
    ("os_version", "os_version"),
    ("name", "name"),
    ("cmdline", "cmdline"),
)


def reject(ok, reason):
    if not ok:
        raise ValueError("P25_PROFILE_BLOCKED_" + reason)


def regular(path):
    return path.is_file() and not path.is_symlink() and not any(
        x.is_symlink() for x in path.parents)


def verify(config, prefix, audit_receipt, public_dtb):
    for path in (config, prefix, audit_receipt, public_dtb):
        reject(regular(path), "PRIVATE_INPUT_NONREGULAR")
    cfg = json.loads(config.read_text())
    audit = json.loads(audit_receipt.read_text())
    reject(audit.get("schema") == 1 and
           audit.get("status") == "PRIVATE_REFERENCE_LAYOUT_VERIFIED_NOT_LICENSED" and
           audit.get("binary_or_prefix_bytes_exported") is False and
           audit.get("public_manufacture_configuration_approved") is False,
           "REFERENCE_AUDIT_STATUS")
    old = audit["android_header"]
    for name, field in HEADERS:
        value = cfg[name]
        if name.endswith("_addr"):
            try:
                value = int(value, 0)
                observed = int(old[field], 0)
            except (TypeError, ValueError) as exc:
                raise ValueError("P25_PROFILE_BLOCKED_ADDRESS_PARSE") from exc
        else:
            observed = old[field]
        reject(value == observed, "FIELD_MISMATCH_" + name.upper())
    reject(cfg["ramdisk_mode"] == "kernel_embedded" and
           old["ramdisk_size"] == 0, "RAMDISK_POLICY")
    reference_prefix = audit["reference_prefix"]
    reject(reference_prefix["bytes"] == 64 and
           reference_prefix["rights"] == "UNVERIFIED" and
           reference_prefix["lk_semantics"] == "UNVERIFIED",
           "REFERENCE_PREFIX_SCOPE")
    reject(cfg["dtb_prefix_bytes"] == 64 and
           prefix.stat().st_size == 64, "PREFIX_SIZE")
    phash = hashlib.sha256(prefix.read_bytes()).hexdigest()
    reject(phash == reference_prefix["sha256"] ==
           cfg["dtb_prefix_sha256"], "PREFIX_NOT_IDENTICAL_TO_REFERENCE")
    bare = public_dtb.read_bytes()
    reject(len(bare) >= 40 and bare[:4] == bytes.fromhex("d00dfeed"),
           "PUBLIC_DTB_MAGIC")
    reject(struct.unpack_from(">I", bare, 4)[0] == len(bare),
           "PUBLIC_DTB_TOTALSIZE")
    return {
        "schema": 1,
        "status": "REFERENCE_PROFILE_FIELDS_AND_PREFIX_MATCH_NOT_BOOT_OR_RIGHTS",
        "reference_p25_sha256": audit["reference_p25_sha256"],
        "candidate_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "candidate_prefix_sha256": phash,
        "candidate_dtb_sha256": hashlib.sha256(bare).hexdigest(),
        "candidate_differs_from_reference_bare_dtb":
            hashlib.sha256(bare).hexdigest() != audit["bare_dtb_sha256"],
        "prefix_bytes_in_report": False,
        "hardware_boot_approved": False,
        "redistribution_approved": False,
        "third_party_rights": "UNVERIFIED",
        "no_signing_or_device_writes": True,
        "not_proven": [
            "LK accepts newer kernel/DTB and load addresses",
            "OEM prefix semantics or independent origin",
            "right to redistribute prefix or derived image",
            "actual slot A cold boot",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "prefix", "audit_receipt", "public_dtb"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    a = p.parse_args()
    verify(a.config, a.prefix, a.audit_receipt, a.public_dtb)
    print("P25_REFERENCE_PROFILE_CONSISTENCY_PASS_NOT_BOOT_OR_RIGHTS")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
