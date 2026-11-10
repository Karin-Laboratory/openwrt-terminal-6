# SPDX-License-Identifier: MIT
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/boot/pack_p25_unsigned_v2.py"
spec = importlib.util.spec_from_file_location("p25", PATH)
p25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p25)
VPATH = PATH.with_name("verify_p25_independent.py")
vspec = importlib.util.spec_from_file_location("p25_verify", VPATH)
p25verify = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(p25verify)


class TestP25BootV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.kernel = root / "Image.gz"
        self.ramdisk = root / "empty-ramdisk"
        self.dtb = root / "board.dtb"
        self.prefix = root / "dtb-prefix.bin"
        self.cfg = root / "config.json"
        self.output = root / "unsigned.p25"
        image = bytearray(256)
        image[56:60] = b"ARM\x64"
        self.kernel.write_bytes(gzip.compress(bytes(image), mtime=0))
        self.ramdisk.write_bytes(b"")
        self.dtb.write_bytes(b"\xd0\x0d\xfe\xed" + struct.pack(">I", 40) + bytes(32))
        self.prefix.write_bytes(b"synthetic-public-format-prefix".ljust(64, b"!"))
        self.config = {
            "kernel_addr": "0x0", "ramdisk_addr": "0x01000000",
            "second_addr": "0x00f00000", "tags_addr": "0x0",
            "dtb_addr": "0x01f00000", "page_size": 2048,
            "os_version": 131072, "name": "mt6990",
            "cmdline": "bootopt=example rdinit=/init",
            "ramdisk_mode": "kernel_embedded",
            "dtb_prefix_bytes": 64,
            "dtb_prefix_sha256": hashlib.sha256(self.prefix.read_bytes()).hexdigest(),
        }
        self.cfg.write_text(json.dumps(self.config))

    def build(self):
        return p25.build(self.kernel, self.ramdisk, self.dtb, self.cfg,
                         self.output, self.prefix)

    def verify(self):
        return p25verify.verify(self.output, self.kernel, self.ramdisk,
                                self.dtb, self.cfg, self.prefix)

    def test_rc14_observed_header_contract_full_partition(self):
        receipt = self.build()
        content = self.output.read_bytes()
        self.assertEqual(len(content), 33554432)
        self.assertEqual(content[:8], b"ANDROID!")
        self.assertEqual(struct.unpack_from("<I", content, 36)[0], 2048)
        self.assertEqual(struct.unpack_from("<I", content, 40)[0], 2)
        self.assertEqual(struct.unpack_from("<I", content, 1644)[0], 1660)
        self.assertEqual(struct.unpack_from("<I", content, 24)[0], 0)
        self.assertEqual(struct.unpack_from("<I", content, 20)[0], 0x01000000)
        self.assertEqual(struct.unpack_from("<I", content, 1648)[0], 104)
        self.assertEqual(struct.unpack_from("<Q", content, 1652)[0], 0x01f00000)
        self.assertEqual(receipt["ramdisk_mode"], "kernel_embedded")
        self.assertEqual(receipt["partition_bytes"], len(content))
        self.assertEqual(receipt["dtb_section_prefix_sha256"], self.config["dtb_prefix_sha256"])
        self.assertEqual(self.verify()["partition_bytes"], len(content))
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            self.build()

    def test_independent_full_readback_rejects_nonzero_tail(self):
        self.build()
        damaged = bytearray(self.output.read_bytes())
        damaged[-1] = 1
        self.output.write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "NONZERO_PARTITION_PADDING"):
            self.verify()

    def test_rejects_modified_header_cmdline(self):
        self.build()
        damaged = bytearray(self.output.read_bytes())
        damaged[64] ^= 1
        self.output.write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "CONFIG_CMDLINE_PRIMARY"):
            self.verify()

    def test_rejects_modified_header_address(self):
        self.build()
        damaged = bytearray(self.output.read_bytes())
        damaged[12] ^= 4
        self.output.write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "CONFIG_LOAD_ADDRESSES"):
            self.verify()

    def test_rejects_modified_config_after_manufacture(self):
        self.build()
        changed = dict(self.config, cmdline="console=ttyS0")
        self.cfg.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "CONFIG_CMDLINE_PRIMARY"):
            self.verify()

    def test_rejects_nonempty_ramdisk_when_initramfs_is_kernel_embedded(self):
        self.ramdisk.write_bytes(gzip.compress(b"duplicate initramfs"))
        with self.assertRaisesRegex(ValueError, "EXTERNAL_RAMDISK_MUST_BE_EMPTY"):
            self.build()

    def test_rejects_unpinned_or_wrong_dtb_prefix(self):
        self.prefix.write_bytes(b"changed".ljust(64, b"?"))
        with self.assertRaisesRegex(ValueError, "DTB_SECTION_PREFIX_SHA256"):
            self.build()

    def test_rejects_invalid_kernel_gzip_and_architecture(self):
        self.kernel.write_bytes(gzip.compress(b"not an arm64 image"))
        with self.assertRaisesRegex(ValueError, "KERNEL_NOT_ARM64_IMAGE"):
            self.build()
        self.kernel.write_bytes(b"not gzip")
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP_REQUIRED"):
            self.build()

    def test_rejects_malformed_dtb(self):
        self.dtb.write_bytes(b"not a device tree")
        with self.assertRaisesRegex(ValueError, "DTB_MAGIC"):
            self.build()

    def test_rejects_unconfigured_hardware_values(self):
        self.cfg.write_text("{}")
        with self.assertRaisesRegex(ValueError, "CONFIG_KEYS"):
            self.build()

    def test_rejects_invalid_page_size(self):
        self.config["page_size"] = 3000
        self.cfg.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, "PAGE_SIZE"):
            self.build()


if __name__ == "__main__":
    unittest.main()
