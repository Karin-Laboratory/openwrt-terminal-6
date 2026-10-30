# SPDX-License-Identifier: MIT
"""Host-only regression for pinned non-installable Air6 source selection."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "air6_userspace_source_checker", ROOT / "tools/build/check_air6_userspace_source.py"
)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)

class Air6UserspaceSourceTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "config/sbat6-userspace-source.json").read_text())
        self.feeds = (ROOT / "config/feeds.lock").read_text()

    def errors(self, plan=None, feeds=None):
        return checker.validate(self.plan if plan is None else plan,
                                self.feeds if feeds is None else feeds)

    def test_fixed_manifest_and_feeds_are_source_only(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.plan["output_policy"]["rootfs_build_allowed"], False)

    def test_reject_floating_upstream_revision(self):
        for ref in ("main", "v25", "0" * 39, "deadbeef^"):
            p = copy.deepcopy(self.plan)
            p["openwrt"]["commit"] = ref
            self.assertTrue(self.errors(p))

    def test_reject_unreviewed_but_full_length_upstream_commit(self):
        p = copy.deepcopy(self.plan)
        # A syntactically valid SHA must not silently change the reviewed input.
        p["openwrt"]["commit"] = "a" * 40
        self.assertTrue(any("reviewed exact Git commit" in e for e in self.errors(p)))

    def test_reject_other_device_donor_or_untrusted_upstream(self):
        p = copy.deepcopy(self.plan)
        p["openwrt"]["url"] = "https://github.com/13179415360/openwrt-mt6990-lg6851f"
        self.assertTrue(self.errors(p))

    def test_pin_six_official_upstream_package_makefiles(self):
        self.assertEqual(len(self.plan["package_makefiles"]), 6)
        self.assertEqual(self.errors(), [])
        for key, replacement in (
            ("package", "other-package"),
            ("path", "package/unreviewed/Makefile"),
            ("git_blob_sha1", "a" * 40),
        ):
            with self.subTest(field=key):
                p = copy.deepcopy(self.plan)
                p["package_makefiles"][0][key] = replacement
                self.assertTrue(any("Makefile provenance" in e for e in self.errors(p)))
        for mutation in ("extra", "missing", "nonmapping"):
            with self.subTest(mutation=mutation):
                p = copy.deepcopy(self.plan)
                if mutation == "extra":
                    p["package_makefiles"].append(copy.deepcopy(p["package_makefiles"][0]))
                elif mutation == "missing":
                    p["package_makefiles"].pop()
                else:
                    p["package_makefiles"][0] = None
                self.assertTrue(any("Makefile provenance" in e for e in self.errors(p)))

    def local_fixture(self, root):
        path = root / "package" / "base-files" / "Makefile"
        path.parent.mkdir(parents=True)
        data = b"synthetic Makefile fixture\n"
        path.write_bytes(data)
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        return path, (("base-files", "package/base-files/Makefile", digest),)

    def test_local_makefile_bytes_match_and_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, records = self.local_fixture(root)
            self.assertEqual(checker.verify_local_makefiles(root, records), [])
            path.write_bytes(b"tampered fixture\n")
            self.assertIn("bytes differ", str(checker.verify_local_makefiles(root, records)))

    def test_local_makefile_missing_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, records = self.local_fixture(root)
            path.unlink()
            self.assertIn("unavailable or unsafe", str(checker.verify_local_makefiles(root, records)))
            target = root / "unreviewed"
            target.write_bytes(b"unreviewed source")
            path.symlink_to(target)
            self.assertIn("unavailable or unsafe", str(checker.verify_local_makefiles(root, records)))

    def test_local_makefile_symlinked_parent_and_oversize_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, records = self.local_fixture(root)
            path.write_bytes(b"x" * (1024 * 1024 + 1))
            self.assertIn("unavailable or unsafe", str(checker.verify_local_makefiles(root, records)))
            path.unlink()
            original = root / "package" / "base-files"
            relocated = root / "relocated"
            original.rename(relocated)
            original.symlink_to(relocated, target_is_directory=True)
            self.assertIn("unavailable or unsafe", str(checker.verify_local_makefiles(root, records)))

    def test_local_makefile_nonregular_fifo_is_rejected_without_blocking(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("POSIX only")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, records = self.local_fixture(root)
            path.unlink()
            os.mkfifo(path)
            self.assertIn("unavailable or unsafe", str(checker.verify_local_makefiles(root, records)))

    def test_reject_floating_feed_or_source_link(self):
        self.assertTrue(self.errors(feeds=self.feeds.replace(
            "^11396c3434272b73294d29aa9d86497b25cf33da", "")))
        self.assertTrue(self.errors(feeds=self.feeds + "\nsrc-link packages /home/private\n"))

    def test_reject_rootfs_or_image_build_enable(self):
        for key in self.plan["output_policy"]:
            p = copy.deepcopy(self.plan)
            p["output_policy"][key] = True
            self.assertTrue(self.errors(p))

    def test_reject_insecure_first_boot_or_extra_packages(self):
        p = copy.deepcopy(self.plan)
        p["first_boot"]["preset_root_password"] = ""
        self.assertTrue(self.errors(p))
        p = copy.deepcopy(self.plan)
        p["packages"].append("luci-app-5gmodem")
        self.assertTrue(self.errors(p))

    def test_no_automatic_rights_approval_or_extra_fields(self):
        p = copy.deepcopy(self.plan)
        p["rights_review"] = "approved"
        self.assertTrue(self.errors(p))
        p = copy.deepcopy(self.plan)
        p["flash_image"] = "boot_a.img"
        self.assertTrue(self.errors(p))

if __name__ == "__main__":
    unittest.main()
