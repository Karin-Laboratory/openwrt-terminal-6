#!/usr/bin/env python3
"""Check a locally obtained DTS text inventory against the public evidence checklist.

Non-invasive source inspection. No OEM DTS is uploaded or copied into the repo.
"""
import argparse
import json
from pathlib import Path
from inventory_sgmii_fdt import inspect

TARGETS = ("sgmiisys@11305000", "sgmiiphy@11E60000")
def assess(dts_text):
    inventory = inspect(dts_text)
    missing = []
    for name in TARGETS:
        item = inventory["targets"].get(name, {})
        if not item.get("present") or item.get("parse_error"):
            missing.append(name + ": missing or malformed")
            continue
        props = item.get("properties", {})
        for prop in ("compatible",):
            if not props.get(prop):
                missing.append(name + ": missing " + prop)
    return {
        "status": "TEXT_INVENTORY_ONLY",
        "target_inventory": inventory["targets"],
        "missing": missing,
        "warnings": [
            "Text inventory does not resolve phandles or validate register mappings",
            "Do not infer power-domains, clocks or PLL providers from another board",
            "No official board DTS or installable image is generated",
        ],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("runtime_dts", type=Path)
    a = p.parse_args()
    print(json.dumps(assess(a.runtime_dts.read_text(encoding="utf-8")), indent=2))

if __name__ == "__main__":
    main()
