#!/usr/bin/env python3
"""Offline byte-readback regression tests; no firmware assets required."""
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import unittest

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
