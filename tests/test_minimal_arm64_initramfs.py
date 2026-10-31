# SPDX-License-Identifier: MIT
"""Offline archive/ELF format checks; does not execute AArch64 PID1."""
import gzip
import importlib.util
from pathlib import Path
import stat
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "minimal_initramfs", ROOT / "scripts/build-minimal-arm64-initramfs.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MinimalInitramfsTests(unittest.TestCase):
    def test_deterministic_archive_and_pid1_entry(self):
        first = module.make_archive(b"synthetic ELF placeholder")
        self.assertEqual(first, module.make_archive(b"synthetic ELF placeholder"))
        self.assertTrue(first.startswith(b"070701"))
        self.assertIn(b"init\x00", first)
        self.assertIn(b"dev/console\x00", first)
        self.assertIn(b"TRAILER!!!\x00", first)
        self.assertEqual(gzip.decompress(gzip.compress(first, mtime=0)), first)

    def test_reject_unsafe_cpio_paths(self):
        for path in ("/init", "../init", "dev/../init", "", "bad\x00name"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.newc_entry(path, stat.S_IFREG | 0o755)

    def test_reject_non_arm64_or_dynamic_elf(self):
        with self.assertRaises(ValueError):
            module.validate_elf(b"not an ELF")
        fake = bytearray(64)
        fake[:6] = b"\x7fELF\x02\x01"
        with self.assertRaises(ValueError):
            module.validate_elf(bytes(fake))


if __name__ == "__main__":
    unittest.main()
