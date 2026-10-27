# SPDX-License-Identifier: MIT
"""Hardware-free regression checks for competing LK fallback hypotheses."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ab_hypotheses", ROOT / "tools/boot/ab_fallback_hypotheses.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ABHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.a = mod.Slot("A", 15, 3, False, False)
        self.b = mod.Slot("B", 14, 0, True, True)

    def test_retry_polices_disagree(self):
        outcome = mod.compare_policies(self.a, self.b, cycles=2)
        self.assertFalse(outcome["fallback_proven"])
        self.assertFalse(outcome["safe_to_modify_device"])
        traces = outcome["traces"]
        self.assertEqual(traces["ignore_counter"][0]["retries"], (3, 0))
        self.assertEqual(traces["decrement_on_selection"][0]["retries"], (2, 0))
        self.assertEqual(traces["decrement_on_failure"][0]["retries"], (2, 0))

    def test_exhausted_retry_does_not_magically_trigger_fallback(self):
        a = mod.Slot("A", 15, 0, False, False)
        for policy in mod.RetryPolicy:
            _, _, selected, accepted = mod.step(a, self.b, policy)
            self.assertEqual(selected, "A")
            self.assertFalse(accepted)

    def test_observations_unchanged(self):
        original = self.a
        mod.compare_policies(self.a, self.b, cycles=4)
        self.assertEqual(self.a, original)
        self.assertEqual(original.retries, 3)

    def test_priority_zero_selects_none(self):
        a = mod.Slot("A", 0, 0, False, False)
        b = mod.Slot("B", 0, 0, False, False)
        _, _, selected, accepted = mod.step(a, b, mod.RetryPolicy.IGNORE_COUNTER)
        self.assertIsNone(selected)
        self.assertFalse(accepted)

    def test_reject_bool_and_out_of_bounds(self):
        with self.assertRaises(ValueError):
            mod.Slot("A", True, 0, False, False)
        with self.assertRaises(ValueError):
            mod.Slot("A", 15, 8, False, False)
        with self.assertRaises(ValueError):
            mod.compare_policies(self.a, self.b, cycles=100)


if __name__ == "__main__":
    unittest.main()
