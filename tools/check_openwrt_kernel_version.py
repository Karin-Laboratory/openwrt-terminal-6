#!/usr/bin/env python3
"""Report OpenWrt source kernel version without invoking make or building firmware."""
import argparse
import json
from pathlib import Path
import re

def inspect(text):
    found = {}
    for key in ("LINUX_VERSION", "LINUX_VERSION-6.18", "LINUX_VERSION-6.12", "LINUX_VERSION-6.6"):
        match = re.search(r"(?m)^" + re.escape(key) + r"\s*[:?+]?=\s*([^#\n]+)", text)
        if match:
            found[key] = match.group(1).strip()
    direct = found.get("LINUX_VERSION", "")
    exact_upstream = direct == "6.18"
    return {
        "status": "version-inventory-only",
        "linux_versions": found,
        "public_rfc_target": "Linux v6.18 C/header exact blobs",
        "can_claim_direct_rfc_compatibility": False,
        "requires_exact_blob_match": True,
        "note": "Kernel version is insufficient; run check_openwrt_rfc_compat.py on the prepared kernel tree.",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("openwrt_kernel_version_mk", type=Path)
    args = p.parse_args()
    print(json.dumps(inspect(args.openwrt_kernel_version_mk.read_text()), indent=2))

if __name__ == "__main__":
    main()
