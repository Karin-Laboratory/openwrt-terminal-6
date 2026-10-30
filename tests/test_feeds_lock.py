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

PINS = {
    "packages": "11396c3434272b73294d29aa9d86497b25cf33da",
    "luci": "a8c110bed82375b69eb3881b2e54e617520e8c7d",
    "routing": "4b9891b9136259f93294a424507ed24c5e8c1cbd",
    "telephony": "5d68d53c160a325ea9d03fce393e051573bcc736",
    "video": "644a66261288b4a95dbc6e46fe805d33cb9f71d9",
}
TEXT = "\n".join((
    f"src-git packages https://git.openwrt.org/feed/packages.git^{PINS['packages']}",
    f"src-git luci https://git.openwrt.org/project/luci.git^{PINS['luci']}",
    f"src-git routing https://git.openwrt.org/feed/routing.git^{PINS['routing']}",
    f"src-git telephony https://git.openwrt.org/feed/telephony.git^{PINS['telephony']}",
    f"src-git video https://github.com/openwrt/video.git^{PINS['video']}",
))


class FeedLockTests(unittest.TestCase):
    def test_proposed_snapshot_is_exactly_pinned(self):
        lock = (ROOT / "config/feeds.lock").read_text()
        self.assertEqual(mod.inspect(lock), [])
        expected = PINS
        entries = [line.split() for line in lock.splitlines()
                   if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(len(entries), 5)
        for _, name, url in entries:
            self.assertEqual(url.rpartition("^")[2], expected[name])

    def test_pinned_first_party_feeds_are_accepted(self):
        self.assertEqual(mod.inspect(TEXT), [])

    def test_donor_default_unpinned_feeds_are_rejected(self):
        donor = "\n".join(line.rpartition("^")[0] for line in TEXT.splitlines())
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
        self.assertTrue(mod.inspect(TEXT + f"\nsrc-git extra https://git.openwrt.org/feed/extra.git^{"a" * 40}"))

    def test_unreviewed_full_length_feed_commits_are_rejected(self):
        for name, original in PINS.items():
            with self.subTest(feed=name):
                changed = TEXT.replace("^" + original, "^" + "a" * 40)
                errors = mod.inspect(changed)
                self.assertTrue(any("reviewed exact commit" in e for e in errors), errors)

    def test_tag_and_mutable_branch_are_rejected(self):
        self.assertTrue(mod.inspect(TEXT.replace("^" + PINS["packages"], ";main")))
        self.assertTrue(mod.inspect(TEXT.replace("^" + PINS["packages"], "^v1.0")))

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
