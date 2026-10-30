# SPDX-License-Identifier: MIT
"""Host-only regression for pinned non-installable Air6 source selection."""
from pathlib import Path
import copy
import importlib.util
import json
import sys
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

    def test_reject_other_device_donor_or_untrusted_upstream(self):
        p = copy.deepcopy(self.plan)
        p["openwrt"]["url"] = "https://github.com/13179415360/openwrt-mt6990-lg6851f"
        self.assertTrue(self.errors(p))

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
