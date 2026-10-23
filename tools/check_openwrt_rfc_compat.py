#!/usr/bin/env python3
"""Fail-closed compatibility manifest for staging public Ethernet RFCs in OpenWrt.

This does NOT package, build, sign or flash firmware.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FILES = {
    "drivers/net/ethernet/mediatek/mtk_eth_soc.c":
        "e68997a29191b2a8ce0868873dcfe95c79e10e56",
    "drivers/net/ethernet/mediatek/mtk_eth_soc.h":
        "0168e2fbc6197a6aa9fe159767166e86915accbc",
}

def check(tree):
    matches = {}
    for name, expected in FILES.items():
        source = tree / name
        if not source.is_file() or source.is_symlink():
            matches[name] = {"state": "missing", "expected_git_blob": expected}
            continue
        data = source.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()
        matches[name] = {
            "state": "exact" if blob == expected else "different",
            "git_blob": blob,
            "expected_git_blob": expected,
        }
    ready = all(v["state"] == "exact" for v in matches.values())
    return {
        "schema": "openwrt-rfc-compat-v1",
        "patch_target": "Linux v6.18 MediaTek Ethernet source blobs",
        "rfc1_rfc2_direct_apply_eligible": ready,
        "kernel_tree_files": matches,
        "note": "Exact blob match alone does not prove OpenWrt target integration or runtime safety",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("linux_kernel_tree", type=Path)
    parser.add_argument("--require-exact", action="store_true")
    args = parser.parse_args()
    result = check(args.linux_kernel_tree)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_exact and not result["rfc1_rfc2_direct_apply_eligible"]:
        print("NO-GO: rebase and rerun compile tests on the selected OpenWrt kernel", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
