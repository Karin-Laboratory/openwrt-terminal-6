# SPDX-License-Identifier: MIT
import gzip
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tools/boot/pack_p25_unsigned_v2.py"
spec = importlib.util.spec_from_file_location("p25", PATH)
p25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p25)
VPATH = PATH.with_name('verify_p25_independent.py')
vspec = importlib.util.spec_from_file_location('p25_verify', VPATH)
p25verify = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(p25verify)


class TestP25BootV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = Path(self.tmp.name)
        self.kernel, self.ramdisk, self.dtb, self.cfg = [p / v for v in
            ("kernel.gz", "ramdisk.cpio.gz", "board.dtb", "config.json")]
        self.output = p / "unsigned.p25"
        self.kernel.write_bytes(gzip.compress(b"synthetic-kernel" * 200))
        self.ramdisk.write_bytes(gzip.compress(b"070701" + b"synthetic"))
        self.dtb.write_bytes(b"\xd0\x0d\xfe\xed" + struct.pack(">I", 40) + bytes(32))
        self.cfg.write_text(json.dumps({
            "kernel_addr": "0x40080000", "ramdisk_addr": "0x44000000",
            "tags_addr": "0x40000100", "dtb_addr": "0x48000000",
            "name": "public-test", "cmdline": "console=ttyS0"}))

    def test_layout_v2_full_partition(self):
        receipt = p25.build(self.kernel, self.ramdisk, self.dtb,
                            self.cfg, self.output)
        content = self.output.read_bytes()
        self.assertEqual(len(content), 33554432)
        self.assertEqual(content[:8], b"ANDROID!")
        self.assertEqual(struct.unpack_from("<I", content, 40)[0], 2)
        self.assertEqual(struct.unpack_from("<I", content, 1644)[0], 1660)
        self.assertEqual(struct.unpack_from("<I", content, 1648)[0], 40)
        self.assertEqual(struct.unpack_from("<Q", content, 1652)[0], 0x48000000)
        self.assertTrue(content.rstrip(b"\x00"))
        self.assertEqual(receipt["partition_bytes"], len(content))
        with self.assertRaises(ValueError):
            p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg, self.output)

    def test_independent_full_readback(self):
        p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg, self.output)
        result = p25verify.verify(self.output, self.kernel, self.ramdisk, self.dtb)
        self.assertEqual(result["partition_bytes"], 33554432)
        damaged = bytearray(self.output.read_bytes())
        damaged[-1] = 1
        self.output.write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "NONZERO_PARTITION_PADDING"):
            p25verify.verify(self.output, self.kernel, self.ramdisk, self.dtb)

    def test_rejects_invalid_kernel(self):
        self.kernel.write_bytes(b"not gzip")
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP"):
            p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg, self.output)

    def test_rejects_malformed_dtb(self):
        self.dtb.write_bytes(b"not a device tree")
        with self.assertRaisesRegex(ValueError, "DTB_MAGIC"):
            p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg, self.output)

    def test_no_implicit_hardware_addresses(self):
        self.cfg.write_text("{}")
        with self.assertRaisesRegex(ValueError, "CONFIG_KEYS"):
            p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg, self.output)

if __name__ == "__main__":
    unittest.main()
