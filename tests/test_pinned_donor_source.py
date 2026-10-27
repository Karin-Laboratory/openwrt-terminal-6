# SPDX-License-Identifier: MIT
"""Offline tests for donor *text-only* acquisition, no device/vendor payloads."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fetch-pinned-openwrt-donor.sh"


class DonorTextAllowlistTests(unittest.TestCase):
    def test_public_donor_revision_is_pinned(self):
        body = SCRIPT.read_text()
        self.assertIn("github.com/13179415360/openwrt-mt6990-lg6851f.git", body)
        self.assertIn("a40df9a5afb46716dea799acea69f17480df4d82", body)
        self.assertIn("FETCH_HEAD^{commit}", body)
        self.assertIn("--filter=blob:none", body)

    def test_exact_four_source_text_blob_allowlist(self):
        body = SCRIPT.read_text()
        for name, expected in (
            ("feeds.conf.default", "05f5c8c47c7ae4161067e045f579ddf46c4fe77f"),
            ("target/linux/mediatek/Makefile", "77b27878987e53e83be3d40dc342753e3734ac75"),
            ("target/linux/mediatek/mt6990/target.mk", "c98113e8a8cc9ee334eef28428972d8e9d4404e7"),
            ("target/linux/mediatek/image/mt6990.mk", "714551500ccd45bd3dfc77f951f104e0c46a660b"),
        ):
            self.assertIn(name, body)
            self.assertIn(expected, body)
        self.assertIn("git hash-object --", body)
        self.assertIn("DONOR_TEXT_ALLOWLIST_4_BLOBS_PASS", body)

    def test_no_checkout_of_firmware_binaries_or_arbitrary_source(self):
        body = SCRIPT.read_text()
        for forbidden in (
            "git clone", "git checkout", "sparse-checkout", "sysupgrade",
            "fastboot", "dd if=", "mkimage", "sign-image", "make -j",
            "sudo ", "ssh root@", "scp ", "flashrom", "apt install",
            "TARGET_DEVICES +=", "mt7996_eeprom", "connsys_gnss_b.img",
        ):
            self.assertNotIn(forbidden, body)
        self.assertIn("cat-file blob", body)

    def test_bash_variable_expansion_is_not_escaped(self):
        body = SCRIPT.read_text()
        self.assertNotIn(chr(92) + "${", body)
        self.assertIn('${TMPDIR:-/tmp}', body)

    def test_non_root_no_overwrite_and_temp_cleanup(self):
        body = SCRIPT.read_text()
        for expected in (
            "EUID == 0", "-e \"$DEST\"", "-L \"$DEST\"",
            "trap 'rm -rf -- \"$temporary\"' EXIT",
            'mv -- "$temporary/output" "$DEST"',
        ):
            self.assertIn(expected, body)


if __name__ == "__main__":
    unittest.main()
