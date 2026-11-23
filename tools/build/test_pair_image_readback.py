#!/usr/bin/env python3
"""Offline byte-readback regression tests; no firmware assets required."""
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock

MODULE = pathlib.Path(__file__).with_name("compare_pair_repro_receipts.py")
spec = importlib.util.spec_from_file_location("pair_receipts", MODULE)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class ImageReadbackTests(unittest.TestCase):
    def test_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            payload = b"unsigned synthetic image" * 1024
            path.write_bytes(payload)
            self.assertEqual(
                pair.verify_image(str(path), hashlib.sha256(payload).hexdigest(), len(payload)),
                hashlib.sha256(payload).hexdigest(),
            )

    def test_identity_from_verified_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            alias = pathlib.Path(directory) / "alias"
            payload = b"distinct image identity"
            path.write_bytes(payload)
            alias.hardlink_to(path)
            expected = hashlib.sha256(payload).hexdigest()
            first = pair.verify_image(str(path), expected, len(payload), return_identity=True)
            second = pair.verify_image(str(alias), expected, len(payload), return_identity=True)
            self.assertEqual(first, second)
            self.assertEqual(first[0], expected)

    def test_cli_rejects_reused_image_inode(self):
        import contextlib
        import io
        import sys
        receipt = {field: "a" * 64 for field in pair.FIELDS}
        images = ["p25-a", "p25-b", "p26-a", "p26-b"]
        args = ["compare", "receipt-a", "receipt-b",
                "--p25-a", images[0], "--p25-b", images[1],
                "--p26-a", images[2], "--p26-b", images[3]]
        identities = iter([(0, 1), (0, 1)])
        with mock.patch.object(sys, "argv", args), \\
             mock.patch.object(pair, "load_with_identity", side_effect=[
                 (receipt, (1, 1)), (receipt, (1, 2))]), \\
             mock.patch.object(pair, "verify_image",
                               side_effect=lambda *a, **k: ("a" * 64, next(identities))), \\
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as caught:
                pair.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("four distinct files", stderr.getvalue())

    def test_corruption_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            path.write_bytes(b"abcd")
            digest = hashlib.sha256(b"abcd").hexdigest()
            with self.assertRaises(ValueError):
                pair.verify_image(str(path), digest, 5)
            with self.assertRaises(ValueError):
                pair.verify_image(str(path), hashlib.sha256(b"abce").hexdigest(), 4)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            link = pathlib.Path(directory) / "link"
            path.write_bytes(b"data")
            link.symlink_to(path)
            with self.assertRaises(OSError):
                pair.verify_image(str(link), hashlib.sha256(b"data").hexdigest(), 4)


if __name__ == "__main__":
    unittest.main()
