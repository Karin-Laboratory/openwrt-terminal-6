# SPDX-License-Identifier: MIT
"""Host-only regression for QEMU split mount identity guard."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/air6-rescue-qemu-v0.3/n-unit-split-qemu.sh"


class MountIdentityGuardTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)

    def test_guard_uses_kernel_device_id_not_mount_source(self):
        src = SCRIPT.read_text()
        guard = src.split("check_mounts() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("/proc/self/mountinfo", guard)
        self.assertIn("/sys/class/block/vda43/dev", guard)
        self.assertIn("/sys/class/block/vda44/dev", guard)
        self.assertNotIn("/proc/mounts", guard.split("if /bin/busybox awk", 1)[-1])

    def test_mountinfo_alias_and_unrelated_devices(self):
        # mountinfo field 3 is major:minor; source after '-' may be an alias.
        awk = '$3==a || (b!="" && $3==b) {found=1} END {exit !found}'
        cases = [
            ("254:43", "254:44", "35 1 254:43 / /mnt/x rw - ext4 /dev/disk/by-uuid/abc rw\n", 0),
            ("254:43", "254:44", "35 1 254:44 / /mnt/x rw - ext4 /dev/mapper/alias rw\n", 0),
            ("254:43", "254:44", "35 1 254:45 / /mnt/x rw - ext4 /dev/vda43 rw\n", 1),
            ("254:43", "", "35 1 254:44 / /mnt/x rw - ext4 /dev/vda44 rw\n", 1),
        ]
        for a, b, record, expected in cases:
            with self.subTest(a=a, b=b, record=record):
                p = subprocess.run(["awk", "-v", f"a={a}", "-v", f"b={b}", awk],
                                   input=record, text=True, capture_output=True)
                self.assertEqual(p.returncode, expected)


if __name__ == "__main__":
    unittest.main()
