#!/usr/bin/env python3
"""Synthetic newc checksum regression tests. SPDX-License-Identifier: MIT"""
import importlib.util
import pathlib
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "compare_newc.py"
spec = importlib.util.spec_from_file_location("compare_newc", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def record(name, payload=b"", crc=False, corrupt=False):
    name = name.encode() + b"\0"
    checksum = sum(payload) & 0xffffffff if crc else 0
    if corrupt:
        checksum ^= 1
    fields = [1, 0o100644, 0, 0, 1, 0, len(payload), 0, 0, 0, 0, len(name), checksum]
    header = (b"070702" if crc else b"070701") + b"".join(
        ("%08x" % x).encode() for x in fields
    )
    blob = header + name
    blob += b"\0" * (-len(blob) % 4)
    blob += payload
    blob += b"\0" * (-len(blob) % 4)
    return blob


class ChecksumTests(unittest.TestCase):
    def parse(self, blob):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "test.cpio"
            path.write_bytes(blob + record("TRAILER!!!"))
            return mod.entries(path)

    def test_trailer_padding_difference_is_not_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            a = pathlib.Path(d) / "a.cpio"
            b = pathlib.Path(d) / "b.cpio"
            payload = record("hello", b"abc") + record("TRAILER!!!")
            a.write_bytes(payload)
            b.write_bytes(payload + b"\0" * 512)
            report = mod.compare(a, b)
            self.assertEqual(report["changed"], [])
            self.assertTrue(report["order_matches"])
            self.assertFalse(report["byte_identical"])

    def test_equal_complete_archives_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            a = pathlib.Path(d) / "a.cpio"
            b = pathlib.Path(d) / "b.cpio"
            payload = record("hello", b"abc") + record("TRAILER!!!")
            a.write_bytes(payload)
            b.write_bytes(payload)
            self.assertTrue(mod.compare(a, b)["byte_identical"])

    def test_valid_crc(self):
        self.assertEqual(self.parse(record("hello", b"abc", crc=True))[0]["filesize"], 3)

    def test_bad_crc_rejected(self):
        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            self.parse(record("hello", b"abc", crc=True, corrupt=True))

    def test_noncrc_checksum_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonzero checksum"):
            self.parse(record("hello", b"abc", corrupt=True))


if __name__ == "__main__":
    unittest.main()
