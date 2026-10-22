#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect a caller-provided text DTS for SGMII dependencies, without modification.

This is a lexical triage tool, not a full Device Tree parser or binding validator.
"""
import argparse
import json
import re
from pathlib import Path

NODES = ("/sgmiisys@11305000", "/sgmiiphy@11E60000")
REQUIRED = {
    NODES[0]: ("compatible", "phys", "phy-names"),
    NODES[1]: ("compatible", "#phy-cells", "mediatek,sgmii-pll", "mediatek,spm", "power-domains"),
}

def extract_node(text, name):
    # Only absolute root-level nodes; no source rewrite or overlay application.
    unit = name.lstrip("/")
    pattern = re.compile(r"(?m)^\s*(?:/)?(?:[a-zA-Z_][\w]*\s*:\s*)?" + re.escape(unit) + r"\s*\{")
    match = pattern.search(text)
    if not match:
        return None
    start = match.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start:i-1] if depth == 0 else None

def audit(text):
    output = {}
    for node in NODES:
        body = extract_node(text, node)
        if body is None:
            output[node] = {"present": False, "missing": list(REQUIRED[node])}
            continue
        properties = set(re.findall(r"(?m)^\s*([#a-zA-Z0-9,._+\-]+)\s*(?:=|;)", body))
        output[node] = {"present": True,
                        "missing": [x for x in REQUIRED[node] if x not in properties],
                        "status": (re.search(r'\bstatus\s*=\s*"([^"]+)"', body) or [None, "implicit"])[1]}
    return {"mode": "READ_ONLY_TEXT_TRIAGE", "nodes": output,
            "warning": "Lexical checks do not resolve phandles, power-domain IDs, register ownership or bindings."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dts", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.dts.read_text(encoding="utf-8")), indent=2))

if __name__ == "__main__":
    main()
