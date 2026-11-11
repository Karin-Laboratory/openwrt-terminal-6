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

    def test_receipt_open_failure_rolls_back_new_image(self):
        # Exercise the post-image-write failure path with valid synthetic inputs.
        import json
        import struct
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.gz"
            ramdisk = root / "ramdisk"
            dtb = root / "board.dtb"
            config = root / "config.json"
            output = root / "p25.img"
            kernel.write_bytes(gzip.compress(b"synthetic kernel"))
            ramdisk.write_bytes(b"synthetic ramdisk")
            dtb.write_bytes(b"\\xd0\\x0d\\xfe\\xed" + struct.pack(">I", 40) + bytes(32))
            config.write_text(json.dumps({
                "kernel_addr": "0x40008000", "ramdisk_addr": "0x42000000",
                "tags_addr": "0x40000100", "dtb_addr": "0x43000000",
                "name": "test", "cmdline": "console=ttyS0"
            }))
            original_open = packer.os.open

            def reject_receipt(path, flags, mode=0o777):
                if Path(path) == output.with_name(output.name + ".json"):
                    raise PermissionError("synthetic receipt failure")
                return original_open(path, flags, mode)

            with patch.object(packer.os, "open", side_effect=reject_receipt):
                with self.assertRaises(PermissionError):
                    packer.build(kernel, ramdisk, dtb, config, output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_name(output.name + ".json").exists())

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
