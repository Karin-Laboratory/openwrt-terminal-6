# SPDX-License-Identifier: MIT
"""Source-only safety contract for pinned host-dtc build and disabled overlay."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-disabled-sgmii-dtc.sh"


class PinnedDtcBuildTests(unittest.TestCase):
    def test_pinned_upstream_source_identity(self):
        content = SCRIPT.read_text()
        self.assertIn("--branch v6.18", content)
        self.assertIn("7d0a66e4bb9081d75c82ec4957c50034cb0ea449", content)
        self.assertIn("e68997a29191b2a8ce0868873dcfe95c79e10e56", content)

    def test_disabled_overlay_compiles_in_disposable_dir(self):
        content = SCRIPT.read_text()
        for phrase in (
            "verify_sgmii_overlay.py",
            "scripts_dtc",
            '-@ -I dts -O dtb',
            "status = \"disabled\";",
            "trap 'rm -rf -- \"$temporary\"' EXIT",
        ):
            self.assertIn(phrase, content)

    def test_no_installation_privileged_or_device_actions(self):
        content = SCRIPT.read_text()
        for forbidden in (
            "sysupgrade", "fastboot", "dd if=", "mkimage",
            "sign-image", "sudo ", "ssh root@", "flashrom", "apt install",
            "TARGET_DEVICES +=",
        ):
            self.assertNotIn(forbidden, content)
        self.assertIn("EUID == 0", content)

    def test_does_not_claim_complete_device_tree(self):
        content = SCRIPT.read_text()
        self.assertIn("a valid, bootable SBAT6 board DTS has NOT been established", content)


if __name__ == "__main__":
    unittest.main()
