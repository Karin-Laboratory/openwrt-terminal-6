# SPDX-License-Identifier: MIT
"""QEMU-only virtio p26 archive tests use synthetic 4KiB source; no device."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from tools.boot import build_p26_p44_initramfs as producer
from tools.boot import build_p26_qemu_virt_fixture as fixture
from tools.boot import verify_p26_qemu_virt_fixture as verifier


class SyntheticVirtioBootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.rootfs = self.d / "rootfs"
        for path in ("bin", "sbin", "etc"):
            (self.rootfs / path).mkdir(parents=True)
        (self.rootfs / "bin/busybox").write_bytes(b"target fixture binary")
        (self.rootfs / "sbin/procd").write_bytes(b"target fixture procd")
        (self.rootfs / "sbin/init").symlink_to("procd")
        (self.rootfs / "etc/preinit").write_bytes(b"#!/bin/sh\nexit 0\n")
        self.p26 = self.d / "p26"
        self.p26.write_bytes(b"SYNTHETIC_ONLY" + b"\0" * (4096 - 14))
        self.p26_receipt = self.d / "p26.json"
        self.p26_receipt.write_text(json.dumps({
            "partition_bytes": 4096,
            "p26_sha256": hashlib.sha256(self.p26.read_bytes()).hexdigest()}))
        self.original = self.d / "original.cpio"
        self.original_receipt = self.d / "original.json"
        self.output = self.d / "qemu-only.cpio"
        self.receipt = self.d / "qemu-only.json"

    def build(self):
        with mock.patch.object(producer, "PARTITION_BYTES", 4096):
            producer.package(self.rootfs, self.p26, self.p26_receipt,
                             self.original, self.original_receipt)
            return fixture.build(self.original, self.original_receipt,
                                 self.p26, self.p26_receipt, self.output, self.receipt)

    def verify(self):
        with mock.patch.object(producer, "PARTITION_BYTES", 4096):
            return verifier.verify(self.original, self.output, self.receipt,
                                   self.p26, self.p26_receipt)

    def test_real_newc_fixture_provenance_independent_readback(self):
        data = self.build()
        self.assertEqual(data["virtual_block"], "/dev/vda")
        self.assertFalse(data["owner_p44_authorization"])
        self.assertFalse(data["air6_hardware_proven"])
        self.assertFalse(data["signed_or_installable"])
        result = self.verify()
        self.assertEqual(result["status"], "QEMU_VIRTIO_SYNTHETIC_P26_CPIO_INDEPENDENT_READBACK_PASS")
        self.assertFalse(result["hardware_boot_proven"])

    def test_original_air6_init_unchanged(self):
        self.build()
        self.assertEqual(producer.BOOT_SCRIPT.read_bytes().count(b"/dev/mmcblk0p26"), 1)
        self.assertNotEqual(self.original.read_bytes(), self.output.read_bytes())
        self.assertEqual(self.verify()["p26_sha256"],
                         json.loads(self.p26_receipt.read_text())["p26_sha256"])

    def test_tampered_guest_cpio_rejected(self):
        self.build()
        with self.output.open("r+b") as stream:
            stream.seek(170)
            stream.write(b"CHANGED")
        with self.assertRaisesRegex(ValueError, "VIRTIO_READBACK_RECEIPT"):
            self.verify()

    def test_p26_change_invalidates_source_binding(self):
        self.build()
        self.p26.write_bytes(b"DIFFERENT" + b"\0" * (4096 - 9))
        with self.assertRaisesRegex(ValueError, "VIRTIO_READBACK_P26"):
            self.verify()

    def test_never_overwrite_existing_fixture_output(self):
        self.build()
        with mock.patch.object(producer, "PARTITION_BYTES", 4096):
            with self.assertRaisesRegex(ValueError, "QEMU_FIXTURE_OUTPUT_EXISTS"):
                fixture.build(self.original, self.original_receipt,
                              self.p26, self.p26_receipt, self.output, self.receipt)

    def test_original_cpio_receipt_mismatch_rejected(self):
        self.build()
        record = json.loads(self.original_receipt.read_text())
        record["cpio_sha256"] = "0" * 64
        self.original_receipt.write_text(json.dumps(record))
        self.output.unlink()
        self.receipt.unlink()
        with mock.patch.object(producer, "PARTITION_BYTES", 4096):
            with self.assertRaisesRegex(ValueError, "QEMU_FIXTURE_SOURCE_READBACK"):
                fixture.build(self.original, self.original_receipt,
                              self.p26, self.p26_receipt, self.output, self.receipt)


if __name__ == "__main__":
    unittest.main()
