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

    def test_fakeroot_state_survives_separate_install_and_pack_processes(self):
        # Native CI uses separate fakeroot invocations for package/install and
        # p26 packing. Verify the recorded target ownership survives that
        # boundary rather than silently becoming runner-owned.
        import os
        import shutil
        import subprocess
        import sys
        if not shutil.which("fakeroot"):
            self.skipTest("fakeroot unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shadow = root / "shadow"
            shadow.write_text("root:!:0:0:99999:7:::\\n")
            state = root / "fakeroot.state"
            install = subprocess.run(
                ["fakeroot", "-s", str(state), "--", sys.executable, "-c",
                 "import os,sys; os.chown(sys.argv[1],0,0); os.chmod(sys.argv[1],0o600)",
                 str(shadow)], capture_output=True, text=True, timeout=30)
            self.assertEqual(install.returncode, 0, install.stderr)
            self.assertTrue(state.is_file())
            pack = subprocess.run(
                ["fakeroot", "-i", str(state), "--", sys.executable, "-c",
                 "import os,sys; s=os.stat(sys.argv[1]); "
                 "assert (s.st_uid,s.st_gid,s.st_mode & 0o777)==(0,0,0o600)",
                 str(shadow)], capture_output=True, text=True, timeout=30)
            self.assertEqual(pack.returncode, 0, pack.stderr)

    def test_runner_owned_target_files_rejected(self):
        from types import SimpleNamespace
        with patch.object(mod.Path, "stat", return_value=SimpleNamespace(st_uid=1001, st_gid=1001)):
            with self.assertRaisesRegex(ValueError, "TARGET_ROOT_OWNERSHIP_UNPROVEN_ETC_SHADOW"):
                mod.check_target_ownership(Path("/synthetic-root"))

    def test_root_owned_target_files_accepted(self):
        from types import SimpleNamespace
        with patch.object(mod.Path, "stat", return_value=SimpleNamespace(st_uid=0, st_gid=0)):
            self.assertTrue(mod.check_target_ownership(Path("/synthetic-root")))

    def test_xattr_cannot_be_silently_dropped(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            if not hasattr(os, "setxattr"):
                self.skipTest("xattr API unavailable")
            try:
                os.setxattr(root / "bin/busybox", "user.p26_test", b"1")
            except OSError:
                self.skipTest("filesystem does not permit user xattrs")
            with self.assertRaisesRegex(ValueError, "XATTR_WOULD_BE_DROPPED"):
                mod.check_tree(root)

    def test_root_directory_xattr_cannot_be_silently_dropped(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            if not hasattr(os, "setxattr"):
                self.skipTest("xattr API unavailable")
            try:
                os.setxattr(root, "user.p26_test", b"1")
            except OSError:
                self.skipTest("filesystem does not permit user xattrs")
            with self.assertRaisesRegex(ValueError, "XATTR_WOULD_BE_DROPPED"):
                mod.check_tree(root)

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

    def test_empty_firmware_directories_are_safe(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "lib/firmware").mkdir(parents=True)
            (root / "usr/lib/firmware").mkdir(parents=True)
            self.assertTrue(mod.check_tree(root))

    def test_forbidden_firmware_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            firmware = root / "lib/firmware"
            firmware.mkdir(parents=True)
            (firmware / "radio.bin").write_bytes(b"unreviewed")
            with self.assertRaisesRegex(ValueError, "FIRMWARE_RIGHTS_UNPROVEN"):
                mod.check_tree(root)

    def test_firmware_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root"
            root.mkdir()
            self.make_root(root)
            (root / "lib/firmware").parent.mkdir(parents=True, exist_ok=True)
            (root / "lib/firmware").symlink_to("../missing-firmware")
            with self.assertRaisesRegex(ValueError, "FIRMWARE_RIGHTS_UNPROVEN"):
                mod.check_tree(root)

    def test_nested_firmware_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "usr/lib/firmware/vendor").mkdir(parents=True)
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

    def test_failed_mksquashfs_removes_only_new_output(self):
        import json
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            stage = base / "stage"
            stage.mkdir()
            self.make_root(stage)
            out_parent = base / "private"
            out_parent.mkdir(mode=0o700)
            sentinel = out_parent / "keep.txt"
            sentinel.write_text("unchanged")
            source = base / "source.json"
            source.write_text(json.dumps({
                "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
                "package_install": True, "source_built": True,
                "packages": ["base-files", "busybox", "procd", "ubus",
                             "uci", "netifd", "dropbear"],
                "feeds": {}
            }))
            output = out_parent / "new-output"

            def fail_after_partial_output(*args, **kwargs):
                (output / "rootfs.squashfs").write_bytes(b"partial")
                raise subprocess.CalledProcessError(1, "mksquashfs")

            with patch.object(mod, "check_tree", return_value=True), \
                 patch.object(mod, "check_target_ownership", return_value=True), \
                 patch.object(mod.shutil, "which", return_value="/usr/bin/mock"), \
                 patch.object(mod.subprocess, "run", side_effect=fail_after_partial_output):
                with self.assertRaises(subprocess.CalledProcessError):
                    mod.produce(stage, output, source)
            self.assertFalse(output.exists())
            self.assertEqual(sentinel.read_text(), "unchanged")
            self.assertTrue(stage.is_dir())
            self.assertTrue(source.is_file())

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

    def test_source_receipt_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            actual = Path(d) / "receipt-dir"
            actual.mkdir()
            (actual / "source.json").write_text("{}")
            alias = Path(d) / "receipt-alias"
            alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_ANCESTOR_SYMLINK"):
                mod.produce(root, Path(d) / "out", alias / "source.json")

    def test_output_requires_verified_source_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_REQUIRED"):
                mod.produce(root, Path(d) / "out", Path(d) / "missing.json")


if __name__ == "__main__":
    unittest.main()
