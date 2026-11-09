# SPDX-License-Identifier: MIT
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.boot import check_p26_p44_kernel as gate


class P26P44KbuildTests(unittest.TestCase):
    def setUp(self):
        self.config = "\n".join(key + "=y" for key in gate.BUILTIN) + "\n"

    def test_realized_kernel_config_has_every_builtin(self):
        res = gate.check_config(self.config)
        self.assertEqual(res["required_builtin"], len(gate.BUILTIN))
        self.assertFalse(res["device_mmc_controller_proven"])

    def test_missing_or_module_squashfs_xz_blocked(self):
        for text in ("CONFIG_SQUASHFS_XZ=m", "# CONFIG_SQUASHFS_XZ is not set"):
            with self.subTest(text=text):
                conf = self.config.replace("CONFIG_SQUASHFS_XZ=y", text)
                with self.assertRaisesRegex(ValueError, "KERNEL_NOT_BUILTIN"):
                    gate.check_config(conf)

    def test_missing_mmc_block_or_overlayfs_blocked(self):
        for opt in ("CONFIG_MMC_BLOCK", "CONFIG_OVERLAY_FS", "CONFIG_EFI_PARTITION"):
            with self.subTest(opt=opt):
                with self.assertRaisesRegex(ValueError, "KERNEL_NOT_BUILTIN"):
                    gate.check_config(self.config.replace(opt + "=y", opt + "=m"))

    def test_duplicate_config_cannot_hide_override(self):
        with self.assertRaisesRegex(ValueError, "BOOT_KCONFIG_DUPLICATE"):
            gate.check_config(self.config + "CONFIG_MMC=n\n")

    def test_real_p26_superblock_xz_compressor_checked(self):
        with tempfile.TemporaryDirectory() as t, patch.object(gate, "P26_BYTES", 4096):
            p = Path(t) / "p26"
            raw = bytearray(4096)
            raw[:4] = b"hsqs"
            struct.pack_into("<H", raw, 20, 4)
            struct.pack_into("<HH", raw, 28, 4, 0)
            struct.pack_into("<Q", raw, 40, 1024)
            p.write_bytes(raw)
            res = gate.check_squashfs_header(p)
            self.assertEqual(res["squashfs_compression"], "xz")
            self.assertFalse(res["device_boot_proven"])
            struct.pack_into("<H", raw, 20, 1)
            p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "NOT_XZ"):
                gate.check_squashfs_header(p)

    def test_bad_magic_and_length_rejected(self):
        with tempfile.TemporaryDirectory() as t, patch.object(gate, "P26_BYTES", 4096):
            p = Path(t) / "p26"
            p.write_bytes(b"X" * 4096)
            with self.assertRaisesRegex(ValueError, "SQUASHFS_MAGIC"):
                gate.check_squashfs_header(p)
            p.write_bytes(b"X" * 4095)
            with self.assertRaisesRegex(ValueError, "PARTITION_BYTES"):
                gate.check_squashfs_header(p)


if __name__ == "__main__":
    unittest.main()
