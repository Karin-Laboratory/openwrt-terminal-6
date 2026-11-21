# SPDX-License-Identifier: MIT
import gzip
import hashlib
import importlib.util
import json
from unittest import mock
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
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
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

    def test_receipt_is_private_and_matches_image(self):
        receipt = self.build()
        receipt_path = self.output.with_name(self.output.name + ".json")
        self.assertEqual(receipt_path.stat().st_mode & 0o777, 0o600)
        on_disk = json.loads(receipt_path.read_text())
        self.assertEqual(on_disk, receipt)
        self.assertEqual(on_disk["p25_sha256"],
                         hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(self.verify()["partition_bytes"], 33554432)

    def test_oversized_section_rejected_before_image_creation(self):
        # A sparse file avoids allocating or storing a large test fixture.
        with self.dtb.open("wb") as stream:
            stream.truncate(p25.PARTITION + 1)
        with self.assertRaisesRegex(ValueError, "INPUT_TOO_LARGE"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_name(self.output.name + ".json").exists())

    def test_oversized_config_rejected_without_output(self):
        self.cfg.write_bytes(b" " * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, "CONFIG_TOO_LARGE"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_name(self.output.name + ".json").exists())

    def test_stale_receipt_blocks_image_creation(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        receipt_path.write_text("existing evidence")
        with self.assertRaisesRegex(ValueError, "RECEIPT_EXISTS"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertEqual(receipt_path.read_text(), "existing evidence")

    def test_concurrent_receipt_creation_is_preserved(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        real_open = p25.os.open
        marker = "concurrent producer evidence"

        def competing_receipt(path, flags, *args, **kwargs):
            if str(path) == str(receipt_path):
                receipt_path.write_text(marker)
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(p25.os, "open", side_effect=competing_receipt):
            with self.assertRaises(FileExistsError):
                self.build()
        self.assertFalse(self.output.exists())
        self.assertEqual(receipt_path.read_text(), marker)

    def test_image_sync_failure_removes_partial_image(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        with mock.patch.object(p25.os, "fsync",
                               side_effect=OSError("synthetic image sync failure")):
            with self.assertRaisesRegex(OSError, "synthetic image sync failure"):
                self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(receipt_path.exists())

    def test_receipt_sync_failure_removes_both_outputs(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        original_fsync = p25.os.fsync
        calls = 0

        def fail_second_sync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic receipt sync failure")
            return original_fsync(fd)

        with mock.patch.object(p25.os, "fsync", side_effect=fail_second_sync):
            with self.assertRaisesRegex(OSError, "synthetic receipt sync failure"):
                self.build()
        self.assertEqual(calls, 3)  # includes rollback directory fsync
        self.assertFalse(self.output.exists())
        self.assertFalse(receipt_path.exists())
    def test_directory_sync_failure_rolls_back_and_syncs_removal(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        original_fsync = p25.os.fsync
        calls = 0

        def fail_initial_directory_sync(fd):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("synthetic directory sync failure")
            return original_fsync(fd)

        with mock.patch.object(p25.os, "fsync", side_effect=fail_initial_directory_sync):
            with self.assertRaisesRegex(OSError, "synthetic directory sync failure"):
                self.build()
        self.assertEqual(calls, 4)  # rollback directory sync is mandatory
        self.assertFalse(self.output.exists())
        self.assertFalse(receipt_path.exists())

    def test_rollback_sync_failure_preserves_original_error(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        original_fsync = p25.os.fsync
        calls = 0

        def fail_receipt_and_cleanup_sync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("original receipt failure")
            if calls == 3:
                raise OSError("rollback sync failure")
            return original_fsync(fd)

        with mock.patch.object(p25.os, "fsync",
                               side_effect=fail_receipt_and_cleanup_sync):
            with self.assertRaisesRegex(OSError, "original receipt failure") as caught:
                self.build()
        self.assertEqual(calls, 3)
        self.assertTrue(any("rollback sync failure" in note
                            for note in caught.exception.__notes__))
        self.assertFalse(self.output.exists())
        self.assertFalse(receipt_path.exists())

    def test_receipt_open_failure_rolls_back_created_image(self):
        receipt_path = self.output.with_name(self.output.name + ".json")
        real_open = p25.os.open

        def fail_receipt_open(path, flags, *args, **kwargs):
            if str(path) == str(receipt_path):
                raise OSError("synthetic receipt creation failure")
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(p25.os, "open", side_effect=fail_receipt_open):
            with self.assertRaisesRegex(OSError, "synthetic receipt creation failure"):
                self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(receipt_path.exists())

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

    def test_rejects_gzip_expansion_beyond_limit(self):
        image = bytearray(128 * 1024 * 1024 + 1)
        image[56:60] = b"ARM\x64"
        self.kernel.write_bytes(gzip.compress(bytes(image), compresslevel=9, mtime=0))
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP_TOO_LARGE_OR_INCOMPLETE"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_rejects_trailing_gzip_data(self):
        self.kernel.write_bytes(self.kernel.read_bytes() + b"trailing")
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP_TRAILING_DATA"):
            self.build()

    def test_rejects_truncated_gzip_stream(self):
        self.kernel.write_bytes(self.kernel.read_bytes()[:-4])
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP_TOO_LARGE_OR_INCOMPLETE"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_rejects_concatenated_gzip_members(self):
        self.kernel.write_bytes(self.kernel.read_bytes() + gzip.compress(b"extra member", mtime=0))
        with self.assertRaisesRegex(ValueError, "KERNEL_GZIP_TRAILING_DATA"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_rejects_malformed_dtb(self):
        self.dtb.write_bytes(b"not a device tree")
        with self.assertRaisesRegex(ValueError, "DTB_MAGIC"):
            self.build()

    def test_rejects_duplicate_json_config_keys(self):
        # JSON parsers normally keep the last value, making review ambiguous.
        original = self.cfg.read_text()
        self.cfg.write_text(original[:-1] + ', "page_size": 4096}')
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CONFIG_KEY"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_name(self.output.name + ".json").exists())

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
