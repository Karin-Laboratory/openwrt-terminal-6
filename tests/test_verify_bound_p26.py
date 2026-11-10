# SPDX-License-Identifier: MIT
"""Host-only dynamic P26 early-boot hash checker regressions."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/boot/verify_bound_p26.sh"


class BoundP26Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.p26 = self.work / "fake-p26"
        self.p26.write_bytes(b"synthetic public test rootfs")
        self.manifest = self.work / "p26.sha256"
        self.set_manifest(hashlib.sha256(self.p26.read_bytes()).hexdigest())

    def set_manifest(self, hexhash):
        self.manifest.write_text(f"{hexhash}  {self.p26}\n")

    def check(self, *paths):
        args = ["sh", str(SCRIPT)]
        args.extend(str(p) for p in (paths or (self.manifest, self.p26)))
        return subprocess.run(args, capture_output=True, text=True, timeout=10)

    def test_full_hash_passes(self):
        output = self.check()
        self.assertEqual(output.returncode, 0)
        self.assertIn("P26_RUNTIME_FULL_SHA256_PASS", output.stdout)

    def test_trailing_blank_line_fails(self):
        self.manifest.write_bytes(self.manifest.read_bytes() + b"\\n")
        self.assertEqual(self.check().returncode, 15)

    def test_missing_final_newline_fails(self):
        self.manifest.write_bytes(self.manifest.read_bytes().rstrip(b"\\n"))
        self.assertEqual(self.check().returncode, 15)

    def test_embedded_nul_fails(self):
        data = self.manifest.read_bytes()
        self.manifest.write_bytes(data[:-1] + b"\\x00\\n")
        self.assertEqual(self.check().returncode, 15)

    def test_extra_line_fails(self):
        self.manifest.write_bytes(self.manifest.read_bytes() + b"extra\\n")
        self.assertEqual(self.check().returncode, 15)

    def test_modified_partition_fails(self):
        self.p26.write_bytes(b"synthetic public test changed")
        self.assertEqual(self.check().returncode, 17)

    def test_mismatched_manifest_fails(self):
        self.set_manifest("0" * 64)
        self.assertEqual(self.check().returncode, 17)

    def test_wrong_manifest_device_fails(self):
        self.manifest.write_text("0" * 64 + "  /another-device\n")
        self.assertEqual(self.check().returncode, 15)

    def test_missing_or_symlinked_manifest_fails(self):
        self.manifest.unlink()
        self.assertEqual(self.check().returncode, 11)
        self.manifest.symlink_to(self.p26)
        self.assertEqual(self.check().returncode, 11)

    def test_missing_or_symlinked_device_fails(self):
        self.p26.unlink()
        self.assertEqual(self.check().returncode, 12)
        other = self.work / "other"
        other.write_bytes(b"synthetic")
        self.p26.symlink_to(other)
        self.assertEqual(self.check().returncode, 12)


if __name__ == "__main__":
    unittest.main()
