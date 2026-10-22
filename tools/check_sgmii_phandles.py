#!/usr/bin/env python3
"""Validate SGMII provider links in a local, decompiled DTS (read-only)."""
import argparse
import json
import re
from pathlib import Path

def block(text, node):
    match = re.search(r"(?m)^\s*(?:[a-zA-Z_][\w]*\s*:\s*)?" + re.escape(node) + r"\s*\{", text)
    if not match:
        return None
    i, start, depth = match.end(), match.end(), 1
    while i < len(text) and depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[start:i-1] if depth == 0 else None

def check(text):
    a = block(text, "sgmiisys@11305000")
    p = block(text, "sgmiiphy@11E60000")
    errors = []
    if a is None or p is None:
        return ["SGMIISYS1 or PHY1 node missing"]
    if not re.search(r"\bphys\s*=\s*<\s*&([a-zA-Z_][\w]*)\s*>\s*;", a):
        errors.append("SGMIISYS1 has no single label-based phys reference")
    else:
        label = re.search(r"\bphys\s*=\s*<\s*&([a-zA-Z_][\w]*)\s*>\s*;", a).group(1)
        if not re.search(r"(?m)\b" + re.escape(label) + r"\s*:\s*sgmiiphy@11E60000\s*\{", text):
            errors.append("phys label does not resolve to PHY1")
    if not re.search(r'\bphy-names\s*=\s*"sgmii"\s*;', a):
        errors.append("SGMIISYS1 lacks phy-names=sgmii")
    for prop in ("mediatek,sgmii-pll", "mediatek,spm", "power-domains"):
        if not re.search(r"(?m)^\s*" + re.escape(prop) + r"\s*=", p):
            errors.append("PHY1 lacks " + prop)
    return errors

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dts", type=Path)
    args = ap.parse_args()
    failures = check(args.dts.read_text())
    print(json.dumps({"passed": not failures, "errors": failures,
                      "scope": "lexical checks; not dtbs_check or hardware verification"}, indent=2))
    raise SystemExit(bool(failures))

if __name__ == "__main__":
    main()
