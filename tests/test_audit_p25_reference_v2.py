# SPDX-License-Identifier: MIT
"""Synthetic, host-only audit of a reference boot-v2 image and vendor64."""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools/boot/audit_p25_reference_v2.py"
PACK = ROOT / "tools/boot/pack_p25_unsigned_v2.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit = load(AUDIT, "audit_ref_p25")
pack = load(PACK, "synthetic_p25_packer")


class P25ReferenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.kernel = self.root / "Image.gz"
        self.dtb = self.root / "board.dtb"
        self.ramdisk = self.root / "empty"
        self.prefix = self.root / "private-prefix"
        self.config = self.root / "config.json"
        self.p25 = self.root / "reference.p25"
        self.receipt = self.root / "receipt.json"
        image = bytearray(256)
        image[56:60] = b"ARM\x64"
        self.kernel.write_bytes(gzip.compress(bytes(image), mtime=0))
        self.dtb.write_bytes(bytes.fromhex("d00dfeed") +
                             struct.pack(">I", 40) + bytes(32))
        self.ramdisk.write_bytes(b"")
        self.prefix.write_bytes(b"synthetic-test-only".ljust(64, b"_"))
        cfg = {
            "kernel_addr": "0x0", "ramdisk_addr": "0x01000000",
            "second_addr": "0x00f00000", "tags_addr": "0x0",
            "dtb_addr": "0x01f00000", "page_size": 2048,
            "os_version": 131072, "name": "mt6990",
            "cmdline": "bootopt=64S3,32N2,64N2 init_debug=4",
            "ramdisk_mode": "kernel_embedded", "dtb_prefix_bytes": 64,
            "dtb_prefix_sha256": hashlib.sha256(
                self.prefix.read_bytes()).hexdigest(),
        }
        self.config.write_text(json.dumps(cfg))
        pack.build(self.kernel, self.ramdisk, self.dtb, self.config,
                   self.p25, self.prefix)

    def expected(self):
        return hashlib.sha256(self.p25.read_bytes()).hexdigest()

    def test_owner_supplied_prefix_matches_without_binary_export(self):
        outcome = audit.inspect(self.p25, self.expected(), self.prefix)
        self.assertEqual(outcome["status"],
                         "PRIVATE_REFERENCE_LAYOUT_VERIFIED_NOT_LICENSED")
        self.assertEqual(outcome["android_header"]["page_size"], 2048)
        self.assertEqual(outcome["android_header"]["ramdisk_size"], 0)
        self.assertEqual(outcome["android_header"]["name"], "mt6990")
        self.assertEqual(outcome["reference_prefix"]["bytes"], 64)
        self.assertTrue(outcome["reference_prefix"][
            "independently_supplied_candidate_matches"])
        self.assertEqual(outcome["reference_prefix"]["rights"], "UNVERIFIED")
        self.assertFalse(outcome["public_manufacture_configuration_approved"])
        self.assertFalse(outcome["binary_or_prefix_bytes_exported"])

    def test_signed_tail_does_not_invalidate_boot_layout_audit(self):
        content = bytearray(self.p25.read_bytes())
        content[-1] = 1  # private signer may use reserved end-of-partition data
        self.p25.write_bytes(content)
        result = audit.inspect(self.p25, self.expected())
        self.assertFalse(result["reference_prefix"][
            "independently_supplied_candidate_matches"])

    def test_reject_wrong_expected_image_hash(self):
        with self.assertRaisesRegex(ValueError, "REFERENCE_SHA_MISMATCH"):
            audit.inspect(self.p25, "0" * 64)

    def test_reject_wrong_vendor_prefix(self):
        self.prefix.write_bytes(b"changed".ljust(64, b"?"))
        with self.assertRaisesRegex(ValueError, "PREFIX_NOT_FROM_REFERENCE"):
            audit.inspect(self.p25, self.expected(), self.prefix)

    def test_reject_tampered_fdt_offset(self):
        content = bytearray(self.p25.read_bytes())
        # synthetic kernel has one page; DTB section is the next page
        dtb_section_start = 2048 * 2
        content[dtb_section_start + 64] = 0
        self.p25.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "VENDOR64_FDT_OFFSET"):
            audit.inspect(self.p25, self.expected())

    def test_reject_tampered_boot_id(self):
        content = bytearray(self.p25.read_bytes())
        content[576] ^= 0x40
        self.p25.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "BOOT_ID"):
            audit.inspect(self.p25, self.expected())

    def test_private_cli_receipt_is_0600_and_no_overwrite(self):
        argv = [sys.executable, str(AUDIT), "--reference", str(self.p25),
                "--expected-sha256", self.expected(), "--candidate-prefix",
                str(self.prefix), "--private-receipt", str(self.receipt)]
        subprocess.run(argv, check=True, capture_output=True, text=True)
        self.assertEqual(stat.S_IMODE(self.receipt.stat().st_mode), 0o600)
        self.assertFalse(json.loads(self.receipt.read_text())[
            "public_manufacture_configuration_approved"])
        again = subprocess.run(argv, capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("RECEIPT_OUTPUT_NOT_FRESH_PRIVATE", again.stderr)


if __name__ == "__main__":
    unittest.main()
