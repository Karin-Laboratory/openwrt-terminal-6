#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only regression tests for pair receipt file-descriptor validation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/build/verify_unsigned_pair.py"
spec = importlib.util.spec_from_file_location("verify_unsigned_pair", MODULE)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class ReceiptInputTests(unittest.TestCase):
    def test_regular_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"schema": 1}', encoding="utf-8")
            value, checksum = pair.read_receipt(path)
            self.assertEqual(value, {"schema": 1})
            self.assertEqual(len(checksum), 64)

    def test_symlink_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            target.write_text('{"schema": 1}', encoding="utf-8")
            link = Path(directory) / "receipt.json"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                pair.read_receipt(link)

    def test_directory_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((OSError, ValueError)):
                pair.read_receipt(Path(directory))

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                pair.read_receipt(path)


if __name__ == "__main__":
    unittest.main()
