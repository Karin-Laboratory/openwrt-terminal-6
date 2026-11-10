# SPDX-License-Identifier: MIT
"""Host-only synthetic first-stage assembly and failure regressions."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build/build_air6_first_stage.py"
spec = importlib.util.spec_from_file_location("build_air6_first_stage", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FirstStageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.root = base / "rootfs"
        for directory in ("bin", "lib", "etc"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        elf = bytearray(2048)
        elf[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", elf, 18, 183)
        (self.root / "bin/busybox").write_bytes(elf)
        (self.root / "lib/libc.so").write_bytes(b"fake-musl")
        (self.root / "lib/ld-musl-aarch64.so.1").symlink_to("libc.so")
        self.p26 = base / "p26"
        self.p26.write_bytes(b"hsqs" + bytes(252))
        self.out = base / "first.cpio"
        self.size = patch.object(mod, "P26_BYTES", 256)
        self.size.start()
        self.addCleanup(self.size.stop)

    def test_builds_first_stage_with_exact_p26_hash(self):
        receipt = mod.build(self.root, self.p26, self.out)
        archive = self.out.read_bytes()
        self.assertTrue(archive.startswith(b"070701"))
        self.assertEqual(receipt["p26_sha256"],
                         hashlib.sha256(self.p26.read_bytes()).hexdigest())
        self.assertIn(receipt["p26_sha256"].encode("ascii") +
                      b"  /dev/mmcblk0p26", archive)
        self.assertIn(b"usr/libexec/air6/verify-bound-p26", archive)
        self.assertIn(b"usr/libexec/air6/prepare-p44-state", archive)
        self.assertIn(b"AIR6_FIRST_STAGE_P26_SHA_PASS", archive)
        self.assertIn(b"TRAILER!!!", archive)
        with self.assertRaisesRegex(ValueError, "OUTPUT"):
            mod.build(self.root, self.p26, self.out)

    def test_mutated_p26_changes_binding(self):
        expected = mod.build(self.root, self.p26, self.out)["p26_sha256"]
        self.out.unlink()
        data = bytearray(self.p26.read_bytes())
        data[-1] = 1
        self.p26.write_bytes(data)
        actual = mod.build(self.root, self.p26, self.out)["p26_sha256"]
        self.assertNotEqual(expected, actual)

    def test_wrong_architecture_rejected(self):
        elf = self.root / "bin/busybox"
        raw = bytearray(elf.read_bytes())
        struct.pack_into("<H", raw, 18, 62)
        elf.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "BUSYBOX_NOT_AARCH64"):
            mod.build(self.root, self.p26, self.out)

    def test_linked_loader_outside_staging_rejected(self):
        loader = self.root / "lib/ld-musl-aarch64.so.1"
        loader.unlink()
        loader.symlink_to("/tmp/not-allowed")
        with self.assertRaisesRegex(ValueError, "LIBRARY_SYMLINK_OUTSIDE"):
            mod.build(self.root, self.p26, self.out)

    def test_wrong_p26_size_rejected(self):
        self.p26.write_bytes(b"hsqs")
        with self.assertRaisesRegex(ValueError, "P26_IDENTITY"):
            mod.build(self.root, self.p26, self.out)


if __name__ == "__main__":
    unittest.main()
