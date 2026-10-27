# SPDX-License-Identifier: MIT
"""Synthetic, read-only A/B metadata tests; not bootloader verification."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "slot_observation", ROOT / "tools/boot/slot_observation.py"
)
mod = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class SlotObservationTests(unittest.TestCase):
    def test_observed_priority_does_not_prove_fallback(self):
        a = mod.SlotObservation("A", 14, 0, False)
        b = mod.SlotObservation("B", 15, 0, True)
        summary = mod.summarize(a, b)
        self.assertEqual(summary["priority_field_order"], "B higher priority field")
        self.assertEqual(summary["successful_flags"], ["B"])
        self.assertFalse(summary["fallback_proven"])
        self.assertFalse(summary["safe_to_switch"])

    def test_reject_identifying_extra_fields(self):
        with self.assertRaisesRegex(ValueError, "unexpected"):
            mod.from_sanitized_fields({
                "label":"A", "priority":1, "tries_remaining":0,
                "successful":False, "imei":"synthetic-not-a-device",
            })

    def test_reject_boolean_priority_and_out_of_range_retry(self):
        for priority in (True, -1, 16, "15"):
            with self.assertRaises(ValueError):
                mod.SlotObservation("A", priority, 0, False)
        with self.assertRaises(ValueError):
            mod.SlotObservation("B", 15, 8, True)

    def test_pair_order_must_be_explicit(self):
        a = mod.SlotObservation("A", 0, 0, False)
        b = mod.SlotObservation("B", 0, 0, False)
        with self.assertRaises(ValueError):
            mod.summarize(b, a)
        self.assertEqual(mod.summarize(a, b)["priority_field_order"],
                         "equal priority fields")

if __name__ == "__main__":
    unittest.main()
