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
                      "segments": [{"offset": 8, "length": len(payload),
                                    "sha256": hashlib.sha256(payload).hexdigest()}]}
            receipt.write_text(json.dumps(record))
            self.assertEqual(verifier.verify(image, receipt), record["p25_sha256"])
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

if __name__ == "__main__":
    unittest.main()
