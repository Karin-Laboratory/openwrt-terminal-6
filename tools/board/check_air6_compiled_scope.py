#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check resolved DTC round-trips, not just the source-level DTS overrides.

This is a source-only guard, not dtbs_check or proof of hardware readiness.
"""
from pathlib import Path
import re
import sys


def node(text: str, name: str) -> str:
    """Return the unique named node's body, including nested child text."""
    matches = list(re.finditer(r"(?m)^\s*" + re.escape(name) + r"\s*\{", text))
    if len(matches) != 1:
        raise ValueError(f"expected one {name} node, found {len(matches)}")
    match = matches[0]
    depth = 1
    pos = match.end()
    while depth and pos < len(text):
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    if depth:
        raise ValueError(f"unclosed {name} node")
    return text[match.end():pos - 1]


def status(body: str) -> str:
    """Read only the direct status property, never a child's status."""
    depth = 0
    found = []
    for line in body.splitlines():
        if depth == 0:
            match = re.fullmatch(r'\s*status\s*=\s*"(okay|disabled)";\s*', line)
            if match:
                found.append(match.group(1))
        depth += line.count("{") - line.count("}")
        if depth < 0:
            raise ValueError("unbalanced node body")
    if depth or len(found) != 1:
        raise ValueError("missing, duplicated or malformed direct status")
    return found[0]



def direct_cell(body: str, name: str) -> int:
    """Require exactly one direct positive 32-bit cell in canonical DTC text."""
    depth = 0
    values = []
    for line in body.splitlines():
        if depth == 0 and re.match(r"\s*" + re.escape(name) + r"\s*=", line):
            match = re.fullmatch(
                r"\s*" + re.escape(name) + r"\s*=\s*<(0x[0-9a-fA-F]+)>;\s*", line
            )
            if not match:
                raise ValueError(f"malformed {name} cell")
            values.append(int(match.group(1), 16))
        depth += line.count("{") - line.count("}")
        if depth < 0:
            raise ValueError("unbalanced node body")
    if depth or len(values) != 1 or not (0 < values[0] <= 0xFFFFFFFF):
        raise ValueError(f"missing, duplicated or invalid direct {name} cell")
    return values[0]


def validate(base: str, trial: str) -> list[str]:
    errors = []
    for variant, tree, expected in (("base", base, "disabled"),
                                    ("trial", trial, "okay")):
        try:
            eth = node(node(tree, "netsys@15100000"), "ethernet@15100000")
            pcs = node(tree, "syscon@11305000")
            for name, body in (("Ethernet", eth), ("SGMII1 PCS", pcs)):
                actual = status(body)
                if actual != expected:
                    errors.append(f"{variant}: {name} compiled status {actual}, expected {expected}")
            if variant == "trial":
                # Check resolved MAC children, not only their parent:
                # MAC0 is unreviewed, MAC1 is the sole observed CPU5 uplink.
                for mac_name, required in (("mac@0", "disabled"), ("mac@1", "okay")):
                    actual = status(node(eth, mac_name))
                    if actual != required:
                        errors.append(
                            f"trial: {mac_name} compiled status {actual}, expected {required}"
                        )
                # Check the resolved CPU5 -> MAC1 phandle after compilation.
                # Merely finding both node names does not prove their wiring.
                mac1 = node(eth, "mac@1")
                ports = node(node(node(eth, "mdio-bus"), "switch@1f"), "ports")
                cpu5 = node(ports, "port@5")
                if direct_cell(cpu5, "ethernet") != direct_cell(mac1, "phandle"):
                    errors.append("trial: CPU5 ethernet phandle does not reference MAC1")
                if status(node(tree, "phy@11e60000")) != "okay":
                    errors.append("trial: SGMII1 PHY must be enabled")
        except ValueError as exc:
            errors.append(f"{variant}: {exc}")
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_air6_compiled_scope.py base.roundtrip.dts trial.roundtrip.dts", file=sys.stderr)
        return 2
    try:
        paths = [Path(name) for name in sys.argv[1:]]
        if any(path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000
               for path in paths):
            raise ValueError("unsafe round-trip input")
        base, trial = (path.read_text(encoding="utf-8") for path in paths)
        errors = validate(base, trial)
    except (OSError, UnicodeError, ValueError):
        print("AIR6_COMPILED_SCOPE_BLOCKED: invalid input")
        return 2
    for error in errors:
        print("AIR6_COMPILED_SCOPE_BLOCKED:", error)
    if errors:
        return 1
    print("AIR6_COMPILED_SCOPE_PASS (resolved DTB status only; NOT dtbs_check or boot proof)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
