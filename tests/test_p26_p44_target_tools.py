# SPDX-License-Identifier: MIT
import tempfile
from pathlib import Path
import unittest
from tools.boot import verify_p26_p44_target_tools as check


class TargetCommandsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "bin").mkdir()
        (self.root / "sbin").mkdir()
        self.busybox = self.root / "bin/busybox"
        self.busybox.write_bytes(b"\x7fELF" + b"0" * 64)
        self.busybox.chmod(0o755)

    def test_required_target_applets_pass(self):
        r = check.validate(self.root, "\n".join(check.REQUIRED))
        self.assertEqual(r["status"], "TARGET_BUSYBOX_RUNTIME_APPLETS_PASS")
        self.assertFalse(r["air6_boot_or_mount_proven"])

    def test_missing_switch_root_blocks(self):
        actual = "\n".join(x for x in check.REQUIRED if x != "switch_root")
        with self.assertRaisesRegex(ValueError, "TARGET_COMMAND_NOT_AVAILABLE:switch_root"):
            check.validate(self.root, actual)

    def test_standalone_target_executable_is_accepted(self):
        (self.root / "sbin/switch_root").write_text("binary")
        (self.root / "sbin/switch_root").chmod(0o755)
        actual = "\n".join(x for x in check.REQUIRED if x != "switch_root")
        r = check.validate(self.root, actual)
        self.assertEqual(r["commands"]["switch_root"], "target-executable:sbin/switch_root")

    def test_symlink_to_busybox_not_proof_of_missing_applet(self):
        (self.root / "sbin/switch_root").symlink_to("../bin/busybox")
        actual = "\n".join(x for x in check.REQUIRED if x != "switch_root")
        with self.assertRaisesRegex(ValueError, "TARGET_COMMAND_NOT_AVAILABLE:switch_root"):
            check.validate(self.root, actual)

    def test_outside_root_symlink_refused(self):
        (self.root / "sbin/switch_root").symlink_to("../../../../etc/passwd")
        actual = "\n".join(x for x in check.REQUIRED if x != "switch_root")
        with self.assertRaisesRegex(ValueError, "TARGET_PATH_ESCAPE"):
            check.validate(self.root, actual)

    def test_no_host_busybox_shortcut(self):
        with self.assertRaisesRegex(ValueError, "TARGET_COMMAND_NOT_AVAILABLE"):
            check.validate(self.root, "sh\nsha256sum")


if __name__ == "__main__":
    unittest.main()
