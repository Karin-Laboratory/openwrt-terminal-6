#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only regression tests for descriptor-bound unsigned pair hashing."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build/verify_unsigned_pair.py"
spec = importlib.util.spec_from_file_location("verify_unsigned_pair_fd", SCRIPT)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class DigestDescriptorTests(unittest.TestCase):
    def test_regular_file_matches_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input"
            path.write_bytes(b"unsigned pair test")
            self.assertEqual(pair.digest(path), hashlib.sha256(path.read_bytes()).hexdigest())

    def test_symlink_rejected_even_after_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.write_bytes(b"contents")
            link = Path(tmp) / "link"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                pair.digest(link)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFO")
    def test_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fifo"
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, "HASH_INPUT_NOT_REGULAR"):
                pair.digest(path)

    def test_in_place_change_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input"
            path.write_bytes(b"original")
            real_fstat = pair.os.fstat
            calls = 0

            def changed_after_read(fd):
                nonlocal calls
                calls += 1
                if calls == 2:
                    path.write_bytes(b"changed!")
                return real_fstat(fd)

            with mock.patch.object(pair.os, "fstat", side_effect=changed_after_read):
                with self.assertRaisesRegex(ValueError, "HASH_INPUT_CHANGED_DURING_READ"):
                    pair.digest(path)


if __name__ == "__main__":
    unittest.main()
