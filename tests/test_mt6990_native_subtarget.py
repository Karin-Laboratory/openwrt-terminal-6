# SPDX-License-Identifier: MIT
"""Synthetic source-only staging checks. No downloads, signer or device."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "native_mt6990", ROOT / "tools/build/stage_mt6990_subtarget.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
UPSTREAM = """# Copyright (c) 2015 OpenWrt.org
include $(TOPDIR)/rules.mk
ARCH:=arm
BOARD:=mediatek
BOARDNAME:=MediaTek ARM
SUBTARGETS:=filogic mt7622 mt7623 mt7629
FEATURES:=dt-overlay emmc fpu gpio nand pci pcie rootfs-part separate_ramdisk squashfs usb
KERNEL_PATCHVER:=6.18
include $(INCLUDE_DIR)/target.mk
DEFAULT_PACKAGES += \\
\tkmod-leds-gpio kmod-gpio-button-hotplug
$(eval $(call BuildTarget))
"""


class TargetStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / "openwrt"
        self.makefile = self.tree / "target/linux/mediatek/Makefile"
        self.makefile.parent.mkdir(parents=True)
        self.makefile.write_text(UPSTREAM)
        self.report = self.root / "report.json"
        self.templates = self.root / "templates"
        shutil.copytree(mod.TEMPLATES, self.templates)

    def apply(self):
        with mock.patch.object(mod, "git", side_effect=lambda _, *args:
                               mod.OPENWRT_PIN if args[0] == "rev-parse" else ""):
            return mod.stage(self.tree, self.report, self.templates)

    def test_source_only_staging(self):
        result = self.apply()
        self.assertEqual(result["status"], "MT6990_NATIVE_OPENWRT_SOURCE_SUBTARGET_STAGED")
        self.assertIn(mod.NEW_SUBTARGETS, self.makefile.read_text())
        self.assertIn(mod.MT6990_PARENT_DEFAULTS, self.makefile.read_text())
        self.assertIn("DEVICE_TYPE:=basic", (self.tree / mod.TARGET).read_text())
        self.assertEqual(set(result["files"]), {mod.TARGET, mod.IMAGE, mod.CONFIG})
        self.assertFalse(result["signed"])
        self.assertEqual(result["firmware_outputs"], "NONE")
        self.assertNotIn("define Device/", (self.tree / mod.IMAGE).read_text())
        self.assertIn("CONFIG_SQUASHFS_XZ=y", (self.tree / mod.CONFIG).read_text())
        staged_config = (self.tree / mod.CONFIG).read_text()
        for choice in ("CONFIG_ARM64_4K_PAGES=y", "CONFIG_ARM64_VA_BITS_48=y",
                       "CONFIG_ARM64_PA_BITS_48=y", "CONFIG_CPU_LITTLE_ENDIAN=y"):
            self.assertIn(choice, staged_config)
        # Kbuild syncconfig must not ask interactively about newly
        # discovered alternatives of already selected ARM64 choices.
        for choice in ("ARM64_16K_PAGES", "ARM64_64K_PAGES",
                       "ARM64_VA_BITS_39", "ARM64_VA_BITS_52"):
            self.assertIn(f"# CONFIG_{choice} is not set", staged_config)
        self.assertTrue(json.loads(self.report.read_text())["not_verified"])

    def test_wrong_source_commit_rejected_before_mutation(self):
        with mock.patch.object(mod, "git", return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "pinned and clean"):
                mod.stage(self.tree, self.report, self.templates)
        self.assertFalse(self.report.exists())
        self.assertEqual(self.makefile.read_text(), UPSTREAM)

    def test_dirty_tree_rejected_before_mutation(self):
        def fake_git(_root, *args):
            return mod.OPENWRT_PIN if args[0] == "rev-parse" else " M Makefile"
        with mock.patch.object(mod, "git", side_effect=fake_git):
            with self.assertRaisesRegex(ValueError, "pinned and clean"):
                mod.stage(self.tree, self.report, self.templates)
        self.assertEqual(self.makefile.read_text(), UPSTREAM)

    def test_unknown_upstream_source_rejected(self):
        self.makefile.write_text(UPSTREAM.replace("KERNEL_PATCHVER:=6.18",
                                                  "KERNEL_PATCHVER:=6.17"))
        with self.assertRaisesRegex(ValueError, "unexpected pinned"):
            self.apply()
        self.assertFalse(self.report.exists())

    def test_parent_kernel_defaults_mismatch_rejected(self):
        self.makefile.write_text(UPSTREAM.replace("kmod-gpio-button-hotplug", "kmod-other"))
        with self.assertRaisesRegex(ValueError, "unexpected pinned"):
            self.apply()
        self.assertEqual(self.makefile.read_text(), UPSTREAM.replace("kmod-gpio-button-hotplug", "kmod-other"))
        self.assertFalse(self.report.exists())

    def test_installer_device_definition_rejected(self):
        with (self.templates / "mt6990.mk").open("a") as f:
            f.write("\ndefine Device/flashable\n")
        with self.assertRaisesRegex(ValueError, "Device profile forbidden"):
            self.apply()
        self.assertEqual(self.makefile.read_text(), UPSTREAM)

    def test_existing_target_never_overwritten(self):
        path = self.tree / mod.TARGET
        path.parent.mkdir(parents=True)
        path.write_text("PRESERVE\n")
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            self.apply()
        self.assertEqual(path.read_text(), "PRESERVE\n")
        self.assertEqual(self.makefile.read_text(), UPSTREAM)

    def test_template_symlink_rejected(self):
        path = self.templates / "target.mk"
        original = self.root / "original.mk"
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "missing or unsafe source template"):
            self.apply()
        self.assertFalse(self.report.exists())

    def test_existing_report_rejected(self):
        self.report.write_text("PRESERVE\n")
        with self.assertRaisesRegex(ValueError, "report path"):
            self.apply()
        self.assertEqual(self.report.read_text(), "PRESERVE\n")
        self.assertEqual(self.makefile.read_text(), UPSTREAM)


if __name__ == "__main__":
    unittest.main()
