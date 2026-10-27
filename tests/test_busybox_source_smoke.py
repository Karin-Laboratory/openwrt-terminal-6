# SPDX-License-Identifier: MIT
"""Static security contract for a source-only, non-installable ARM64 userland smoke."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-arm64-busybox-smoke.sh"


class BusyBoxSourceSmokeTests(unittest.TestCase):
    def test_upstream_commit_and_makefile_are_pinned(self):
        src = SCRIPT.read_text()
        self.assertIn("mirror/busybox.git", src)
        self.assertIn("1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4", src)
        self.assertIn("fa8cb761443388730372eaf260e7ca1a0235bc43", src)
        self.assertIn("ARCH=arm64 CROSS_COMPILE", src)

    def test_no_install_flash_sign_keys_or_execution(self):
        src = SCRIPT.read_text()
        for forbidden in (
            "sudo ", "apt install", "sysupgrade", "fastboot",
            "dd if=", "scp ", "ssh root@", "flashrom",
            "sign-image", "gpg --import", "make install",
            "qemu-aarch64", "chroot ", "socat ", "curl | sh",
        ):
            self.assertNotIn(forbidden, src)
        self.assertIn('EUID == 0', src)
        self.assertIn('trap \'rm -rf -- "$tmp"\' EXIT', src)

    def test_header_check_requires_aarch64(self):
        src = SCRIPT.read_text()
        self.assertIn("header[:4]", src)
        self.assertIn("header[4] != 2", src)
        self.assertIn("header[5] != 1", src)
        self.assertIn("!= 183", src)
        self.assertIn("never execute", src)

    def test_does_not_claim_rootfs_completeness(self):
        src = SCRIPT.read_text()
        self.assertIn("not an OpenWrt rootfs or board firmware", src)


if __name__ == "__main__":
    unittest.main()
