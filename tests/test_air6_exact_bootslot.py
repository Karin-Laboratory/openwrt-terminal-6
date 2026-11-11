# SPDX-License-Identifier: MIT
"""Execute the production slot-A guard against synthetic kernel command lines."""
from pathlib import Path
import re
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools/boot/air6_first_stage.sh"


class SlotArgumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = SOURCE.read_text()
        match = re.search(r"^(tr .*?</proc/cmdline \| grep -Fxq 'bootslot=a') \|\| fail NOT_SLOT_A$", script, re.M)
        if match is None:
            raise AssertionError("production slot guard not found")
        cls.guard = match.group(1).replace("</proc/cmdline", "<\"$1\"")

    def check_slot(self, cmdline, expected):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cmdline"
            path.write_text(cmdline)
            result = subprocess.run(["sh", "-c", self.guard, "slot-test", str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode == 0, expected, (cmdline, result.stderr))

    def test_exact_slot(self):
        self.check_slot("console=ttyS0 bootslot=a rootwait", True)

    def test_other_slot(self):
        self.check_slot("console=ttyS0 bootslot=b rootwait", False)

    def test_suffix_punctuation(self):
        for suffix in (",b", "-fallback", ".backup", "/other", ":other"):
            with self.subTest(suffix=suffix):
                self.check_slot("console=ttyS0 bootslot=a" + suffix, False)

    def test_prefix_and_longer_value(self):
        for cmdline in ("xbootslot=a", "bootslot=aa", "bootslot=a_extra"):
            with self.subTest(cmdline=cmdline):
                self.check_slot(cmdline, False)

    def test_tabs_and_newline(self):
        self.check_slot("console=ttyS0\tbootslot=a\trootwait\n", True)


if __name__ == "__main__":
    unittest.main()
