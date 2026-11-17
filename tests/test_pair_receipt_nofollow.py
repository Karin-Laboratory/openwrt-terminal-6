#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only regression tests for pair receipt file-descriptor validation."""
import ast
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
    def test_initramfs_object_hash_is_assigned(self):
        # An escaped newline in a comment previously swallowed the assignment,
        # leaving the pair verifier with an unbound local at receipt creation.
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        verify = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == "verify_pair")
        assignments = [node for node in ast.walk(verify)
                       if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name)
                               and target.id == "initramfs_object_hash"
                               for target in node.targets)]
        self.assertEqual(len(assignments), 1)

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

    def test_symlink_parent_receipt_rejected_by_valid_path(self):
        # A final-component O_NOFOLLOW check does not cover parent links.
        # The caller must reject a symlinked ancestor before attestation.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "actual"
            actual.mkdir()
            receipt = actual / "receipt.json"
            receipt.write_text('{"schema": 1}', encoding="utf-8")
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            self.assertFalse(pair.valid_path(alias / "receipt.json"))
            self.assertTrue(pair.valid_path(receipt))
            with self.assertRaisesRegex(ValueError, "RECEIPT_SYMLINK_OR_INVALID_PATH"):
                pair.read_receipt(alias / "receipt.json")

    def test_nested_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"outer": {"schema": 1, "schema": 2}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
                pair.read_receipt(path)

    def test_directory_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((OSError, ValueError)):
                pair.read_receipt(Path(directory))

    def test_fifo_receipt_rejected_without_blocking(self):
        # A FIFO is not a receipt. O_NONBLOCK prevents hanging before fstat.
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, "RECEIPT_NOT_REGULAR"):
                pair.read_receipt(path)

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                pair.read_receipt(path)


    def test_nonfinite_constant_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "NONFINITE_JSON_CONSTANT"):
                pair.read_receipt(path)

    def test_receipt_size_limit_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_bytes(b" " * (pair.MAX_RECEIPT_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "RECEIPT_TOO_LARGE"):
                pair.read_receipt(path)

    def test_empty_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_bytes(b"")
            with self.assertRaises(json.JSONDecodeError):
                pair.read_receipt(path)


if __name__ == "__main__":
    unittest.main()
