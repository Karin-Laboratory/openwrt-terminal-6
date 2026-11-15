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
        for part in self.parts[:3]:
            part.write_text("synthetic")
        self.parts[3].write_text(json.dumps({"ramdisk_mode": "kernel_embedded"}))
        self.producer = self.base / "producer.json"
        self.independent = self.base / "independent.json"
        self.out = self.base / "pair.json"
        self.cpio = self.base / "initramfs.cpio"
        self.initramfs_object = self.base / "initramfs_data.o"
        self.vmlinux = self.base / "vmlinux"
        self.image = self.base / "Image"
        for path in (self.initramfs_object, self.vmlinux, self.image):
            path.write_bytes(b"synthetic")
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

    def fake_initramfs(self, *args):
        return {"kernel_image_sha256": "a" * 64}

    def run_pair(self):
        return pair.verify_pair(self.p25, *self.parts, self.p26,
                                self.producer, self.independent,
                                self.cpio, self.initramfs_object,
                                self.vmlinux, self.image, self.out,
                                p25_verify=self.fake_p25,
                                initramfs_verify=self.fake_initramfs)

    def test_pair_identity_pass_and_refuse_overwrite(self):
        evidence = self.run_pair()
        self.assertEqual(evidence["status"], "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED")
        self.assertEqual(json.loads(self.out.read_text())["p26_sha256"],
                         pair.digest(self.p26))
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            self.run_pair()

    def test_receipt_sync_failure_removes_partial_evidence(self):
        # The first fsync targets the receipt file; rollback must sync its
        # parent directory after unlinking the incomplete receipt.
        import os
        real_fsync = os.fsync
        calls = []

        def fail_first_fsync(fd):
            calls.append(fd)
            if len(calls) == 1:
                raise OSError("synthetic receipt sync failure")
            return real_fsync(fd)

        with patch.object(pair.os, "fsync", side_effect=fail_first_fsync):
            with self.assertRaisesRegex(OSError, "synthetic receipt sync failure"):
                self.run_pair()
        self.assertFalse(self.out.exists())
        self.assertGreaterEqual(len(calls), 2)

    def test_directory_sync_failure_removes_receipt(self):
        # File data may be durable while the directory entry is not.
        # The failed parent sync must roll back the newly created receipt.
        import os
        real_fsync = os.fsync
        calls = []

        def fail_directory_sync(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError("synthetic directory sync failure")
            return real_fsync(fd)

        with patch.object(pair.os, "fsync", side_effect=fail_directory_sync):
            with self.assertRaisesRegex(OSError, "synthetic directory sync failure"):
                self.run_pair()
        self.assertFalse(self.out.exists())
        self.assertGreaterEqual(len(calls), 3)

    def test_receipt_json_failure_removes_partial_evidence(self):
        with patch.object(pair.json, "dump", side_effect=OSError("synthetic short write")):
            with self.assertRaisesRegex(OSError, "synthetic short write"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_producer_path_swap_does_not_change_validated_receipt_hash(self):
        # The producer file is replaced after parsing, but the independent
        # receipt must be checked against the originally validated bytes.
        original_bytes = self.producer.read_bytes()
        original_read = pair.read_receipt

        def swap_after_read(path):
            result = original_read(path)
            if path == self.producer:
                self.producer.write_bytes(b'{"replacement": true}')
            return result

        with patch.object(pair, "read_receipt", side_effect=swap_after_read):
            evidence = self.run_pair()
        self.assertEqual(evidence["p26_sha256"], pair.digest(self.p26))
        self.assertEqual(json.loads(self.out.read_text())["p26_sha256"],
                         pair.digest(self.p26))
        self.assertNotEqual(self.producer.read_bytes(), original_bytes)

    def test_mismatched_initramfs_p26_hash_rejected(self):
        self.cpio.write_bytes(b"newc" + b"0" * 64 + b"  /dev/mmcblk0p26")
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_BINDING"):
            self.run_pair()
        self.assertFalse(self.out.exists())

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

    def test_non_object_receipts_fail_closed(self):
        cases = ((self.parts[3], "P25_CONFIG_NOT_OBJECT"),
                 (self.producer, "P26_PRODUCER_NOT_OBJECT"),
                 (self.independent, "P26_ATTESTATION_NOT_OBJECT"))
        for path, marker in cases:
            original = path.read_text()
            for value in ("[]", "null", "true", "42", '"string"'):
                with self.subTest(path=path.name, value=value):
                    path.write_text(value)
                    with self.assertRaisesRegex(ValueError, marker):
                        self.run_pair()
                    self.assertFalse(self.out.exists())
            path.write_text(original)

    def test_duplicate_receipt_keys_fail_closed(self):
        for path in (self.parts[3], self.producer, self.independent):
            with self.subTest(path=path.name):
                original = path.read_text()
                duplicate = '"ramdisk_mode": "kernel_embedded",' if path == self.parts[3] else '"schema": 1,'
                path.write_text(original.replace("{", "{" + duplicate, 1))
                with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                path.write_text(original)

    def test_boolean_integer_fields_fail_closed(self):
        for path, field, marker in (
            (self.producer, "schema", "P26_PRODUCER_STATUS"),
            (self.independent, "schema", "P26_NOT_INDEPENDENTLY_VERIFIED"),
            (self.producer, "partition_bytes", "P26_SIZE"),
            (self.independent, "partition_bytes", "P26_SIZE"),
        ):
            with self.subTest(path=path.name, field=field):
                original = path.read_text()
                data = json.loads(original)
                data[field] = True if field == "schema" else False
                path.write_text(json.dumps(data))
                if path == self.producer:
                    self.update_independent()
                with self.assertRaisesRegex(ValueError, marker):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                path.write_text(original)
                self.update_independent()

    def test_squashfs_boolean_size_rejected(self):
        for value in (True, False, 0, 128):
            with self.subTest(value=value):
                original = json.loads(self.producer.read_text())
                original["squashfs_bytes"] = value
                self.producer.write_text(json.dumps(original))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                original["squashfs_bytes"] = 9
                self.producer.write_text(json.dumps(original))
                self.update_independent()

    def test_invalid_squashfs_size_types_fail_closed(self):
        original = self.producer.read_text()
        for value in (True, False, 0, -1, 128, 129, "9", 9.0):
            with self.subTest(value=value):
                data = json.loads(original)
                data["squashfs_bytes"] = value
                self.producer.write_text(json.dumps(data))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
        self.producer.write_text(original)
        self.update_independent()

    def test_malformed_squashfs_digest_rejected(self):
        original = self.producer.read_text()
        for digest in ("", "f" * 63, "f" * 65, "g" * 64,
                       "F" * 64, 123, True, None):
            with self.subTest(digest=digest):
                data = json.loads(original)
                data["squashfs_sha256"] = digest
                self.producer.write_text(json.dumps(data))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
        self.producer.write_text(original)
        self.update_independent()

    def test_p25_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "P25_IDENTITY"):
            pair.verify_pair(self.p25, *self.parts, self.p26, self.producer,
                             self.independent, self.cpio,
                             self.initramfs_object, self.vmlinux, self.image,
                             self.out,
                             p25_verify=lambda *args: {"partition_bytes": 64,
                                                       "p25_sha256": "0" * 64},
                             initramfs_verify=self.fake_initramfs)


if __name__ == "__main__":
    unittest.main()
