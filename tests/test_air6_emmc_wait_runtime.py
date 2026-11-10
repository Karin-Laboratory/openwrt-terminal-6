#!/usr/bin/env python3
"""Host-only executable regression for the first-stage eMMC wait loop.

The extracted production loop is run with regular-file presence substituted for
block-device presence. This tests timing/control flow, NOT real eMMC discovery.
"""
import pathlib
import re
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'tools/boot/air6_first_stage.sh'


def wait_loop():
    source = SCRIPT.read_text()
    match = re.search(r'(?m)^i=0\nwhile \[ ! -b "\$root" \] \|\| \[ ! -b "\$persist" \]; do\n(?:.*\n)*?done$', source)
    if not match:
        raise AssertionError('production eMMC wait loop not found')
    return match.group().replace('! -b', '! -e')


class WaitRuntimeTests(unittest.TestCase):
    def run_case(self, initial, appear_at=None):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'root'
            persist = pathlib.Path(directory) / 'persist'
            for name in initial:
                {'root': root, 'persist': persist}[name].touch()
            # sleep is a deterministic mock: each call advances one simulated second.
            script = '''
root="$1"; persist="$2"; appear="$3"; ticks=0
fail() { echo "FAIL:$1:$ticks"; exit 17; }
sleep() {
  ticks=$((ticks + 1))
  if [ "$ticks" -eq "$appear" ]; then : > "$root"; : > "$persist"; fi
}
''' + wait_loop() + '''
printf 'PASS:%s\\n' "$ticks"
'''
            result = subprocess.run(['/bin/sh', '-c', script, 'test', str(root), str(persist), str(appear_at or -1)], capture_output=True, text=True, timeout=5)
            return result.returncode, result.stdout.strip()

    def test_both_present_immediately(self):
        self.assertEqual(self.run_case({'root', 'persist'}), (0, 'PASS:0'))

    def test_delayed_nodes_at_last_allowed_tick(self):
        self.assertEqual(self.run_case(set(), 20), (0, 'PASS:20'))

    def test_nodes_never_appear(self):
        self.assertEqual(self.run_case(set()), (17, 'FAIL:PARTITIONS_NOT_BLOCK:20'))

    def test_only_one_node_is_not_sufficient(self):
        self.assertEqual(self.run_case({'root'}), (17, 'FAIL:PARTITIONS_NOT_BLOCK:20'))


if __name__ == '__main__':
    unittest.main()
