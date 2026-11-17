#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only regression tests for pair receipt file-descriptor validation."""
import ast
import importlib.util
import json
import os
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
            with self.assertRaises((OSError, ValueError)):
                pair.read_receipt(alias / "receipt.json")

    def test_nested_real_directories_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "one" / "two"
            nested.mkdir(parents=True)
            receipt = nested / "receipt.json"
            receipt.write_text('{"schema": 1}', encoding="utf-8")
            self.assertEqual(pair.read_receipt(receipt)[0], {"schema": 1})

    def test_parent_swap_after_directory_open_is_fd_anchored(self):
        # Swap a parent path after its descriptor is opened. The reader must
        # continue inside the original directory, never follow the replacement.
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            parent.mkdir()
            (parent / "receipt.json").write_text('{"origin": "original"}', encoding="utf-8")
            other = root / "other"
            other.mkdir()
            (other / "receipt.json").write_text('{"origin": "replacement"}', encoding="utf-8")
            moved = root / "moved"
            real_open = os.open
            swapped = False

            def swap_after_parent_open(file, flags, *args, **kwargs):
                nonlocal swapped
                fd = real_open(file, flags, *args, **kwargs)
                if not swapped and file == "parent" and "dir_fd" in kwargs:
                    swapped = True
                    parent.rename(moved)
                    parent.symlink_to(other, target_is_directory=True)
                return fd

            with patch.object(pair.os, "open", side_effect=swap_after_parent_open):
                value, _ = pair.read_receipt(parent / "receipt.json")
            self.assertTrue(swapped)
            self.assertEqual(value, {"origin": "original"})

    def test_final_symlink_swap_after_parent_open_is_rejected(self):
        # A receipt replaced after opening its parent must never be followed.
        # This exercises the final-component O_NOFOLLOW at the actual open.
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            parent.mkdir()
            receipt = parent / "receipt.json"
            receipt.write_text('{"origin": "original"}', encoding="utf-8")
            outside = root / "outside.json"
            outside.write_text('{"origin": "outside"}', encoding="utf-8")
            real_open = os.open
            swapped = False

            def swap_final_component(file, flags, *args, **kwargs):
                nonlocal swapped
                fd = real_open(file, flags, *args, **kwargs)
                if not swapped and file == "parent" and "dir_fd" in kwargs:
                    swapped = True
                    receipt.unlink()
                    receipt.symlink_to(outside)
                return fd

            with patch.object(pair.os, "open", side_effect=swap_final_component):
                with self.assertRaises(OSError):
                    pair.read_receipt(receipt)
            self.assertTrue(swapped)

    def test_final_regular_file_swap_after_open_reads_original_inode(self):
        # A rename after os.open must not redirect the already opened FD
        # to a different regular receipt at the same pathname.
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "receipt.json"
            receipt.write_text('{"origin": "original"}', encoding="utf-8")
            replacement = root / "replacement.json"
            replacement.write_text('{"origin": "replacement"}', encoding="utf-8")
            real_open = os.open
            swapped = False

            def swap_after_file_open(file, flags, *args, **kwargs):
                nonlocal swapped
                fd = real_open(file, flags, *args, **kwargs)
                if not swapped and file == "receipt.json" and "dir_fd" in kwargs:
                    swapped = True
                    receipt.rename(root / "old.json")
                    replacement.rename(receipt)
                return fd

            with patch.object(pair.os, "open", side_effect=swap_after_file_open):
                value, checksum = pair.read_receipt(receipt)
            self.assertTrue(swapped)
            self.assertEqual(value, {"origin": "original"})
            import hashlib
            self.assertEqual(checksum, hashlib.sha256(
                b'{"origin": "original"}').hexdigest())
            self.assertEqual(json.loads(receipt.read_text()), {"origin": "replacement"})

    def test_nested_symlink_ancestor_rejected(self):
        # An inner symlink must not bypass the descriptor-anchored walk.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real" / "nested").mkdir(parents=True)
            (root / "real" / "nested" / "receipt.json").write_text(
                '{"schema": 1}', encoding="utf-8")
            (root / "outer").mkdir()
            (root / "outer" / "alias").symlink_to(
                root / "real" / "nested", target_is_directory=True)
            with self.assertRaises((OSError, ValueError)):
                pair.read_receipt(root / "outer" / "alias" / "receipt.json")

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").mkdir()
            receipt = root / "real" / ".." / "receipt.json"
            (root / "receipt.json").write_text('{"schema": 1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "RECEIPT_SYMLINK_OR_INVALID_PATH"):
                pair.read_receipt(receipt)

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
