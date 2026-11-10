# SPDX-License-Identifier: MIT
"""Synthetic local-only boot-v2 DTB-container classifiers. No private bytes."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "tools/boot/classify_p25_dtb_prefix.py"
PACKER = ROOT / "tools/boot/pack_p25_unsigned_v2.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


classifier = load(CLASSIFIER, "prefix_classifier")
packer = load(PACKER, "prefix_synthetic_packer")


class PrefixClassificationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.kernel = self.home / "kernel.gz"
        self.ramdisk = self.home / "empty-ramdisk"
        self.dtb = self.home / "public-synthetic-fdt"
        self.prefix = self.home / "synthetic-prefix"
        self.cfg = self.home / "config.json"
        self.p25 = self.home / "synthetic-reference-p25"
        self.report = self.home / "private-report.json"
        image = bytearray(256)
        image[56:60] = b"ARM\\x64"
        # Assign as real bytes to avoid a literal textual backslash.
        image[56:60] = bytes([65, 82, 77, 100])
        self.kernel.write_bytes(gzip.compress(bytes(image), mtime=0))
        self.ramdisk.write_bytes(b"")
        self.dtb.write_bytes(bytes.fromhex("d00dfeed") + struct.pack(">I", 40) + bytes(32))

    def make(self, prefix):
        self.prefix.write_bytes(prefix)
        cfg = {
            "kernel_addr": "0x0", "ramdisk_addr": "0x01000000",
            "second_addr": "0x00f00000", "tags_addr": "0x0",
            "dtb_addr": "0x01f00000", "page_size": 2048,
            "os_version": 131072, "name": "mt6990",
            "cmdline": "bootopt=64S3,32N2,64N2 init_debug=4",
            "ramdisk_mode": "kernel_embedded", "dtb_prefix_bytes": 64,
            "dtb_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        }
        self.cfg.write_text(json.dumps(cfg))
        packer.build(self.kernel, self.ramdisk, self.dtb,
                     self.cfg, self.p25, self.prefix)
        return hashlib.sha256(self.p25.read_bytes()).hexdigest()

    def dt_table(self, total=104, dt_size=40):
        header = struct.pack("<8I", 0xd7b7ab1e, total, 32, 32, 1, 32, 2048, 0)
        entry = struct.pack("<8I", dt_size, 64, 0, 0, 0, 0, 0, 0)
        return header + entry

    def uimage(self, payload=None):
        if payload is None:
            payload = self.dtb.read_bytes()
        h = bytearray(64)
        struct.pack_into(">I", h, 0, 0x27051956)
        struct.pack_into(">I", h, 12, len(payload))
        struct.pack_into(">I", h, 24, zlib.crc32(payload))
        h[28:32] = bytes([5, 22, 8, 0])
        struct.pack_into(">I", h, 4, zlib.crc32(h))
        return bytes(h)

    def test_exact_32_plus_32_table(self):
        digest = self.make(self.dt_table())
        result = classifier.inspect(self.p25, digest)
        self.assertEqual(result["prefix_format"],
                         "AOSP_SINGLE_ENTRY_DT_TABLE_STRUCTURALLY_VALID")
        self.assertTrue(result["android_dt_table"][
            "single_entry_32_plus_32_valid"])
        self.assertFalse(result["redistribution_approved"])

    def test_uimage_requires_both_crcs_and_size(self):
        digest = self.make(self.uimage())
        result = classifier.inspect(self.p25, digest)
        self.assertEqual(result["prefix_format"],
                         "UBOOT_LEGACY_UIMAGE_STRUCTURALLY_VALID")
        self.assertTrue(result["uboot_legacy_image"]["header_crc_matches"])
        self.assertTrue(result["uboot_legacy_image"]["payload_crc_matches"])

    def test_wrong_table_total_does_not_classify(self):
        digest = self.make(self.dt_table(total=111))
        result = classifier.inspect(self.p25, digest)
        self.assertEqual(result["prefix_format"],
                         "UNCLASSIFIED_PREFIX_NO_FORMAT_PROVEN")
        self.assertEqual(result["diagnostic"],
                         "DT_TABLE_MAGIC_PRESENT_BUT_FIELDS_OR_BOUNDS_INVALID")

    def test_stale_uimage_data_crc_does_not_classify(self):
        damaged = bytearray(self.uimage())
        # Make a *valid header CRC* which signs an intentionally wrong
        # payload CRC so that magic-only parsing would be a false positive.
        struct.pack_into(">I", damaged, 24, 0)
        struct.pack_into(">I", damaged, 4, 0)
        struct.pack_into(">I", damaged, 4, zlib.crc32(damaged))
        digest = self.make(damaged)
        result = classifier.inspect(self.p25, digest)
        self.assertFalse(result["uboot_legacy_image"]["payload_crc_matches"])
        self.assertEqual(result["diagnostic"],
                         "UIMAGE_MAGIC_PRESENT_BUT_CRC_OR_SIZE_INVALID")

    def test_opaque_64_byte_prefix_is_not_falsely_recognized(self):
        digest = self.make(b"not-a-header".ljust(64, b"!"))
        result = classifier.inspect(self.p25, digest)
        self.assertEqual(result["prefix_format"],
                         "UNCLASSIFIED_PREFIX_NO_FORMAT_PROVEN")
        self.assertFalse(result["format_proves_lk_consumption"])

    def test_owner_private_cli_does_not_export_bytes_or_overwrite(self):
        digest = self.make(self.dt_table())
        args = [sys.executable, str(CLASSIFIER),
                "--reference", str(self.p25),
                "--expected-sha256", digest,
                "--private-report", str(self.report)]
        first = subprocess.run(args, capture_output=True, text=True, check=True)
        self.assertEqual(stat.S_IMODE(self.report.stat().st_mode), 0o600)
        self.assertNotIn("d7b7ab1e", first.stdout)
        receipt = json.loads(self.report.read_text())
        self.assertFalse(receipt["prefix_or_identifier_bytes_exported"])
        self.assertFalse(receipt["independent_header_generation_approved"])
        second = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("PRIVATE_REPORT_MUST_BE_NEW", second.stderr)


if __name__ == "__main__":
    unittest.main()
