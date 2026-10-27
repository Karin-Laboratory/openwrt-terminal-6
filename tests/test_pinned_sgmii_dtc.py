# SPDX-License-Identifier: MIT
"""Source-only safety contract for pinned host-dtc build and disabled overlay."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-disabled-sgmii-dtc.sh"


class PinnedDtcBuildTests(unittest.TestCase):
    def test_pinned_standalone_source_identity(self):
        content = SCRIPT.read_text()
        self.assertIn("--branch v1.7.2", content)
        self.assertIn("github.com/dgibson/dtc.git", content)
        self.assertIn("2d10aa2afe35527728db30b35ec491ecb6959e5c", content)
        self.assertIn("NO_PYTHON=1 dtc", content)

    def test_disabled_overlay_compiles_in_disposable_dir(self):
        content = SCRIPT.read_text()
        for phrase in (
            "verify_sgmii_overlay.py",
            "NO_PYTHON=1 dtc",
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

    def test_reject_long_linux_clone_regression(self):
        content = SCRIPT.read_text()
        self.assertNotIn("torvalds/linux.git", content)
        self.assertNotIn("scripts_dtc", content)

    def test_does_not_claim_complete_device_tree(self):
        content = SCRIPT.read_text()
        self.assertIn("a valid, bootable SBAT6 board DTS has NOT been established", content)


if __name__ == "__main__":
    unittest.main()
