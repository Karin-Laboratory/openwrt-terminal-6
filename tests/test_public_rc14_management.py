# SPDX-License-Identifier: MIT
"""Public RC14-derived P26 management candidate, host-only safety checks."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "config/sbat6-stage/usr/libexec/sba6d/rc14-management.sh"
WORKFLOW = ROOT / ".github/workflows/mt6990-native-subtarget.yml"


class PublicRc14ManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text()
        cls.workflow = WORKFLOW.read_text()

    def test_posix_shell_syntax(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)

    def test_no_unprovisioned_autostart_or_shared_secret(self):
        self.assertIn('case "${1:-}" in', self.source)
        self.assertIn("--check|--start", self.source)
        self.assertIn("SSH_PROVISIONING_MISSING", self.source)
        self.assertIn("SSH_SECRET_OWNER_MODE", self.source)
        self.assertIn("AUTHORIZED_KEY_FORMAT", self.source)
        for forbidden in ("ssh-keygen", "dropbearkey", "mkfs.", "modprobe",
                          "insmod ", "iw phy", "hostapd ", "reboot",
                          "ip link set", "ip addr add"):
            self.assertNotIn(forbidden, self.source)

    def test_rc14_observed_management_order_and_port(self):
        for required in ("NETSYS_MAC1_ABSENT", "DSA_LAN2_ABSENT",
                         "LAN2_NO_CARRIER", "LAN2_NOT_1000",
                         "LAN2_NOT_FULL_DUPLEX", "DROPBEAR_START",
                         "DROPBEAR_LISTEN_READY"):
            self.assertIn(required, self.source)
        self.assertLess(self.source.index("NETSYS_MAC1_ABSENT"),
                        self.source.index("DSA_LAN2_ABSENT"))
        self.assertLess(self.source.index("LAN2_NOT_1000"),
                        self.source.index("DROPBEAR_START"))
        self.assertIn("192.168.1.1:22", self.source)
        self.assertIn("-s -g -j -k", self.source)

    def test_p26_stage_and_no_p44_development_script(self):
        self.assertIn("PUBLIC_MT6990_P26_INTERNAL_RC14_MANAGEMENT_SOURCE_STAGED",
                      self.workflow)
        self.assertIn('fakeroot -i "$work/p26-fakeroot.state"', self.workflow)
        self.assertIn("config/sbat6-stage/usr/libexec/sba6d/rc14-management.sh",
                      self.workflow)
        self.assertIn('sh -n "$management"', self.workflow)
        self.assertIn("No SXXrc14 startup link is installed", self.workflow)
        self.assertIn("PUBLIC_MT6990_P26_INTERNAL_MANAGEMENT_TARGET_ROOT_OWNERSHIP_PASS",
                      self.workflow)
        self.assertIn("PUBLIC_MT6990_REAL_P26_EMBEDDED_RC14_MANAGEMENT_READBACK_PASS",
                      self.workflow)
        self.assertIn("unsquashfs -cat", self.workflow)
        self.assertIn("usr/libexec/sba6d/rc14-management.sh |", self.workflow)
        self.assertIn("stat -c '%u:%g:%a' \"$management\" | grep -Fx '0:0:755'",
                      self.workflow)
        self.assertLess(
            self.workflow.index("PUBLIC_MT6990_P26_INTERNAL_MANAGEMENT_TARGET_ROOT_OWNERSHIP_PASS"),
            self.workflow.index("PUBLIC_MT6990_REAL_P26_EMBEDDED_RC14_MANAGEMENT_READBACK_PASS"))
        self.assertNotIn('install -D -m 0755 "$GITHUB_WORKSPACE/config/sbat6-stage/'
                         'usr/libexec/sba6d/rc14-management.sh" "$rootfs/overlay/',
                         self.workflow)


if __name__ == "__main__":
    unittest.main()
