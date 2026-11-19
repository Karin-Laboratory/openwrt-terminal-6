# SPDX-License-Identifier: MIT
"""Reference-profile checks must never become an automatic rights approval."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pack = load("tools/boot/pack_p25_unsigned_v2.py", "ref_pack")
audit = load("tools/boot/audit_p25_reference_v2.py", "ref_audit")
verify = load("tools/boot/verify_p25_profile_provenance.py", "ref_profile")


class ProfileProvenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name)
        self.kernel = home / "Image.gz"
        self.ramdisk = home / "empty-ramdisk"
        self.dtb = home / "synthetic-public-dtb"
        self.prefix = home / "owner-private-prefix"
        self.config = home / "candidate-config.json"
        self.image = home / "ref.p25"
        self.receipt = home / "owner-reference-audit.json"
        kernel = bytearray(256)
        kernel[56:60] = b"ARM\x64"
        self.kernel.write_bytes(gzip.compress(kernel, mtime=0))
        self.ramdisk.write_bytes(b"")
        self.dtb.write_bytes(bytes.fromhex("d00dfeed") +
                             struct.pack(">I", 40) + bytes(32))
        self.prefix.write_bytes(b"fictional-prefix-test".ljust(64, b"~"))
        self.cfg = {
            "kernel_addr": "0x0", "ramdisk_addr": "0x01000000",
            "second_addr": "0x00f00000", "tags_addr": "0x0",
            "dtb_addr": "0x01f00000", "page_size": 2048,
            "os_version": 131072, "name": "mt6990",
            "cmdline": "bootopt=64S3,32N2,64N2 init_debug=4",
            "ramdisk_mode": "kernel_embedded", "dtb_prefix_bytes": 64,
            "dtb_prefix_sha256":
                hashlib.sha256(self.prefix.read_bytes()).hexdigest(),
        }
        self.config.write_text(json.dumps(self.cfg))
        pack.build(self.kernel, self.ramdisk, self.dtb, self.config,
                   self.image, self.prefix)
        receipt = audit.inspect(
            self.image, hashlib.sha256(self.image.read_bytes()).hexdigest(),
            self.prefix)
        self.receipt.write_text(json.dumps(receipt))

    def do_verify(self):
        return verify.verify(self.config, self.prefix, self.receipt, self.dtb)

    def test_matching_field_profile_only_not_rights(self):
        result = self.do_verify()
        self.assertEqual(result["status"],
                         "REFERENCE_PROFILE_FIELDS_AND_PREFIX_MATCH_NOT_BOOT_OR_RIGHTS")
        self.assertFalse(result["hardware_boot_approved"])
        self.assertFalse(result["redistribution_approved"])
        self.assertFalse(result["candidate_differs_from_reference_bare_dtb"])

    def test_reject_altered_load_address(self):
        self.cfg["kernel_addr"] = "0x00001000"
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, "FIELD_MISMATCH_KERNEL_ADDR"):
            self.do_verify()

    def test_reject_altered_cmdline(self):
        self.cfg["cmdline"] = "console=ttyS0"
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, "FIELD_MISMATCH_CMDLINE"):
            self.do_verify()

    def test_reject_altered_or_unreviewed_prefix(self):
        self.prefix.write_bytes(b"other".ljust(64, b"!"))
        with self.assertRaisesRegex(ValueError, "PREFIX_NOT_IDENTICAL_TO_REFERENCE"):
            self.do_verify()
        self.prefix.write_bytes(b"fictional-prefix-test".ljust(64, b"~"))
        obj = json.loads(self.receipt.read_text())
        obj["reference_prefix"]["rights"] = "APPROVED"
        self.receipt.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "REFERENCE_PREFIX_SCOPE"):
            self.do_verify()

    def test_public_dtb_modified_is_recorded_not_approved(self):
        body = bytearray(self.dtb.read_bytes())
        body[-1] = 1
        self.dtb.write_bytes(body)
        result = self.do_verify()
        self.assertTrue(result["candidate_differs_from_reference_bare_dtb"])
        self.assertFalse(result["hardware_boot_approved"])


if __name__ == "__main__":
    unittest.main()
