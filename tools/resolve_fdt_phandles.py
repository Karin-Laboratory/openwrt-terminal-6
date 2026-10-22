#!/usr/bin/env python3
"""Resolve numeric phandle definitions in a locally supplied decompiled DTS.

Read-only, fail-closed diagnostic. Not a complete DTS parser or binding check.
"""
import argparse
import json
import re
from pathlib import Path

TARGETS = ("0x6d", "0x6e", "0x24")
NODE = re.compile(r"(?m)^\s*(?:[\w-]+:\s*)?([\w,@.\-]+)\s*\{")
HANDLE = re.compile(r"(?m)^\s*(?:linux,)?phandle\s*=\s*<\s*(0x[\da-fA-F]+|\d+)\s*>\s*;")

def resolve(source, target_handles=TARGETS):
    stack, definitions = [], {}
    # Track balanced braces line by line and only match properties inside nodes.
    for line_number, line in enumerate(source.splitlines(), 1):
        node = NODE.match(line)
        if node:
            stack.append(node.group(1))
        found = HANDLE.match(line)
        if found and stack:
            value = int(found.group(1), 0)
            entry = {"node": "/" + "/".join(stack), "line": line_number}
            seen = definitions.setdefault(value, [])
            # phandle and linux,phandle aliases on the SAME node are not duplicates.
            if not any(item["node"] == entry["node"] for item in seen):
                seen.append(entry)
        closes = line.count("}")
        for _ in range(closes):
            if stack:
                stack.pop()
    result = {}
    for handle in target_handles:
        value = int(handle, 0)
        matches = definitions.get(value, [])
        result[handle] = {"matches": matches, "status": ("missing" if not matches else
                           "duplicate" if len(matches) > 1 else "resolved")}
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dts", type=Path)
    args = parser.parse_args()
    report = resolve(args.dts.read_text(encoding="utf-8", errors="replace"))
    print(json.dumps(report, indent=2))
    return 0 if all(v["status"] == "resolved" for v in report.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
