#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline P25/P26 pair integrity gate before any separate owner signing review.

This tool never signs, flashes, reads device keys or declares LK compatibility.
"""
import argparse
import hashlib
import json
from pathlib import Path

P25_SIZE = 33_554_432
P26_SIZE = 134_217_728
DIGITS = set("0123456789abcdef")


def fail(reason):
    raise ValueError("PAIR_BLOCKED_" + reason)


def regular(path):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        fail("SYMLINK_PATH")
    if not path.is_file():
        fail("MISSING_FILE")
    return path


def digest(path):
    h = hashlib.sha256()
    with regular(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_sha(value):
    return type(value) is str and len(value) == 64 and set(value) <= DIGITS


def check(p25, p25_receipt, p26, p26_receipt):
    p25, p26 = regular(p25), regular(p26)
    a = json.loads(regular(p25_receipt).read_text(encoding="utf-8"))
    b = json.loads(regular(p26_receipt).read_text(encoding="utf-8"))
    if (a.get("format") != "aosp-boot-v2-p25-research-receipt-v1"
            or b.get("schema") != 1):
        fail("RECEIPT_SCHEMA")
    if (a.get("partition_bytes") != P25_SIZE or p25.stat().st_size != P25_SIZE
            or b.get("partition_bytes") != P26_SIZE or p26.stat().st_size != P26_SIZE):
        fail("PARTITION_LENGTH")
    for record, name, image in ((a, "p25_sha256", p25), (b, "p26_sha256", p26)):
        if not valid_sha(record.get(name)) or digest(image) != record[name]:
            fail("FULL_PARTITION_SHA256_" + name.upper())
    if (a.get("status") != "REAL_32M_BYTES_AOSP_V2_STRUCTURE_ONLY_NOT_LK_ACCEPTED"
            or b.get("status") != "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK"):
        fail("UNEXPECTED_RECEIPT_STATUS")
    if any(a.get(k) is not False for k in
           ("signed", "distributable", "device_boot_proven", "lk_header_and_vendor64_accepted")):
        fail("MISLEADING_P25_ATTESTATION")
    if b.get("signed") is not False or b.get("hardware") != "NONE" or b.get("public_binary") is not False:
        fail("MISLEADING_P26_ATTESTATION")
    # Source-root metadata can be reviewed separately. Neither public provenance
    # nor nonzero addresses demonstrate the OEM LK's kernel/DTB expectations.
    fields = a.get("header_fields")
    if not isinstance(fields, dict):
        fail("MISSING_P25_HEADER_FIELDS")
    provenance = a.get("metadata_provenance")
    addresses = (fields.get("kernel_addr"), fields.get("tags_addr"), fields.get("dtb_addr"))
    if (provenance != "owner-reviewed-public-metadata"
            or any(type(x) is not int or x == 0 for x in addresses)):
        gate = "BLOCKED_SYNTHETIC_OR_UNREVIEWED_P25_METADATA"
    else:
        gate = "BLOCKED_LK_VENDOR64_AND_HARDWARE_ACCEPTANCE_UNPROVEN"
    return {
        "schema": "air6-p25-p26-presign-intake-v1",
        "p25_sha256": a["p25_sha256"],
        "p26_sha256": b["p26_sha256"],
        "p25_bytes": P25_SIZE,
        "p26_bytes": P26_SIZE,
        "pair_integrity": "PASS_RECEIPT_HASHES_ONLY",
        "signing_readiness": gate,
        "hardware_boot_proven": False,
        "signed": False,
        "safe_to_flash": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("p25", "p25-receipt", "p26", "p26-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = check(args.p25, args.p25_receipt, args.p26, args.p26_receipt)
    print(json.dumps(result, sort_keys=True))
    # A research pair is never presented as signer-ready by this tool.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
