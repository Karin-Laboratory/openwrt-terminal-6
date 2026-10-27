# SPDX-License-Identifier: MIT
"""Hardware-free checks for the disabled SGMII1 research overlay."""
from pathlib import Path
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sgmii_review", ROOT / "tools/board/verify_sgmii_overlay.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class SGMIIOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / "board/mt6990-air-terminal-6-sgmii1-experimental.dtso").read_text()

    def test_evidence_only_overlay(self):
        self.assertEqual(gate.inspect(self.overlay), [])

    def test_reject_enabled_phy(self):
        data = self.overlay.replace('status = "disabled";',
                                    'status = "okay";', 1)
        self.assertTrue(gate.inspect(data))

    def test_reject_wrong_target(self):
        data = self.overlay.replace("/sgmiisys@11305000", "/bad-sys@0")
        self.assertTrue(gate.inspect(data))

    def test_reject_per_device_properties(self):
        data = self.overlay.replace(
            'phys = <&sbat6_phy1>;',
            'phys = <&sbat6_phy1>;\nlocal-mac-address = [00 00 00 00 00 00];')
        self.assertTrue(gate.inspect(data))

    def test_board_metadata_does_not_claim_nr(self):
        data = json.loads((ROOT / "board/air-terminal-6.json").read_text())
        self.assertEqual(data["board_dts"], "NOT_YET_AVAILABLE")
        self.assertEqual(data["modem"]["nr"], "NOT_VERIFIED")
        self.assertEqual(data["modem"]["ipv6"], "NOT_VERIFIED")
        self.assertEqual(data["ethernet"]["serdes"], "SGMII1")


if __name__ == "__main__":
    unittest.main()
