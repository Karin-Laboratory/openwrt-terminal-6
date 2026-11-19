"""Host-only negative tests for unsigned p25 independent readback."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "tools/build/verify_p25_unsigned_sections.py"
spec = importlib.util.spec_from_file_location("p25_readback", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / "p25.img"
        with self.image.open("wb") as f:
            f.write(b"ABCD")
            f.truncate(mod.SIZE)
        self.manifest = {"image_sha256": mod.sha256_file(self.image),
                         "sections": [{"offset": 0, "length": 4,
                                       "sha256": hashlib.sha256(b"ABCD").hexdigest()}]}

    def test_full_readback(self):
        self.assertEqual(mod.verify(self.image, self.manifest)["sections_verified"], 1)

    def test_full_sha_mismatch(self):
        self.manifest["image_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "FULL_SHA"):
            mod.verify(self.image, self.manifest)

    def test_section_sha_mismatch(self):
        self.manifest["sections"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SECTION_SHA"):
            mod.verify(self.image, self.manifest)

    def test_overlapping_sections(self):
        self.manifest["sections"].append(dict(self.manifest["sections"][0]))
        with self.assertRaisesRegex(ValueError, "SECTION_RANGE"):
            mod.verify(self.image, self.manifest)

    def test_nonzero_padding(self):
        with self.image.open("r+b") as f:
            f.seek(100)
            f.write(b"X")
        self.manifest["image_sha256"] = mod.sha256_file(self.image)
        with self.assertRaisesRegex(ValueError, "NONZERO_PADDING"):
            mod.verify(self.image, self.manifest)

    def test_size_mismatch(self):
        with self.image.open("r+b") as f:
            f.truncate(100)
        with self.assertRaisesRegex(ValueError, "SIZE_MISMATCH"):
            mod.verify(self.image, self.manifest)


if __name__ == "__main__":
    unittest.main()
