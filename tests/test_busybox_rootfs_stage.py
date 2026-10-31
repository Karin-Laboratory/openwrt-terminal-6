# SPDX-License-Identifier: MIT
"""Host-only tests of deterministic, non-installable BusyBox stage packaging."""
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/package-arm64-busybox-rootfs.py"
spec = importlib.util.spec_from_file_location("busybox_stage", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def synthetic_elf(interpreter=False):
    header = bytearray(64 + 56)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", header, 16, 2, 183)
    struct.pack_into("<Q", header, 32, 64)
    struct.pack_into("<HH", header, 54, 56, 1)
    struct.pack_into("<I", header, 64, 3 if interpreter else 1)
    return bytes(header)


class StaticBusyboxStageTests(unittest.TestCase):
    def test_archive_contents_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            elf = root / "busybox"
            elf.write_bytes(synthetic_elf())
            a, m = root / "one.tar.gz", root / "one.json"
            b, n = root / "two.tar.gz", root / "two.json"
            first = module.package(elf, a, m)
            second = module.package(elf, b, n)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(first, second)
            self.assertEqual(json.loads(m.read_text()), first)
            self.assertEqual(first["rights_review"], "pending")
            with tarfile.open(a, "r:gz") as archive:
                self.assertEqual(archive.getmember("bin/sh").linkname, "busybox")
                self.assertEqual(archive.extractfile("bin/busybox").read(), elf.read_bytes())
                self.assertNotIn("init", archive.getnames())
                self.assertNotIn("etc/passwd", archive.getnames())

    def test_reject_dynamic_interpreter(self):
        with self.assertRaisesRegex(ValueError, "dynamic interpreter"):
            module.check_static_aarch64_elf(synthetic_elf(interpreter=True))

    def test_reject_wrong_arch_and_existing_output(self):
        with self.assertRaises(ValueError):
            module.check_static_aarch64_elf(b"not ELF")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            elf = root / "busybox"
            elf.write_bytes(synthetic_elf())
            existing = root / "already"
            existing.write_text("keep")
            with self.assertRaisesRegex(ValueError, "output must not"):
                module.package(elf, existing, root / "manifest")
            self.assertEqual(existing.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
