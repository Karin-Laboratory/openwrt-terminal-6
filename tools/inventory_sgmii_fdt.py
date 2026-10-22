#!/usr/bin/env python3
"""Fail-closed inspection of a locally provided, decompiled runtime FDT.

It reports existing hexadecimal phandle references and properties. It does not
rewrite DTS, transplant vendor data, invoke signing tools or contact hardware.
"""
import argparse
import json
import re
from pathlib import Path

TARGETS = ("sgmiisys@11305000", "sgmiiphy@11E60000")
PROPS = ("compatible", "phandle", "linux,phandle", "phys", "phy-names",
         "mediatek,sgmii-id", "mediatek,sgmii-pll", "mediatek,spm",
         "power-domains", "power-domain-names", "clocks", "clock-names")

def inspect(text):
    results = {}
    for target in TARGETS:
        hit = re.search(r"(?m)^\s*" + re.escape(target) + r"\s*\{", text)
        if not hit:
            results[target] = {"present": False}
            continue
        start, index, level = hit.end(), hit.end(), 1
        while index < len(text) and level:
            level += (text[index] == "{") - (text[index] == "}")
            index += 1
        if level:
            results[target] = {"present": True, "parse_error": "unbalanced braces"}
            continue
        block = text[start:index-1]
        found = {}
        for name in PROPS:
            matched = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*([^;]+);", block)
            found[name] = matched.group(1).strip() if matched else None
        results[target] = {"present": True, "properties": found}
    return {"scope": "read-only property inventory; not phandle verification", "targets": results}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fdt_text", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.fdt_text.read_text(encoding="utf-8")),
                     indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
