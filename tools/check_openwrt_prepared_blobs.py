#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the pinned OpenWrt 6.18.55 prepared MediaTek source snapshot."""
import argparse
import hashlib
from pathlib import Path
import sys


FILES = {
    "drivers/net/ethernet/mediatek/mtk_eth_soc.c":
        "680f8adf2c7402a8b041966703358e3532b347de",
    "drivers/net/ethernet/mediatek/mtk_eth_soc.h":
        "accf4849979e4bf57ebefa9eb5199656fbee71b7",
}


def git_blob_id(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def inspect(root: Path) -> dict:
    results = {}
    for relative, expected in FILES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            results[relative] = {"state": "missing", "expected_git_blob": expected}
            continue
        actual = git_blob_id(path.read_bytes())
        results[relative] = {
            "state": "exact" if actual == expected else "different",
            "git_blob": actual,
            "expected_git_blob": expected,
        }
    return {
        "schema": "openwrt-prepared-mediatek-source-v1",
        "openwrt_commit": "a25fb079b1463cd5d7d69c6d9a1c28d873291ebb",
        "kernel": "6.18.55",
        "eligible_for_rebased_rfc_series": all(v["state"] == "exact" for v in results.values()),
        "files": results,
        "note": "Fingerprint match identifies this prepared source snapshot only; it is not a runtime safety claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("--require-exact", action="store_true")
    args = parser.parse_args()
    result = inspect(args.tree)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_exact and not result["eligible_for_rebased_rfc_series"]:
        print("NO-GO: source does not match the pinned OpenWrt prepared tree", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
