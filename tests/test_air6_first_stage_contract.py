# SPDX-License-Identifier: MIT
"""Public first-stage shell safety/order contract (no host block operations)."""
from pathlib import Path
import subprocess
import unittest

FIRST = Path(__file__).resolve().parents[1] / "tools/boot/air6_first_stage.sh"
CHECKER = FIRST.with_name("verify_bound_p26.sh")


class FirstStageContractTests(unittest.TestCase):
    def test_shell_syntax(self):
        for file in (FIRST, CHECKER):
            subprocess.run(["sh", "-n", str(file)], check=True, timeout=10)

    def test_boot_gates_order_and_fail_closed(self):
        text = FIRST.read_text()
        steps = [
            "grep -Fxq 'bootslot=a'",
            "grep -qx 'PARTNAME=rootfs_a'",
            "grep -qx 'PARTNAME=rootfs_data'",
            "/usr/libexec/air6/verify-bound-p26",
            "mount -t squashfs -o ro",
            "mount -t ext4 -o ro,noload",
            "grep -Fxq 'SBA6D_ROOTFS_DATA_V1'",
            '[ "$(readlink /mnt/air6/check/.fs_state)" = 2 ]',
            "umount /mnt/air6/check",
            "mount -t ext4 -o rw,noatime,nosuid,nodev",
            "mount -t overlay overlay -o lowerdir=",
            "mount -t squashfs -o ro",
            "exec /sbin/switch_root"
        ]
        positions = [text.find(t) for t in steps]
        # Two distinct squashfs RO mounts (initial lower and final /rom).
        positions[11] = text.find("mount -t squashfs -o ro", positions[10] + 1)
        self.assertTrue(all(p >= 0 for p in positions), positions)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("while :; do sleep 60; done", text)

    def test_emmc_discovery_is_bounded_and_precedes_identity_checks(self):
        text = FIRST.read_text()
        start = text.index('i=0\nwhile [ ! -b "$root" ] || [ ! -b "$persist" ]; do')
        end = text.index('\ndone', start) + len('\ndone')
        loop = text[start:end]
        self.assertIn('[ "$i" -lt 20 ] || fail PARTITIONS_NOT_BLOCK', loop)
        self.assertIn('sleep 1', loop)
        self.assertIn('i=$((i + 1))', loop)
        self.assertLess(end, text.index('fail PARTITIONS_ALIASED'))
        self.assertLess(end, text.index("grep -qx 'PARTNAME=rootfs_a'"))
        self.assertLess(end, text.index('/usr/libexec/air6/verify-bound-p26'))
        self.assertNotIn('mknod', text)
        self.assertNotIn('blockdev --rereadpt', text)

    def test_no_partition_mutation_or_formatting(self):
        text = FIRST.read_text()
        for disallowed in ("mkfs", "mke2fs", "e2fsck", "resize2fs",
                           "dd if=", "wipefs", "parted ", "sfdisk "):
            self.assertNotIn(disallowed, text)
        self.assertIn("mount -t ext4 -o ro,noload", text)
        self.assertNotIn("mkdir -p /mnt/air6/rw/upper", text)
        self.assertNotIn("mkdir -p /mnt/air6/rw/work", text)


if __name__ == "__main__":
    unittest.main()
