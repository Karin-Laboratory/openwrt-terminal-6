#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-fast checks for the public P25 source-build toolchain preflight."""
import os
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/manufacture-public-openwrt-p25-from-debian14.sh"


class CrossTargetPreflight(unittest.TestCase):
    def check_target(self, gcc_target, ld_banner, expected, gcc_exit=0, ld_exit=0):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bindir = root / "bin"
            bindir.mkdir()
            gcc = bindir / "fake-gcc"
            ld = bindir / "fake-ld"
            gcc.write_text("#!/bin/sh\necho " + repr(gcc_target) + "\nexit " + str(gcc_exit) + "\n")
            # Use printf: shell echo handles backslash escapes inconsistently.
            ld.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(ld_banner) + "\nexit " + str(ld_exit) + "\n")
            gcc.chmod(0o755)
            ld.chmod(0o755)
            # Preflight requires dtc to exist, but must reject a wrong target
            # before invoking it. Keep this fixture independent of host packages.
            dtc = bindir / "dtc"
            dtc.write_text("#!/bin/sh\nexit 99\n")
            dtc.chmod(0o755)
            cpio = root / "first.cpio"
            cpio.write_bytes(b"070701")
            p26 = root / "rootfs.p26"
            with p26.open("wb") as f:
                f.truncate(134217728)
            producer = root / "producer.json"
            independent = root / "independent.json"
            producer.write_text("{}")
            independent.write_text("{}")
            env = os.environ.copy()
            env["AIR6_CROSS_COMPILE"] = str(bindir / "fake-")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(SCRIPT), str(root / "fresh"),
                 str(cpio), str(p26), str(producer), str(independent)],
                env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(expected, result.stderr)
            self.assertFalse((root / "fresh").exists())

    def test_wrong_compiler_architecture(self):
        self.check_target("x86_64-linux-gnu", "GNU ld 2.40\n  Supported emulations:\n   aarch64linux", 
                          "PUBLIC_PAIR_BLOCKED_CROSS_COMPILER_TARGET")

    def test_wrong_linker_architecture(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\n  Supported emulations:\n   elf_x86_64",
                          "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET")

    def test_aarch64_supported_but_not_default(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\n  Supported emulations:\n   elf_x86_64\n   aarch64linux", "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET")

    def test_linker_emulations_header_without_entries(self):
        self.check_target(
            "aarch64-linux-gnu",
            "GNU ld 2.40\n  Supported emulations:",
            "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET",
        )

    def test_linker_unrelated_banner_rejected(self):
        self.check_target(
            "aarch64-linux-gnu",
            "GNU ld 2.40\n  supported targets: aarch64linux",
            "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET",
        )

    def test_linker_spoofed_aarch64_prefix_rejected(self):
        self.check_target(
            "aarch64-linux-gnu",
            "GNU ld 2.40\n  Supported emulations:\n   aarch64notanemulation",
            "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET",
        )

    def test_big_endian_linker_default_rejected(self):
        # The kernel and OpenWrt AArch64 target here are little-endian.
        # A big-endian ld default is not an interchangeable ARM64 linker.
        for emulation in ("aarch64linuxb", "aarch64elfb"):
            with self.subTest(emulation=emulation):
                self.check_target(
                    "aarch64-linux-gnu",
                    "GNU ld 2.40\n  Supported emulations:\n   " + emulation,
                    "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET",
                )

    def test_valid_aarch64_targets_pass_preflight_before_git_clone(self):
        # The rejection-only tests must not accidentally allow a preflight
        # that rejects every toolchain, including a valid GNU ARM64 pair.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bindir = root / "bin"
            bindir.mkdir()
            for name, body in (
                ("fake-gcc", "echo aarch64-linux-gnu"),
                ("fake-ld", "printf 'GNU ld 2.40\n  Supported emulations:\n   aarch64linux\n'"),
                ("dtc", "exit 99"),
                ("git", "echo PUBLIC_TEST_GIT_CLONE_STOP >&2; exit 93"),
            ):
                tool = bindir / name
                tool.write_text("#!/bin/sh\n" + body + "\n")
                tool.chmod(0o755)
            cpio = root / "first.cpio"
            cpio.write_bytes(b"070701")
            p26 = root / "rootfs.p26"
            with p26.open("wb") as output:
                output.truncate(134217728)
            producer = root / "producer.json"
            independent = root / "independent.json"
            producer.write_text("{}")
            independent.write_text("{}")
            env = os.environ.copy()
            env["AIR6_CROSS_COMPILE"] = str(bindir / "fake-")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(SCRIPT), str(root / "fresh"),
                 str(cpio), str(p26), str(producer), str(independent)],
                env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 93, result.stderr)
            self.assertIn("PUBLIC_TEST_GIT_CLONE_STOP", result.stderr)
            self.assertTrue((root / "fresh").is_dir())

    def test_compiler_target_query_failure(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\n  Supported emulations:\n   aarch64linux",
                          "PUBLIC_PAIR_BLOCKED_CROSS_COMPILER_TARGET_QUERY", gcc_exit=1)

    def test_linker_target_query_failure(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\n  Supported emulations:\n   aarch64linux",
                          "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET_QUERY", ld_exit=1)


if __name__ == "__main__":
    unittest.main()
