#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only negative and deterministic acceptance tests for p26 staging."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/build/pack_p26_rootfs.py"
spec = importlib.util.spec_from_file_location("pack_p26_rootfs", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class P26PackerTests(unittest.TestCase):
    def make_root(self, root):
        for name in mod.REQUIRED:
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("test")
        (root / "etc/shadow").write_text("root:!:0:0:99999:7:::\n")

    def test_missing_service_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "MISSING_"):
                mod.check_tree(Path(d))

    def test_minimal_safe_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            self.assertTrue(mod.check_tree(root))

    def test_required_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            external = Path(d) / "host"
            external.mkdir()
            (external / "dropbear").write_text("host secret")
            (root / "usr/sbin/dropbear").unlink()
            (root / "usr/sbin").rmdir()
            (root / "usr/sbin").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "REQUIRED_PARENT_SYMLINK"):
                mod.check_tree(root)

    def test_forbidden_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            outside = Path(d) / "outside"
            outside.mkdir()
            (root / "root").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "FORBIDDEN_PARENT_SYMLINK"):
                mod.check_tree(root)

    def test_autostart_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            outside = Path(d) / "outside"
            outside.mkdir()
            (outside / "S50dropbear").write_text("unsafe")
            (root / "etc/rc.d").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "AUTOSTART_DIRECTORY_SYMLINK"):
                mod.check_tree(root)

    def test_firmware_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            outside = Path(d) / "outside"
            outside.mkdir()
            (outside / "firmware").mkdir()
            (root / "usr/lib").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "FIRMWARE_PARENT_SYMLINK"):
                mod.check_tree(root)

    def test_unlocked_password_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "etc/shadow").write_text("root::0:0:99999:7:::\n")
            with self.assertRaisesRegex(ValueError, "ROOT_ACCOUNT_NOT_LOCKED"):
                mod.check_tree(root)

    def test_standard_absolute_symlink_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "var").symlink_to("/tmp")
            self.assertTrue(mod.check_tree(root))

    def test_forbidden_firmware_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "lib/firmware").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "FIRMWARE_RIGHTS_UNPROVEN"):
                mod.check_tree(root)

    def test_unprovisioned_ssh_autostart_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "etc/rc.d").mkdir(parents=True)
            (root / "etc/rc.d/S50dropbear").write_text("test")
            with self.assertRaisesRegex(ValueError, "UNPROVISIONED_AUTOSTART"):
                mod.check_tree(root)

    def test_output_inside_rootfs_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            # This must fail before a source receipt or squashfs tools are needed.
            with self.assertRaisesRegex(ValueError, "OUTPUT_INSIDE_INPUT_ROOTFS"):
                mod.produce(root, root / "out", Path(d) / "missing.json")

    def test_rootfs_symlink_rejected_before_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            alias = Path(d) / "stage-link"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "ROOTFS_SYMLINK"):
                mod.produce(alias, Path(d) / "out", Path(d) / "missing.json")

    def test_rootfs_ancestor_symlink_rejected_before_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            actual = Path(d) / "actual"
            root = actual / "stage"
            root.mkdir(parents=True)
            self.make_root(root)
            alias = Path(d) / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "ROOTFS_ANCESTOR_SYMLINK"):
                mod.produce(alias / "stage", Path(d) / "out", Path(d) / "missing.json")

    def test_output_symlink_into_rootfs_rejected_before_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            alias = Path(d) / "out-link"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "OUTPUT_INSIDE_INPUT_ROOTFS"):
                mod.produce(root, alias / "nested", Path(d) / "missing.json")

    def test_output_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            actual = Path(d) / "actual"
            actual.mkdir(mode=0o700)
            alias = Path(d) / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            receipt = Path(d) / "missing.json"
            # Fail before checking the receipt or invoking mksquashfs.
            with self.assertRaisesRegex(ValueError, "OUTPUT_ANCESTOR_SYMLINK"):
                mod.produce(root, alias / "out", receipt)

    def test_output_requires_verified_source_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_REQUIRED"):
                mod.produce(root, Path(d) / "out", Path(d) / "missing.json")


if __name__ == "__main__":
    unittest.main()
