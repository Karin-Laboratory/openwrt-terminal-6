#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the production first-stage partition-name checks without block I/O."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/boot/air6_first_stage.sh"
START = "[ -r /sys/class/block/mmcblk0p26/uevent ]"
END = "    fail P44_PARTNAME"


class PartitionIdentityRuntimeTest(unittest.TestCase):
    def test_partition_names_fail_closed(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(source.count(START), 1)
        self.assertEqual(source.count(END), 1)
        fragment = source.split(START, 1)[1].split(END, 1)[0]
        fragment = START + fragment + END
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p26 = root / "p26"
            p44 = root / "p44"
            script = fragment.replace(
                "/sys/class/block/mmcblk0p26/uevent", str(p26)
            ).replace("/sys/class/block/mmcblk0p44/uevent", str(p44))
            prefix = 'fail() { echo "BLOCKED_$1"; exit 99; }\n'
            cases = (
                ("valid", "PARTNAME=rootfs_a\n", "PARTNAME=rootfs_data\n", True),
                ("swapped", "PARTNAME=rootfs_data\n", "PARTNAME=rootfs_a\n", False),
                ("missing-p26", None, "PARTNAME=rootfs_data\n", False),
                ("missing-p44", "PARTNAME=rootfs_a\n", None, False),
                ("prefix-p26", "PARTNAME=rootfs_a_extra\n", "PARTNAME=rootfs_data\n", False),
                ("prefix-p44", "PARTNAME=rootfs_a\n", "PARTNAME=rootfs_data_extra\n", False),
                ("case-mismatch", "partname=rootfs_a\n", "PARTNAME=rootfs_data\n", False),
            )
            for label, left, right, valid in cases:
                with self.subTest(label=label):
                    for path, value in ((p26, left), (p44, right)):
                        if value is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_text(value, encoding="ascii")
                    result = subprocess.run(
                        ["sh", "-c", prefix + script],
                        capture_output=True, text=True, timeout=5, check=False,
                    )
                    self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
