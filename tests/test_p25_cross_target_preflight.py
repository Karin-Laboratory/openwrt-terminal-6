#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-fast checks for the public P25 source-build toolchain preflight."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/manufacture-public-openwrt-p25-from-debian14.sh"


class CrossTargetPreflight(unittest.TestCase):
    def check_target(self, gcc_target, ld_banner, expected):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bindir = root / "bin"
            bindir.mkdir()
            gcc = bindir / "fake-gcc"
            ld = bindir / "fake-ld"
            gcc.write_text("#!/bin/sh\necho " + repr(gcc_target) + "\n")
            ld.write_text("#!/bin/sh\necho " + repr(ld_banner) + "\n")
            gcc.chmod(0o755)
            ld.chmod(0o755)
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
            result = subprocess.run(
                ["bash", str(SCRIPT), str(root / "fresh"),
                 str(cpio), str(p26), str(producer), str(independent)],
                env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(expected, result.stderr)
            self.assertFalse((root / "fresh").exists())

    def test_wrong_compiler_architecture(self):
        self.check_target("x86_64-linux-gnu", "GNU ld 2.40\\n  Supported emulations:\\n   aarch64linux", 
                          "PUBLIC_PAIR_BLOCKED_CROSS_COMPILER_TARGET")

    def test_wrong_linker_architecture(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\\n  Supported emulations:\\n   elf_x86_64",
                          "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET")

    def test_aarch64_supported_but_not_default(self):
        self.check_target("aarch64-linux-gnu", "GNU ld 2.40\\n  Supported emulations:\\n   elf_x86_64\\n   aarch64linux", "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET")


if __name__ == "__main__":
    unittest.main()
