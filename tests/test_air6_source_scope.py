# SPDX-License-Identifier: MIT
"""Negative tests: unproven Air6 device-tree consumers must stay disabled."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "air6_scope_guard", ROOT / "tools/board/check_air6_scope.py"
)
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)

class Air6SourceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (ROOT / "board/mt6990-air-terminal-6.dts").read_text()
        cls.trial = (ROOT / "board/mt6990-air-terminal-6-ethernet-test.dts").read_text()

    def test_current_source_scope_is_consistent(self):
        self.assertEqual(guard.validate(self.base, self.trial), [])

    def test_base_mmc_must_remain_disabled(self):
        mutated = self.base.replace(
            "&mmc0 {\n", '&mmc0 {\n\tstatus = "okay";\n', 1)
        self.assertTrue(guard.validate(mutated, self.trial))

    def test_unsupported_pcie_enablement_is_rejected(self):
        mutated = self.base.replace(
            '&pcie0 {\n\tstatus = "disabled";',
            '&pcie0 {\n\tstatus = "okay";', 1)
        self.assertIn("base: unexpectedly enabled pcie0",
                      guard.validate(mutated, self.trial))

    def test_extra_trial_consumer_is_rejected(self):
        mutated = self.trial + '\n&usb { status = "okay"; };\n'
        self.assertTrue(any("unexpected or missing references" in x
                            for x in guard.validate(self.base, mutated)))

    def test_trial_must_not_override_mmc_or_bootargs(self):
        mutated = self.trial + '\n&mmc0 { status = "okay"; };\n'
        self.assertTrue(guard.validate(self.base, mutated))
        mutated = self.trial + '\n/ { chosen { bootargs = "root=unsafe"; }; };\n'
        self.assertTrue(any("bootargs" in x for x in guard.validate(self.base, mutated)))

    def test_trial_must_keep_mac0_disabled(self):
        mutated = self.trial.replace('&gmac0 {\n\tstatus = "disabled";',
                                     '&gmac0 {\n\tstatus = "okay";', 1)
        self.assertIn("trial: incorrect scope/status gmac0",
                      guard.validate(self.base, mutated))

    def test_no_unreviewed_memory_or_included_payloads(self):
        for payload in ('\n/ { memory@40000000 { reg = <1>; }; };\n',
                        '\n/ { test { data = /incbin/("factory.bin"); }; };\n'):
            self.assertTrue(guard.validate(self.base + payload, self.trial))

    def test_reject_duplicate_reference_block(self):
        self.assertTrue(guard.validate(self.base + '\n&eth { status = "disabled"; };\n',
                                       self.trial))

if __name__ == "__main__":
    unittest.main()
