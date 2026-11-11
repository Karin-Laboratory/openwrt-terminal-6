# SPDX-License-Identifier: MIT
"""Execute the exact first-stage bootslot gate against synthetic cmdlines."""
from pathlib import Path
import subprocess
import tempfile
import unittest

FIRST = Path(__file__).resolve().parents[1] / "tools/boot/air6_first_stage.sh"


class BootslotUniquenessTests(unittest.TestCase):
    def test_bootslot_cases(self):
        text = FIRST.read_text()
        start = text.index("slot_count=$(tr ")
        end = text.index("\nroot=/dev/mmcblk0p26", start)
        gate = text[start:end]
        self.assertIn('grep -c', gate)
        self.assertIn('grep -Fxq', gate)
        with tempfile.TemporaryDirectory() as d:
            cmdline = Path(d) / "cmdline"
            script = gate.replace("</proc/cmdline", '<"$1"')
            wrapper = 'fail() { exit 37; }\n' + script + '\n'
            for value, accepted in (
                ("bootslot=a rootwait", True),
                ("rootwait\tbootslot=a", True),
                ("bootslot=b rootwait", False),
                ("rootwait", False),
                ("bootslot=a bootslot=b", False),
                ("bootslot=a bootslot=a", False),
                ("bootslot=b bootslot=a", False),
                ("bootslot=a,b", False),
                ("bootslot=a-fallback", False),
                ("bootslot=a bootslot=a,b", False),
            ):
                with self.subTest(value=value):
                    cmdline.write_text(value + "\n")
                    result = subprocess.run(
                        ["sh", "-c", wrapper, "sh", str(cmdline)],
                        capture_output=True, text=True, timeout=5,
                    )
                    self.assertEqual(result.returncode == 0, accepted, result.stderr)


if __name__ == "__main__":
    unittest.main()
