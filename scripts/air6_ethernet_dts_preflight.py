#!/usr/bin/env python3
"""Fail-closed source preflight for Air6 opt-in NETSYS/SGMII1 Ethernet DTS.

This checks source wiring, not driver probe, a compiled DTB or real Ethernet.
"""
from pathlib import Path
import re
import sys

def block(source, label):
    match = re.search(r"(?m)^&" + re.escape(label) + r"\s*\{", source)
    if not match:
        raise ValueError("missing DTS block: " + label)
    start = match.end()
    depth = 1
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i]
    raise ValueError("unclosed DTS block: " + label)

def validate(source):
    errors = []
    for name in ("netsys", "eth", "sgmiisys1", "gmac0", "gmac1"):
        try:
            section = block(source, name)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected = "disabled" if name == "gmac0" else "okay"
        if not re.search(r'\bstatus\s*=\s*"' + expected + r'"\s*;', section):
            errors.append(name + ": wrong status")
        if name == "netsys":
            for required in ('"simple-bus"', '#address-cells = <2>;', '#size-cells = <2>;', 'ranges;'):
                if required not in section:
                    errors.append("netsys missing " + required)
        if name == "eth":
            clocks = re.search(r'\bclocks\s*=\s*(.*?);', section, re.S)
            names = re.search(r'\bclock-names\s*=\s*(.*?);', section, re.S)
            if not clocks or not names or len(re.findall(r'<&topckgen\b', clocks.group(1))) != len(re.findall(r'"[^"]+"', names.group(1))):
                errors.append("eth clock/name count mismatch")
            irqs = re.search(r'\binterrupts-extended\s*=\s*(.*?);', section, re.S)
            if not irqs or len(re.findall(r'<&(?:gic|pio)\b', irqs.group(1))) != 8:
                errors.append("eth requires 8 IRQ specifiers")
    return errors

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "board/mt6990-air-terminal-6-ethernet-test.dts"
    errors = validate(path.read_text(encoding="utf-8"))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    print("AIR6_ETHERNET_DTS_SOURCE_PREFLIGHT_PASS (source only)")
