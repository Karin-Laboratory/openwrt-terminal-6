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
        self.assertIn("CONFIG_TC is not set", src)
        self.assertIn("older Linux UAPI types", src)

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

    def test_single_build_and_elf_header_check(self):
        src = SCRIPT.read_text()
        self.assertEqual(src.count("timeout 450s make"), 1)
        self.assertEqual(src.count("<<'PY'"), 1)
        self.assertEqual(src.count("BUSYBOX_ARM64_ELF_HEADER_PASS"), 1)
        self.assertNotIn("CONFIG_TC=ytimeout", src)

    def test_native_musl_mode_uses_explicit_compiler_and_pinned_libc(self):
        src = SCRIPT.read_text()
        self.assertIn("native-musl-static-stage", src)
        self.assertIn("native-musl-static-initramfs", src)
        self.assertIn("SBAT6_MUSL_CC", src)
        self.assertIn('cc_override=("CC=$compiler")', src)
        self.assertIn("musl-static", src)
        musl = (ROOT / "scripts/build-arm64-musl-busybox-stage.sh").read_text()
        self.assertIn("ifduyue/musl.git", musl)
        self.assertIn("0784374d561435f7c787a555aeab8ede699ed298", musl)
        self.assertIn("native-musl-static-stage", musl)
        self.assertIn("native-musl-static-initramfs", musl)
        self.assertIn("SBAT6_NATIVE_MUSL_STATIC_PID1_INITRAMFS_PASS", musl)
        self.assertIn("7d0a66e4bb9081d75c82ec4957c50034cb0ea449", musl)
        self.assertIn("headers_install", musl)
        self.assertIn('INSTALL_HDR_PATH="$tmp/kernel-headers"', musl)
        self.assertIn("SBAT6_NATIVE_MUSL_STATIC_BUSYBOX_STAGE_PASS", musl)
        self.assertIn("EUID == 0", musl)
        self.assertNotIn("sudo ", musl)
        self.assertNotIn("make install DESTDIR=/", musl)

    def test_does_not_claim_rootfs_completeness(self):
        src = SCRIPT.read_text()
        self.assertIn("not an OpenWrt rootfs or board firmware", src)


if __name__ == "__main__":
    unittest.main()
