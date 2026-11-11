# SPDX-License-Identifier: MIT
"""Run both production bootslot guards against synthetic kernel command lines."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools/boot/air6_first_stage.sh"


class UniqueBootslotRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = SOURCE.read_text()
        count = re.search(r"^slot_count=\$\(tr .*?</proc/cmdline \| grep -c '\^bootslot=' \|\| :\)$", source, re.M)
        exact = re.search(r"^tr .*?</proc/cmdline \| grep -Fxq 'bootslot=a' \|\| fail NOT_SLOT_A$", source, re.M)
        if not count or not exact or '[ "$slot_count" = 1 ] || fail BOOTSLOT_AMBIGUOUS' not in source:
            raise AssertionError("production count/exact bootslot guards missing")
        cls.count = count.group().replace("</proc/cmdline", '<"$1"')
        cls.exact = exact.group().replace("</proc/cmdline", '<"$1"')

    def check(self, cmdline, accepted):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cmdline"
            path.write_text(cmdline)
            script = ('fail() { exit 91; }; ' + self.count + '; '
                      '[ "$slot_count" = 1 ] || fail BOOTSLOT_AMBIGUOUS; '
                      + self.exact)
            result = subprocess.run(["sh", "-c", script, "slot-test", str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode == 0, accepted,
                             (cmdline, result.returncode, result.stderr))

    def test_single_valid_slot(self):
        self.check("console=ttyS0 bootslot=a rootwait", True)

    def test_duplicate_same_slot(self):
        self.check("bootslot=a bootslot=a", False)

    def test_conflicting_slots(self):
        self.check("bootslot=a bootslot=b", False)
        self.check("bootslot=b bootslot=a", False)

    def test_no_slot(self):
        self.check("console=ttyS0 rootwait", False)

    def test_malformed_slot(self):
        for cmdline in ("bootslot=a,b", "bootslot=a-fallback", "bootslot=aa", "bootslot="):
            with self.subTest(cmdline=cmdline):
                self.check(cmdline, False)

    def test_tabs(self):
        self.check("console=ttyS0\tbootslot=a\trootwait\n", True)
        self.check("bootslot=a\tbootslot=b", False)


if __name__ == "__main__":
    unittest.main()
