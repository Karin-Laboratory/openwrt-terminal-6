#!/usr/bin/env python3
"""Compare independent public unsigned P25/P26 build receipts, without firmware bytes.

Origin: independently authored for this repository; SPDX-License-Identifier: MIT.
This is a metadata gate, not proof of matching underlying image bytes.
"""
import argparse
import json
from pathlib import Path

FIELDS = (
    "p25_sha256", "p26_sha256", "bound_initramfs_sha256",
    "kernel_image_sha256", "initramfs_object_sha256", "p25_config_sha256",
)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    obj = json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonstandard JSON constant: " + value)),
    )
    if not isinstance(obj, dict):
        raise ValueError("receipt must be an object")
    for field in FIELDS:
        value = obj.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(
            ch not in "0123456789abcdef" for ch in value
        ):
            raise ValueError("missing or malformed SHA-256: " + field)
    return obj


def compare(a, b):
    return [field for field in FIELDS if a[field] != b[field]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_a")
    parser.add_argument("workspace_b")
    args = parser.parse_args()
    try:
        if Path(args.workspace_a).samefile(args.workspace_b):
            raise ValueError("workspace A and B must be different receipt files")
        a, b = load(args.workspace_a), load(args.workspace_b)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, "REPRO_RECEIPT_INVALID: " + str(exc) + "\n")
    differences = compare(a, b)
    for field in FIELDS:
        print("REPRO_" + field.upper() + "=" + ("DIFF" if field in differences else "MATCH"))
    if differences:
        print("REPRO_RECEIPT_MISMATCH: " + ",".join(differences))
        return 1
    print("REPRO_RECEIPT_HASHES_MATCH; independent byte verification remains required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
