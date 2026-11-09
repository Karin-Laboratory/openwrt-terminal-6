# SPDX-License-Identifier: MIT
"""P25/P26 intake gate: actual partition bytes, explicit non-bootable status."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.build.check_p25_p26_presign import check


class PairIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.p25, self.p26 = root / "p25", root / "p26"
        self.a, self.b = root / "a.json", root / "b.json"
        for path, length in ((self.p25, 33554432), (self.p26, 134217728)):
            with path.open("wb") as f:
                f.truncate(length)
        self.ra = {
            "format": "aosp-boot-v2-p25-research-receipt-v1",
            "status": "REAL_32M_BYTES_AOSP_V2_STRUCTURE_ONLY_NOT_LK_ACCEPTED",
            "partition_bytes": 33554432,
            "p25_sha256": self.sha(self.p25),
            "metadata_provenance": "synthetic-research-only",
            "header_fields": {"kernel_addr": 0, "tags_addr": 0, "dtb_addr": 0},
            "signed": False, "distributable": False,
            "device_boot_proven": False, "lk_header_and_vendor64_accepted": False,
        }
        self.rb = {"schema": 1, "status": "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK",
                   "partition_bytes": 134217728, "p26_sha256": self.sha(self.p26),
                   "signed": False, "hardware": "NONE", "public_binary": False}
        self.save()

    @staticmethod
    def sha(path):
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def save(self):
        self.a.write_text(json.dumps(self.ra))
        self.b.write_text(json.dumps(self.rb))

    def verify(self):
        return check(self.p25, self.a, self.p26, self.b)

    def test_hash_verified_but_synthetic_not_signer_ready(self):
        r = self.verify()
        self.assertEqual(r["pair_integrity"], "PASS_RECEIPT_HASHES_ONLY")
        self.assertEqual(r["signing_readiness"], "BLOCKED_SYNTHETIC_OR_UNREVIEWED_P25_METADATA")
        self.assertFalse(r["safe_to_flash"])

    def test_reviewed_nonzero_still_not_lk_proven(self):
        self.ra["metadata_provenance"] = "owner-reviewed-public-metadata"
        self.ra["header_fields"] = {"kernel_addr": 0x40080000,
                                    "tags_addr": 0x40000100, "dtb_addr": 0x48000000}
        self.save()
        self.assertEqual(self.verify()["signing_readiness"],
                         "BLOCKED_LK_VENDOR64_AND_HARDWARE_ACCEPTANCE_UNPROVEN")

    def test_reject_tampered_partition_and_lying_receipt(self):
        with self.p26.open("r+b") as f:
            f.seek(11000000)
            f.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.verify()
        self.rb["p26_sha256"] = self.sha(self.p26)
        self.ra["signed"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "MISLEADING_P25"):
            self.verify()

    def test_reject_wrong_size_and_symlink(self):
        self.p26.write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "PARTITION_LENGTH"):
            self.verify()
        self.p26.unlink()
        self.p26.symlink_to(self.p25)
        with self.assertRaisesRegex(ValueError, "SYMLINK"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
