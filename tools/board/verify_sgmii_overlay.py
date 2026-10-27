#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Static, no-device checks for an intentionally disabled research DT overlay.

Not dtc, dtbs_check or a validation of SoC binding/provider correctness.
"""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TARGETS = ("/sgmiiphy@11E60000", "/sgmiisys@11305000")


def inspect(content: str) -> list[str]:
    issues = []
    targets = re.findall(r'target-path\s*=\s*"([^"]+)"\s*;', content)
    statuses = re.findall(r'status\s*=\s*"([^"]+)"\s*;', content)
    if sorted(targets) != sorted(EXPECTED_TARGETS):
        issues.append("not the two expected SGMII1 paths")
    if len(statuses) != 2 or any(value != "disabled" for value in statuses):
        issues.append("both experimental fragments must remain disabled")
    if not content.startswith("// SPDX-License-Identifier: GPL-2.0-only"):
        issues.append("kernel-origin GPL notice missing")
    if not all(token in content for token in (
        "sbat6_phy1:", "phys = <&sbat6_phy1>;", '#phy-cells = <0>;'
    )):
        issues.append("PHY consumer skeleton incomplete")
    for text in ("firmware-name", "nvmem-cells", "local-mac-address",
                 "chosen", "bootargs", "status = \"okay\"", "status = \"ok\""):
        if text in content:
            issues.append("forbidden runtime or device-specific payload/property")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=ROOT / "board/mt6990-air-terminal-6-sgmii1-experimental.dtso")
    args = parser.parse_args()
    if args.source.is_symlink() or not args.source.is_file():
        print("SGMII OVERLAY FAIL: missing or symlink")
        return 2
    try:
        data = args.source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return 2
    problems = inspect(data)
    for x in problems:
        print("SGMII OVERLAY BLOCKED:", x)
    print("SGMII OVERLAY", "PASS" if not problems else "FAIL",
          "(static disabled-only review; NOT a deployable DTS)")
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main())
