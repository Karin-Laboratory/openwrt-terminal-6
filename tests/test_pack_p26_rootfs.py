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
        (root / "etc/shadow").chmod(0o600)

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
            shadow.write_text("root:!:0:0:99999:7:::\n")
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

    def test_shadow_permissions_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            shadow = root / "etc/shadow"
            for mode in (0o644, 0o606, 0o620):
                shadow.chmod(mode)
                with self.subTest(mode=oct(mode)):
                    with self.assertRaisesRegex(ValueError, "SHADOW_PERMISSIONS_UNSAFE"):
                        mod.check_tree(root)
            shadow.chmod(0o640)
            self.assertTrue(mod.check_tree(root))

    def test_unlocked_password_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            (root / "etc/shadow").write_text("root::0:0:99999:7:::\n")
            with self.assertRaisesRegex(ValueError, "ROOT_ACCOUNT_NOT_LOCKED"):
                mod.check_tree(root)

    def test_secondary_accounts_must_be_locked_and_well_formed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            shadow = root / "etc/shadow"
            baseline = "root:!:0:0:99999:7:::\n"
            for account in ("guest:$6$hash:0:0:99999:7:::",
                            "guest::0:0:99999:7:::",
                            "guest:!", "guest:!x:0:0:99999:7::::extra"):
                shadow.write_text(baseline + account + "\n")
                with self.subTest(account=account):
                    with self.assertRaisesRegex(ValueError,
                                                "UNLOCKED_OR_MALFORMED_SHADOW_ACCOUNT"):
                        mod.check_tree(root)
            shadow.write_text(baseline + "guest:!:0:0:99999:7:::\n")
            self.assertTrue(mod.check_tree(root))

    def test_duplicate_or_invalid_shadow_account_names_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            shadow = root / "etc/shadow"
            baseline = "root:!:0:0:99999:7:::\n"
            shadow.write_text(baseline + "guest:!:0:0:99999:7:::\n" * 2)
            with self.assertRaisesRegex(ValueError, "DUPLICATE_SHADOW_ACCOUNT"):
                mod.check_tree(root)
            for name in ("guest user", "guest\tuser"):
                with self.subTest(name=name):
                    shadow.write_text(baseline + f"{name}:!:0:0:99999:7:::\n")
                    with self.assertRaisesRegex(ValueError, "UNLOCKED_OR_MALFORMED_SHADOW_ACCOUNT"):
                        mod.check_tree(root)

    def test_malformed_root_shadow_record_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_root(root)
            for malformed in ("root:", "root:!", "root:!:0:0:99999:7::"):
                (root / "etc/shadow").write_text(malformed + "\n")
                with self.subTest(malformed=malformed):
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

    def test_canonical_host_root_rejected_before_receipt(self):
        # /tmp/.. is lexically different from / but resolves to the host root.
        # Never inspect a receipt or traverse host files in this case.
        with self.assertRaisesRegex(ValueError, "HOST_ROOT_FORBIDDEN"):
            mod.produce(Path("/tmp/.."), Path("/tmp/p26-out"),
                        Path("/tmp/missing-p26-receipt.json"))

    def test_output_inside_rootfs_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            # This must fail before a source receipt or squashfs tools are needed.
            with self.assertRaisesRegex(ValueError, "OUTPUT_INSIDE_INPUT_ROOTFS"):
                mod.produce(root, root / "out", Path(d) / "missing.json")

    def test_source_receipt_inside_rootfs_rejected_before_pack(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = root / "provenance.json"
            receipt.write_text('{"source_built": true}')
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_INSIDE_ROOTFS"):
                mod.produce(root, Path(d) / "output", receipt)

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

    def test_feed_receipt_requires_immutable_commit_ids(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            record = {
                "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
                "package_install": True, "source_built": True,
                "packages": ["base-files", "busybox", "procd", "ubus",
                             "uci", "netifd", "dropbear"],
            }
            record["feeds"] = {}
            receipt.write_text(json.dumps(record))
            # Core-only OpenWrt builds legitimately have no extra feeds.
            with patch.object(mod, "check_tree", side_effect=RuntimeError("TREE_REACHED")):
                with self.assertRaisesRegex(RuntimeError, "TREE_REACHED"):
                    mod.produce(root, base / "out", receipt)
            for feeds in ({"packages": "main"},
                          {"packages": "a" * 39},
                          {"packages": "g" * 40},
                          {"packages": True}):
                record["feeds"] = feeds
                receipt.write_text(json.dumps(record))
                with self.subTest(feeds=feeds):
                    with self.assertRaisesRegex(ValueError, "PINNED_FEEDS_RECEIPT_REQUIRED"):
                        mod.produce(root, base / "out", receipt)

    def test_feed_receipt_rejects_ambiguous_names(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            for name in (" packages", "packages ", "bad feed",
                         "bad\nfeed", "bad\tfeed"):
                receipt.write_text(json.dumps({
                    "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
                    "package_install": True, "source_built": True,
                    "packages": ["base-files", "busybox", "procd", "ubus",
                                 "uci", "netifd", "dropbear"],
                    "feeds": {name: "a" * 40}
                }))
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ValueError, "PINNED_FEEDS_RECEIPT_REQUIRED"):
                        mod.produce(root, base / "out", receipt)
            self.assertFalse((base / "out").exists())

    def test_non_object_source_receipt_rejected_before_tree_checks(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            for value in ([], None, "text", 42, True):
                receipt.write_text(json.dumps(value))
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_NOT_OBJECT"):
                        mod.produce(root, base / "out", receipt)

    def test_source_receipt_duplicate_or_ambiguous_packages_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            packages = ["base-files", "busybox", "procd", "ubus",
                        "uci", "netifd", "dropbear"]
            for invalid in (packages + ["busybox"],
                            packages + ["bad package"],
                            packages + [" bad"],
                            packages + ["bad" + chr(10) + "name"],
                            packages + ["bad" + chr(0) + "name"],
                            packages + ["bad" + chr(127) + "name"]):
                receipt.write_text(json.dumps({
                    "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
                    "package_install": True, "source_built": True,
                    "packages": invalid, "feeds": {}
                }))
                with self.subTest(invalid=invalid[-1]):
                    with self.assertRaisesRegex(ValueError, "INCOMPLETE_PACKAGE_INVENTORY"):
                        mod.produce(root, base / "out", receipt)
            self.assertFalse((base / "out").exists())

    def test_source_receipt_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            for payload in (
                '{"openwrt_commit":"bad","openwrt_commit":"5799d2da76998be50432b0a3325b42713b4b619b"}',
                '{"feeds":{"packages":"bad","packages":"5799d2da76998be50432b0a3325b42713b4b619b"}}',
            ):
                receipt.write_text(payload)
                with self.subTest(payload=payload):
                    with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_INVALID_JSON"):
                        mod.produce(root, base / "out", receipt)

    def test_source_receipt_hardlink_inside_rootfs_rejected(self):
        import json
        import os
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            receipt.write_text(json.dumps({
                "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
                "package_install": True, "source_built": True,
                "packages": ["base-files", "busybox", "procd", "ubus",
                             "uci", "netifd", "dropbear"], "feeds": {}
            }))
            os.link(receipt, root / "receipt-copy.json")
            with self.assertRaisesRegex(ValueError,
                                        "SOURCE_RECEIPT_HARDLINK_INSIDE_ROOTFS"):
                mod.produce(root, base / "out", receipt)
            self.assertFalse((base / "out").exists())

    def test_source_receipt_fifo_rejected_without_blocking(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            fifo = base / "source.fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_NOT_REGULAR_FILE"):
                mod.produce(root, base / "out", fifo)

    def test_source_receipt_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            receipt.write_bytes(b" " * 65537)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_TOO_LARGE"):
                mod.produce(root, base / "out", receipt)

    def test_source_receipt_invalid_utf8_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stage"
            root.mkdir()
            self.make_root(root)
            receipt = base / "source.json"
            receipt.write_bytes(bytes([255]))
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_INVALID_JSON"):
                mod.produce(root, base / "out", receipt)

    def test_output_requires_verified_source_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "stage"
            root.mkdir()
            self.make_root(root)
            with self.assertRaisesRegex(ValueError, "SOURCE_RECEIPT_REQUIRED"):
                mod.produce(root, Path(d) / "out", Path(d) / "missing.json")


if __name__ == "__main__":
    unittest.main()
