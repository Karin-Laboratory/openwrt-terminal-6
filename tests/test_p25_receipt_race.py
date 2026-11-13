# SPDX-License-Identifier: MIT
"""Regression for p25 receipt exclusive creation during a competing write."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.build import assemble_p25_unsigned_layout as assembler

class ReceiptRaceTests(unittest.TestCase):
    def test_competing_receipt_is_not_overwritten_or_deleted(self):
        with TemporaryDirectory() as tmp, patch.object(assembler, "SIZE", 128):
            root = Path(tmp)
            source = root / "kernel"
            source.write_bytes(b"kernel")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "format": "unsigned-p25-layout-input-v1",
                "segments": [{"path": str(source), "offset": 8,
                              "length": 6,
                              "sha256": hashlib.sha256(b"kernel").hexdigest()}]}))
            image, receipt = root / "image", root / "receipt.json"
            original_open = Path.open
            def concurrent_open(path, mode="r", *args, **kwargs):
                if Path(path) == receipt and mode == "x":
                    receipt.write_bytes(b"other writer\n")
                return original_open(path, mode, *args, **kwargs)
            with patch.object(Path, "open", concurrent_open):
                with self.assertRaises(FileExistsError):
                    assembler.assemble(manifest, image, receipt)
            self.assertEqual(receipt.read_bytes(), b"other writer\n")
            self.assertFalse(image.exists())

if __name__ == "__main__":
    unittest.main()
