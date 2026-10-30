#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative Air6 DTS source scope guard. No hardware, kernel or dtbs_check."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "board/mt6990-air-terminal-6.dts"
TRIAL = ROOT / "board/mt6990-air-terminal-6-ethernet-test.dts"

BASE_DISABLED = frozenset({
    "eth", "sgmiisys0", "sgmiisys1", "mmc0", "mmc1", "pcie0",
    "pcie1", "pcie2", "usb", "xsphy",
})
BASE_ALLOWED = BASE_DISABLED | {"uart0"}
TRIAL_ALLOWED = frozenset({"netsys", "sgmiisys1", "eth", "gmac0", "gmac1"})
TRIAL_ENABLED = frozenset({"netsys", "sgmiisys1", "eth", "gmac1"})


# The &label allowlist does not cover new root-level nodes. Inspect the
# *direct* children of the single / { } block before accepting either variant.
# This is a conservative source guard, not a general DTS grammar parser.
BASE_ROOT_CHILDREN = frozenset({"aliases", "chosen"})
TRIAL_ROOT_CHILDREN = frozenset({"syscon@10014000", "phy@11e60000"})

def root_children(data: str) -> set[str]:
    roots = list(re.finditer(r"/[ \t]*\{", data))
    if len(roots) != 1:
        raise ValueError(f"expected one root block, found {len(roots)}")
    start = roots[0].end()
    depth, pos = 1, start
    while depth and pos < len(data):
        depth += (data[pos] == "{") - (data[pos] == "}")
        pos += 1
    if depth:
        raise ValueError("unclosed root block")
    body = data[start:pos - 1]
    children = []
    depth = 0
    tokens = re.finditer(
        r"(?P<node>(?:[A-Za-z_][\w-]*\s*:\s*)?[A-Za-z_][\w,.\-+@]*)\s*\{|(?P<brace>[{}])",
        body,
    )
    for token in tokens:
        if token.group("node"):
            if depth == 0:
                children.append(token.group("node").split(":")[-1].strip())
            depth += 1
        elif token.group("brace") == "{":
            raise ValueError("unrecognized root child syntax")
        else:
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced root child")
    if depth or len(children) != len(set(children)):
        raise ValueError("unbalanced or duplicate root child")
    return set(children)

def uncomment(data: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", data, flags=re.DOTALL)

def reference_nodes(data: str) -> dict[str, str]:
    """Extract top-level reference blocks with balanced braces, no DT parser claim."""
    nodes: dict[str, str] = {}
    for match in re.finditer(r"&([A-Za-z_][A-Za-z_0-9]*)\s*\{", data):
        name = match.group(1)
        if name in nodes:
            raise ValueError("duplicate reference block: " + name)
        start = match.end()
        pos, depth = start, 1
        while depth and pos < len(data):
            if data[pos] == "{":
                depth += 1
            elif data[pos] == "}":
                depth -= 1
            pos += 1
        if depth:
            raise ValueError("unbalanced node: " + name)
        nodes[name] = data[start:pos-1]
    return nodes

def direct_status(body: str) -> str | None:
    depth = 0
    found: list[str] = []
    for line in body.splitlines():
        if depth == 0:
            match = re.fullmatch(r'\s*status\s*=\s*"(okay|disabled)";\s*', line)
            if match:
                found.append(match.group(1))
        depth += line.count("{") - line.count("}")
    if len(found) != 1:
        raise ValueError("missing or repeated direct status")
    return found[0]

def validate(base: str, trial: str) -> list[str]:
    errors = []
    clean_base, clean_trial = uncomment(base), uncomment(trial)
    for name, source in (("base", clean_base), ("trial", clean_trial)):
        # DTS supports &{/absolute/path} overrides, not only &label blocks.
        # A path override can enable a disabled controller without touching
        # its guarded label declaration; reject all until separately reviewed.
        if re.search(r"&\s*\{\s*/", source):
            errors.append(name + ": path-based reference override is unreviewed")

        if re.search(r"\bbootargs\s*=|/incbin/\s*\(|\bmemory(?:@[0-9a-fA-F]+)?\s*\{", source):
            errors.append(name + ": unreviewed bootargs, memory or binary embedding")
        if re.search(r"(?i)\b(?:mac-address|local-mac-address|password|imei)\s*=", source):
            errors.append(name + ": per-device or credential property")
    for name, source, allowed in (
        ("base", clean_base, BASE_ROOT_CHILDREN),
        ("trial", clean_trial, TRIAL_ROOT_CHILDREN),
    ):
        try:
            actual = root_children(source)
            if actual != allowed:
                errors.append(name + ": unreviewed root children " +
                              repr(sorted(actual ^ allowed)))
        except ValueError as exc:
            errors.append(name + ": " + str(exc))
    if '#include "mt6990.dtsi"' not in clean_base:
        errors.append("base: missing pinned SoC include")
    if '#include "mt6990-air-terminal-6.dts"' not in clean_trial:
        errors.append("trial: must derive from conservative base")
    try:
        base_nodes = reference_nodes(clean_base)
        trial_nodes = reference_nodes(clean_trial)
        if set(base_nodes) != BASE_ALLOWED:
            errors.append("base: unexpected or missing references " + repr(sorted(set(base_nodes) ^ BASE_ALLOWED)))
        if set(trial_nodes) != TRIAL_ALLOWED:
            errors.append("trial: unexpected or missing references " + repr(sorted(set(trial_nodes) ^ TRIAL_ALLOWED)))
        for name in sorted(BASE_DISABLED):
            if name in base_nodes and direct_status(base_nodes[name]) != "disabled":
                errors.append("base: unexpectedly enabled " + name)
        if "uart0" in base_nodes and direct_status(base_nodes["uart0"]) != "okay":
            errors.append("base: UART status changed")
        for name in sorted(TRIAL_ALLOWED):
            if name in trial_nodes:
                status = direct_status(trial_nodes[name])
                expected = "okay" if name in TRIAL_ENABLED else "disabled"
                if status != expected:
                    errors.append("trial: incorrect scope/status " + name)
    except ValueError as exc:
        errors.append(str(exc))
    return errors

def main() -> int:
    try:
        errors = validate(BASE.read_text(), TRIAL.read_text())
    except OSError as exc:
        print("AIR6_DTS_SCOPE_FAIL:", str(exc))
        return 2
    for error in errors:
        print("AIR6_DTS_SCOPE_FAIL:", error)
    if errors:
        return 1
    print("AIR6_DTS_SCOPE_PASS (source guard only; no dtbs_check, driver or boot proof)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
