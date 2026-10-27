# SPDX-License-Identifier: MIT
"""No network, no install: deterministic feed configuration safety tests."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verify_feeds_lock", ROOT / "tools/build/verify_feeds_lock.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PIN = "a" * 40
TEXT = "\n".join((
    f"src-git packages https://git.openwrt.org/feed/packages.git^{PIN}",
    f"src-git luci https://git.openwrt.org/project/luci.git^{PIN}",
    f"src-git routing https://git.openwrt.org/feed/routing.git^{PIN}",
    f"src-git telephony https://git.openwrt.org/feed/telephony.git^{PIN}",
    f"src-git video https://github.com/openwrt/video.git^{PIN}",
))


class FeedLockTests(unittest.TestCase):
    def test_pinned_first_party_feeds_are_accepted(self):
        self.assertEqual(mod.inspect(TEXT), [])

    def test_donor_default_unpinned_feeds_are_rejected(self):
        donor = TEXT.replace("^" + PIN, "")
        issues = mod.inspect(donor)
        self.assertEqual(sum("exact 40-char Git SHA" in x for x in issues), 5)

    def test_tokenized_or_http_feed_is_rejected(self):
        t = TEXT.replace("https://git.openwrt.org/feed/packages.git",
                         "http://user:pass@git.openwrt.org/feed/packages.git")
        self.assertTrue(mod.inspect(t))

    def test_forged_upstream_or_other_packages_are_rejected(self):
        self.assertTrue(mod.inspect(TEXT.replace(
            "https://github.com/openwrt/video.git",
            "https://example.invalid/openwrt/video.git")))
        self.assertTrue(mod.inspect(TEXT + f"\nsrc-git extra https://git.openwrt.org/feed/extra.git^{PIN}"))

    def test_tag_and_mutable_branch_are_rejected(self):
        self.assertTrue(mod.inspect(TEXT.replace("^" + PIN, ";main")))
        self.assertTrue(mod.inspect(TEXT.replace("^" + PIN, "^v1.0")))

    def test_link_and_shell_are_rejected(self):
        self.assertTrue(mod.inspect(TEXT + "\nsrc-link local /private/source"))
        self.assertTrue(mod.inspect(TEXT.replace(
            "https://github.com/openwrt/video.git",
            "https://github.com/openwrt/video.git;echo")))

    def test_missing_and_duplicate_feeds_are_rejected(self):
        self.assertTrue(mod.inspect(TEXT.rsplit("\n", 1)[0]))
        self.assertTrue(mod.inspect(TEXT + "\n" + TEXT.splitlines()[0]))


if __name__ == "__main__":
    unittest.main()
