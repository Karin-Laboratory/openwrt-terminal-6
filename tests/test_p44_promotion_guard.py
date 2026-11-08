# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import tempfile
import unittest
from tools.overlay import p44_promotion_guard as p44


class P44PromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upper = self.root / "upper"
        (self.upper / "etc/init.d").mkdir(parents=True)
        self.p = self.upper / "etc/init.d/air6-demo"
        self.p.write_text("#!/bin/sh\nexit 0\n")

    def test_allowlisted_script_staged_with_digest(self):
        result = p44.stage(self.upper, ["etc/init.d/air6-demo"], self.root / "new")
        self.assertEqual(len(result), 1)
        self.assertEqual((self.root / "new/etc/init.d/air6-demo").read_bytes(), self.p.read_bytes())
        saved = json.loads((self.root / "new/air6-p44-promotion-manifest.json").read_text())
        self.assertFalse(saved["p26_rebuilt"])

    def test_protected_credentials_and_configs_refused(self):
        for path in ("etc/config/wireless", "etc/shadow", "etc/dropbear/authorized_keys",
                     "lib/firmware/device.bin", "etc/init.d/../../etc/shadow"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                p44.safe_path(path)

    def test_whiteout_and_symlink_never_staged(self):
        (self.upper / "etc/init.d/link").symlink_to(self.p)
        with self.assertRaisesRegex(ValueError, "SYMLINK"):
            p44.audit_source(self.upper, ["etc/init.d/link"])
        with self.assertRaises(ValueError):
            p44.safe_path("etc/init.d/.wh.air6-demo")

    def test_refuse_live_destination_overwrite(self):
        dst = self.root / "new"
        dst.mkdir()
        with self.assertRaisesRegex(ValueError, "DESTINATION_EXISTS"):
            p44.stage(self.upper, ["etc/init.d/air6-demo"], dst)
        self.assertTrue(self.p.exists())


if __name__ == "__main__":
    unittest.main()
