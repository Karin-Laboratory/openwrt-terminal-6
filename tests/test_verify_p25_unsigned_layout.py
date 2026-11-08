# SPDX-License-Identifier: MIT
"""Synthetic host regression for unsigned p25 byte readback; no boot claim."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.build import verify_p25_unsigned_layout as verifier

class P25LayoutTests(unittest.TestCase):
    def test_segment_padding_hash_and_overlap(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(verifier, "SIZE", 128):
            image = Path(directory) / "image"
            receipt = Path(directory) / "receipt.json"
            payload = b"KERNEL"
            original = b"\0" * 8 + payload + b"\0" * (128 - 8 - len(payload))
            image.write_bytes(original)
            record = {"format": "unsigned-p25-layout-v1", "partition_bytes": 128,
                      "p25_sha256": hashlib.sha256(original).hexdigest(),
                      "boot_v2_verified": False,
                      "status": "LAYOUT_CANDIDATE_ONLY_NOT_BOOTABLE",
                      "segments": [{"offset": 8, "length": len(payload),
                                    "sha256": hashlib.sha256(payload).hexdigest()}]}
            receipt.write_text(json.dumps(record))
            self.assertEqual(verifier.verify(image, receipt), record["p25_sha256"])
            record["boot_v2_verified"] = True
            receipt.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                verifier.verify(image, receipt)
            record["boot_v2_verified"] = False
            receipt.write_text(json.dumps(record))
            for index in (0, 8, 127):
                modified = bytearray(original)
                modified[index] ^= 1
                image.write_bytes(modified)
                with self.assertRaises(ValueError):
                    verifier.verify(image, receipt)
            image.write_bytes(original)
            record["segments"].append(record["segments"][0])
            receipt.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                verifier.verify(image, receipt)

    def test_assembler_to_independent_readback_and_reject_corruption(self):
        from tools.build import assemble_p25_unsigned_layout as assembler
        with tempfile.TemporaryDirectory() as directory, patch.object(assembler, "SIZE", 128), patch.object(verifier, "SIZE", 128):
            root = Path(directory)
            source = root / "kernel"
            source.write_bytes(b"REAL-INPUT-BYTES")
            manifest = root / "manifest.json"
            image = root / "p25.img"
            receipt = root / "receipt.json"
            manifest.write_text(json.dumps({
                "format": "unsigned-p25-layout-input-v1",
                "segments": [{"path": str(source), "offset": 32,
                              "length": source.stat().st_size,
                              "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]
            }))
            record = assembler.assemble(manifest, image, receipt)
            self.assertEqual(image.stat().st_size, 128)
            self.assertEqual(verifier.verify(image, receipt), record["p25_sha256"])
            self.assertFalse(record["boot_v2_verified"])
            changed = bytearray(image.read_bytes())
            changed[32] ^= 1
            image.write_bytes(changed)
            with self.assertRaises(ValueError):
                verifier.verify(image, receipt)
            with self.assertRaises(ValueError):
                assembler.assemble(manifest, image, root / "other-receipt.json")

if __name__ == "__main__":
    unittest.main()
