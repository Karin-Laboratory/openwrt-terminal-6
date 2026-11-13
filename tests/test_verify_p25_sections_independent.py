"""Host-only regression tests for independent p25 byte verifier."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/build/verify_p25_sections_independent.py"
spec = importlib.util.spec_from_file_location("verify_p25", MODULE)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class P25ReadbackTests(unittest.TestCase):
    def test_exact_bytes_and_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "p25.img"
            manifest = root / "manifest.json"
            payload = b"TEST-ONLY-NOT-BOOT-V2"
            with image.open("wb") as stream:
                stream.write(payload)
                stream.write(b"\0" * (verifier.P25_SIZE - len(payload)))
            record = {
                "format": "air6-p25-unsigned-sections-v1",
                "image_size": verifier.P25_SIZE,
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "sections": [{"name": "synthetic-header", "offset": 0,
                              "length": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
                "zero_padding_from": len(payload),
            }
            manifest.write_text(json.dumps(record))
            self.assertEqual(verifier.verify(image, manifest)["padding"], "PASS")
            self.assertEqual(verifier.verify(image, manifest)["boot_v2_header"], "NOT_CHECKED")
            with image.open("r+b") as stream:
                stream.seek(verifier.P25_SIZE - 1)
                stream.write(b"X")
            with self.assertRaisesRegex(ValueError, "full image SHA mismatch"):
                verifier.verify(image, manifest)


    def test_undeclared_nonzero_tail_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "p25.img"
            manifest = root / "manifest.json"
            payload = b"TEST"
            with image.open("wb") as stream:
                stream.write(payload)
                stream.write(b"\0" * (verifier.P25_SIZE - len(payload) - 1))
                stream.write(b"X")
            record = {
                "format": "air6-p25-unsigned-sections-v1",
                "image_size": verifier.P25_SIZE,
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "sections": [{"name": "synthetic", "offset": 0,
                              "length": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
            }
            manifest.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "nonzero unaccounted trailing bytes"):
                verifier.verify(image, manifest)
            # A zero-filled implicit tail is checked, not skipped.
            with image.open("r+b") as stream:
                stream.seek(verifier.P25_SIZE - 1)
                stream.write(b"\0")
            record["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(record))
            self.assertEqual(verifier.verify(image, manifest)["padding"], "PASS")
            alias = root / "alias.img"
            alias.symlink_to(image)
            with self.assertRaisesRegex(ValueError, "exactly 32 MiB"):
                verifier.verify(alias, manifest)

if __name__ == "__main__":
    unittest.main()
