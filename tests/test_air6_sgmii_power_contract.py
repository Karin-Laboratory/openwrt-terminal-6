#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source-only regression for the Air6 SGMII1 power/PHY wiring.

This checks the opt-in DTS, not a compiled DTB or hardware behavior.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DTS = ROOT / "board/mt6990-air-terminal-6-ethernet-test.dts"


def strip_comments(source):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)


def node_body(source, opener):
    match = re.search(re.escape(opener) + r"\s*\{", source)
    if not match:
        raise ValueError("missing DTS node: " + opener)
    depth = 1
    start = match.end()
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos]
    raise ValueError("unterminated DTS node: " + opener)


def check_sgmii_power_contract(source):
    source = strip_comments(source)
    phy = node_body(source, "air6_sgmii_phy1: phy@11e60000")
    pcs = node_body(source, "&sgmiisys1")
    netsys = node_body(source, "&netsys")
    requirements = (
        (phy, r"power-domains\s*=\s*<&scpsys\s+MT6990_POWER_DOMAIN_SGMII_TOP_1\s*>", "PHY TOP1 genpd"),
        (phy, r"mediatek,sgmii-pll\s*=\s*<&air6_sgmii_pll\s*>", "PHY shared PLL"),
        (phy, r"mediatek,spm\s*=\s*<&scpsys\s*>", "PHY SPM"),
        (pcs, r"phys\s*=\s*<&air6_sgmii_phy1\s*>", "PCS1 PHY"),
        (pcs, r'phy-names\s*=\s*"sgmii"', "PCS1 PHY name"),
        (netsys, r'compatible\s*=\s*"mediatek,mt6990-netsys"\s*,\s*"simple-bus"', "NETSYS bus"),
        (netsys, r"/delete-node/\s+sgmii-pwr0\s*;", "obsolete power helper 0"),
        (netsys, r"/delete-node/\s+sgmii-pwr1\s*;", "obsolete power helper 1"),
    )
    for body, pattern, label in requirements:
        if not re.search(pattern, body):
            raise ValueError("missing or changed " + label)


class SgmiiPowerContractTest(unittest.TestCase):
    def test_candidate_dts(self):
        check_sgmii_power_contract(DTS.read_text())

    def test_missing_power_domain_fails(self):
        source = DTS.read_text().replace("MT6990_POWER_DOMAIN_SGMII_TOP_1", "MT6990_POWER_DOMAIN_SGMII_TOP_0")
        with self.assertRaisesRegex(ValueError, "TOP1"):
            check_sgmii_power_contract(source)

    def test_missing_pcs_phy_fails(self):
        source = DTS.read_text().replace("phys = <&air6_sgmii_phy1>;", "phys = <&air6_sgmii_phy0>;")
        with self.assertRaisesRegex(ValueError, "PCS1 PHY"):
            check_sgmii_power_contract(source)

    def test_old_power_helper_reenabled_fails(self):
        source = DTS.read_text().replace("/delete-node/ sgmii-pwr1;", "")
        with self.assertRaisesRegex(ValueError, "obsolete power helper 1"):
            check_sgmii_power_contract(source)


if __name__ == "__main__":
    unittest.main()
