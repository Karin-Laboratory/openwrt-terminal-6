# SPDX-License-Identifier: MIT
"""Host-only rejection tests of unsigned pair receipt identity gates."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/build/verify_unsigned_pair.py"
spec = importlib.util.spec_from_file_location("verify_unsigned_pair", MODULE)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)



def newc(files):
    out = bytearray()
    for name, content, mode in files + [("TRAILER!!!", b"", 0)]:
        name = name.encode() + b"\\0"
        fields = [0, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, len(name), 0]
        out.extend(b"070701" + b"".join(f"{v:08x}".encode() for v in fields))
        out.extend(name)
        out.extend(bytes((-len(out)) % 4))
        out.extend(content)
        out.extend(bytes((-len(out)) % 4))
    return bytes(out)


class PairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.p25 = self.base / "p25"
        self.p26 = self.base / "p26"
        self.p25.write_bytes(b"boot-v2-test" + bytes(64 - len(b"boot-v2-test")))
        self.p26.write_bytes(b"hsqs-test" + bytes(128 - len(b"hsqs-test")))
        self.parts = [self.base / f for f in ("kernel", "ramdisk", "dtb", "cfg")]
        for part in self.parts:
            part.write_text("synthetic")
        self.producer = self.base / "producer.json"
        self.independent = self.base / "independent.json"
        self.out = self.base / "pair.json"
        self.cpio = self.base / "initramfs.cpio"
        self.cpio.write_bytes(b"newc" + pair.digest(self.p26).encode("ascii") +
                              b"  /dev/mmcblk0p26" + b"TRAILER!!!")
        self.producer.write_text(json.dumps({
            "schema": 1, "status": "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK",
            "signed": False, "hardware": "NONE",
            "partition_bytes": 128,
            "p26_sha256": pair.digest(self.p26),
            "squashfs_sha256": "f" * 64, "squashfs_bytes": 9
        }))
        self.update_independent()
        patches = [patch.object(pair, "P25_BYTES", 64),
                   patch.object(pair, "P26_BYTES", 128)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def update_independent(self):
        prod = json.loads(self.producer.read_text())
        self.independent.write_text(json.dumps({
            "schema": 1, "status": "P26_INDEPENDENT_FS_READBACK_VERIFIED",
            "signed": False, "hardware": "NONE", "partition_bytes": 128,
            "verification": "INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA",
            "p26_sha256": prod["p26_sha256"],
            "producer_receipt_sha256": pair.digest(self.producer),
            "squashfs_sha256": prod["squashfs_sha256"],
            "squashfs_bytes": prod["squashfs_bytes"]
        }))

    def fake_p25(self, *args):
        return {"partition_bytes": 64, "p25_sha256": pair.digest(self.p25)}

    def run_pair(self):
        return pair.verify_pair(self.p25, *self.parts, self.p26,
                                self.producer, self.independent,
                                self.cpio, self.out, self.fake_p25)

    def test_pair_identity_pass_and_refuse_overwrite(self):
        evidence = self.run_pair()
        self.assertEqual(evidence["status"], "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED")
        self.assertEqual(json.loads(self.out.read_text())["p26_sha256"],
                         pair.digest(self.p26))
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            self.run_pair()

    def test_mismatched_initramfs_p26_hash_rejected(self):
        self.cpio.write_bytes(newc([("etc/p26.sha256",
            b"0" * 64 + b"  /dev/mmcblk0p26", 0o100644)]))
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_BINDING"):
            self.run_pair()
        self.assertFalse(self.out.exists())

    def test_hash_only_in_symlink_rejected(self):
        self.cpio.write_bytes(newc([("etc/p26.sha256",
            (pair.digest(self.p26) + "  /dev/mmcblk0p26").encode(), 0o120777)]))
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_BINDING"):
            self.run_pair()

    def test_malformed_cpio_rejected(self):
        self.cpio.write_bytes(b"newc" + pair.digest(self.p26).encode() +
                              b"  /dev/mmcblk0p26")
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_CPIO_FORMAT"):
            self.run_pair()

    def test_changed_p26_rejected(self):
        image = bytearray(self.p26.read_bytes())
        image[-1] = 1
        self.p26.write_bytes(image)
        with self.assertRaisesRegex(ValueError, "P26_IMAGE_IDENTITY"):
            self.run_pair()
        self.assertFalse(self.out.exists())

    def test_wrong_producer_receipt_rejected(self):
        doc = json.loads(self.producer.read_text())
        doc["p26_sha256"] = "0" * 64
        self.producer.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "P26_IMAGE_IDENTITY|P26_RECEIPT_IDENTITY"):
            self.run_pair()

    def test_false_independent_status_rejected(self):
        doc = json.loads(self.independent.read_text())
        doc["status"] = "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK"
        self.independent.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "P26_NOT_INDEPENDENTLY_VERIFIED"):
            self.run_pair()

    def test_p25_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "P25_IDENTITY"):
            pair.verify_pair(self.p25, *self.parts, self.p26, self.producer,
                             self.independent, self.cpio, self.out,
                             lambda *args: {"partition_bytes": 64,
                                            "p25_sha256": "0" * 64})


if __name__ == "__main__":
    unittest.main()
