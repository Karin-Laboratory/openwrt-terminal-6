#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic negative tests for the independent p26 byte-layout verifier.

These do not establish genuine OpenWrt rootfs or metadata acceptance.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

PARTITION_SIZE = 134217728
VERIFY = Path(__file__).resolve().parents[1] / "tools/build/verify_p26_partition.py"


class VerifyP26PartitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "rootfs_a.p26"
        self.receipt = self.root / "receipt.json"
        header = bytearray(96)
        header[:4] = b"hsqs"
        struct.pack_into("<HH", header, 28, 4, 0)
        struct.pack_into("<Q", header, 40, 96)
        self.image.write_bytes(header)
        with self.image.open("ab") as stream:
            stream.truncate(PARTITION_SIZE)
        self.write_receipt()

    def write_receipt(self):
        with self.image.open("rb") as stream:
            filesystem = stream.read(96)
            stream.seek(0)
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        self.receipt.write_text(json.dumps({
            "squashfs_bytes": 96,
            "squashfs_sha256": hashlib.sha256(filesystem).hexdigest(),
            "p26_sha256": digest,
            "signed": False,
        }))

    def run_verifier(self):
        return subprocess.run(
            [sys.executable, str(VERIFY), "--image", str(self.image),
             "--receipt", str(self.receipt)],
            capture_output=True, text=True, check=False,
        )

    def test_synthetic_layout_passes_only_byte_gate(self):
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NOT_FS_METADATA_OR_SOURCE_PROVENANCE_ACCEPTANCE", result.stdout)

    def test_padding_tamper_rejected_even_with_updated_partition_hash(self):
        with self.image.open("r+b") as stream:
            stream.seek(4096)
            stream.write(b"X")
        self.write_receipt()
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_filesystem_tamper_rejected(self):
        with self.image.open("r+b") as stream:
            stream.seek(8)
            stream.write(b"X")
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_receipt_partition_hash_tamper_rejected(self):
        record = json.loads(self.receipt.read_text())
        record["p26_sha256"] = "0" * 64
        self.receipt.write_text(json.dumps(record))
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_signed_receipt_rejected(self):
        record = json.loads(self.receipt.read_text())
        record["signed"] = True
        self.receipt.write_text(json.dumps(record))
        self.assertNotEqual(self.run_verifier().returncode, 0)


if __name__ == "__main__":
    unittest.main()
