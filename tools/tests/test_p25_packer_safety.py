#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only P25 packer safety regression tests."""
import gzip
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PACKER = Path(__file__).resolve().parents[1] / "boot" / "pack_p25_unsigned_v2.py"
spec = importlib.util.spec_from_file_location("p25_packer", PACKER)
packer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)


class P25SafetyTest(unittest.TestCase):
    def test_bounded_gzip_rejects_oversize_expansion(self):
        # A small compressed input must not force an unbounded allocation.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.gz"
            kernel.write_bytes(gzip.compress(b"K" * 8192))
            with patch.object(packer, "MAX_KERNEL_UNCOMPRESSED", 4096):
                with self.assertRaisesRegex(ValueError, "KERNEL_UNCOMPRESSED_TOO_LARGE"):
                    packer.build(kernel, root / "unused", root / "unused2",
                                 root / "unused3", root / "output")
            self.assertFalse((root / "output").exists())

    def test_existing_receipt_blocks_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "p25.img"
            receipt = root / "p25.img.json"
            receipt.write_text("existing receipt")
            with self.assertRaisesRegex(ValueError, "RECEIPT_EXISTS"):
                packer.build(root / "missing-kernel", root / "missing-ramdisk",
                             root / "missing-dtb", root / "missing-config", output)
            self.assertFalse(output.exists())
            self.assertEqual(receipt.read_text(), "existing receipt")

    def test_exclusive_output_flag_present(self):
        # Guard against regressing to non-atomic Path.write_bytes.
        import inspect
        source = inspect.getsource(packer.build)
        self.assertIn("os.O_EXCL", source)
        self.assertIn("receipt_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL", source)
        self.assertIn("os.open(output, flags, 0o600)", source)
        self.assertNotIn("output.write_bytes(data)", source)


if __name__ == "__main__":
    unittest.main()
