# SPDX-License-Identifier: MIT
"""Offline regression: pinned donor fetch must never build or deploy."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fetch-pinned-openwrt-donor.sh"


class DonorSourceOnlyTests(unittest.TestCase):
    def test_pinned_public_repository_and_revision(self):
        text = SCRIPT.read_text()
        self.assertIn("github.com/13179415360/openwrt-mt6990-lg6851f.git", text)
        self.assertIn("a40df9a5afb46716dea799acea69f17480df4d82", text)
        self.assertIn('rev-parse HEAD', text)
        self.assertIn('--detach "$DONOR_REV"', text)

    def test_no_firmware_or_automatic_build(self):
        content = SCRIPT.read_text()
        for forbidden in (
            "sysupgrade", "fastboot", "dd if=", "mkimage", "sign-image",
            "make -C", "make -j", "sudo ", "ssh root@", "scp ", "flashrom",
        ):
            self.assertNotIn(forbidden, content)

    def test_no_root_or_overwrite(self):
        content = SCRIPT.read_text()
        self.assertIn("if [[ $EUID -eq 0 ]]", content)
        self.assertIn("-e \"$DEST\"", content)
        self.assertIn("git clone --no-checkout", content)


if __name__ == "__main__":
    unittest.main()
