#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link independently checked unsigned p25/p26 in a private same-run pair receipt.

No signing, flashing, board-specific boot values, or binary publication.
P26 filesystem readback must have been completed by its separate verifier.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError("UNSIGNED_PAIR_BLOCKED_" + reason)


def valid_path(path):
    return (path.is_file() and not path.is_symlink()
            and not any(p.is_symlink() for p in path.parents))


def p25_verifier():
    path = Path(__file__).resolve().parents[1] / "boot/verify_p25_independent.py"
    spec = importlib.util.spec_from_file_location("public_p25_independent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_pair(p25, kernel, ramdisk, dtb, config, p26, producer,
                independent, out, p25_verify=None):
    paths = (p25, kernel, ramdisk, dtb, config, p26, producer, independent)
    require(all(valid_path(p) for p in paths), "INVALID_INPUT")
    require(not out.exists() and not out.is_symlink()
            and out.parent.is_dir()
            and not any(p.is_symlink() for p in out.parents),
            "OUTPUT_EXISTS_OR_SYMLINK")
    # Independently recheck the p25 including all boot-sensitive config bytes.
    check = p25_verify or p25_verifier().verify
    p25_result = check(p25, kernel, ramdisk, dtb, config)
    require(p25_result["partition_bytes"] == 33_554_432 and
            p25_result["p25_sha256"] == digest(p25), "P25_IDENTITY")
    original = json.loads(producer.read_text())
    approved = json.loads(independent.read_text())
    require(original.get("schema") == 1 and
            original.get("status") == "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK"
            and original.get("signed") is False and
            original.get("hardware") == "NONE", "P26_PRODUCER_STATUS")
    require(approved.get("schema") == 1 and
            approved.get("status") == "P26_INDEPENDENT_FS_READBACK_VERIFIED" and
            approved.get("signed") is False and
            approved.get("hardware") == "NONE" and
            approved.get("verification") ==
            "INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA",
            "P26_NOT_INDEPENDENTLY_VERIFIED")
    require(p26.stat().st_size == 134_217_728 and
            original.get("partition_bytes") == 134_217_728 and
            approved.get("partition_bytes") == 134_217_728,
            "P26_SIZE")
    p26_hash = digest(p26)
    require(p26_hash == original.get("p26_sha256") ==
            approved.get("p26_sha256"), "P26_IMAGE_IDENTITY")
    require(approved.get("producer_receipt_sha256") == digest(producer),
            "P26_RECEIPT_IDENTITY")
    require(original.get("squashfs_sha256") ==
            approved.get("squashfs_sha256") and
            original.get("squashfs_bytes") ==
            approved.get("squashfs_bytes"), "P26_SQUASHFS_IDENTITY")
    receipt = {
        "schema": 1, "status": "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED",
        "p25_sha256": p25_result["p25_sha256"],
        "p26_sha256": p26_hash,
        "p26_independent_receipt_sha256": digest(independent),
        "p25_config_sha256": digest(config),
        "signed": False, "device_writes": False, "public_binary": False,
        "not_proven": ["Air6 LK accepts p25", "RC14 boot compatibility",
                       "hardware cold boot", "LAN/SSH", "publication rights"],
    }
    # Do not overwrite stale pair evidence.
    with out.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("p25", "kernel", "ramdisk", "dtb", "config",
                 "p26", "producer", "independent", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    a = parser.parse_args()
    result = verify_pair(a.p25, a.kernel, a.ramdisk, a.dtb, a.config,
                         a.p26, a.producer, a.independent, a.out)
    print("PUBLIC_UNSIGNED_P25_P26_PAIR_BYTE_IDENTITIES_PASS",
          result["p25_sha256"], result["p26_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
