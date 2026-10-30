# SPDX-License-Identifier: MIT
"""Fail-closed source-level checks for the independent Air6 DTS candidate."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DTS = ROOT / "board/mt6990-air-terminal-6.dts"
RUNNER = ROOT / "scripts/verify-air6-board-dtc.sh"


class BoardDtsSourceTests(unittest.TestCase):
    def setUp(self):
        self.src = DTS.read_text()

    def test_distinct_board_identity_and_soc_include(self):
        self.assertIn('"softbank,air-terminal-6", "mediatek,mt6990"', self.src)
        self.assertIn('#include "mt6990.dtsi"', self.src)
        self.assertNotIn("fiberhome,lg6851f", self.src.lower())
        self.assertNotIn('root=/dev/mmcblk', self.src)

    def test_verified_ethernet_topology(self):
        for token in ('&eth {', 'gmac1: mac@1', 'switch@1f', 'reg = <31>;',
                      'port@5', 'ethernet = <&gmac1>;', 'port@1',
                      'phy-mode = "2500base-x"'):
            with self.subTest(token=token):
                self.assertIn(token, self.src)
        self.assertNotIn("reset-gpios", self.src)

    def test_unverified_consumers_fail_closed(self):
        for label in ("eth", "mmc0", "mmc1", "pcie0", "pcie1", "pcie2",
                      "usb", "xsphy", "sgmiisys0", "sgmiisys1"):
            with self.subTest(node=label):
                match = re.search(r"&" + re.escape(label) + r"\s*\{([\s\S]*?)\n\};", self.src)
                self.assertIsNotNone(match)
                self.assertIn('status = "disabled";', match.group(1))

    def test_no_calibration_or_credentials(self):
        self.assertNotRegex(self.src, r"(?i)(BEGIN PRIVATE KEY|ghp_[a-z0-9]+|"
                                      r"mac-address\s*=|local-mac-address\s*=|"
                                      r"wifi-psk|password\s*=|imei\s*=)")
        self.assertNotRegex(self.src, r"(?m)^\s*data\s*=\s*\[")

    def test_linux_binding_headers_have_exact_blob_gates(self):
        # Source-only regression: all three fetched Linux v6.18 binding
        # headers must be checked against reviewed upstream Git blob IDs.
        helper = RUNNER.read_text()
        expected = {
            "interrupt-controller/arm-gic.h": "887f53363e8a633ba85c8a459313c37b71a729a5",
            "interrupt-controller/irq.h": "9e3d183e138191fe5227cb5ffc5ff52d81036b15",
            "gpio/gpio.h": "b5d531237448241f1870e7d8d4cf1a6411877562",
        }
        pinned = dict(re.findall(
            r'"(interrupt-controller/(?:arm-gic|irq)\.h|gpio/gpio\.h):([0-9a-f]{40})"',
            helper,
        ))
        self.assertEqual(pinned, expected)
        self.assertIn('test "$(git hash-object "$output")" = "$expected_blob"', helper)
        self.assertIn("Unexpected pinned Linux binding identity", helper)

    def test_pinned_source_only_check(self):
        helper = RUNNER.read_text()
        self.assertIn("a40df9a5afb46716dea799acea69f17480df4d82", helper)
        self.assertIn("4f24ec8183c5495a312ec5f1109164d7b770a770", helper)
        self.assertIn("c221b322fb437683d052ec4241a33afaecb33979", helper)
        self.assertIn("NO_PYTHON=1 dtc", helper)
        self.assertNotIn("flashcp", helper)
        self.assertNotIn("dd if=", helper)


if __name__ == "__main__":
    unittest.main()
