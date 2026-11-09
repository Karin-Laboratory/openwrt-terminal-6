# SPDX-License-Identifier: MIT
"""Synthetic UART transcripts; do not claim these are real QEMU executions."""
import unittest
from pathlib import Path
from tools.boot import check_qemu_p26_ram_boot as check


def lines(markers):
    return "\n".join("[    0.100] " + m for m in markers) + "\n"


class ObservedQemuStagesTests(unittest.TestCase):
    def setUp(self):
        self.positive = [check.KERNEL_PID1, *check.POSITIVE]
        self.negative = [check.KERNEL_PID1, *check.NO_P26]
        self.sha_bad = [check.KERNEL_PID1, *check.SHA_REJECT]

    def test_positive_must_have_real_procd_after_switch_root(self):
        result = check.check_trace(lines(self.positive), "positive")
        self.assertEqual(result["status"], "QEMU_OBSERVED_POSITIVE_PASS")
        self.assertTrue(result["guest_procd_after_switch_root"])
        self.assertFalse(result["air6_hardware_boot_proven"])

    def test_missing_p26_fails_closed_with_actual_pid1(self):
        r = check.check_trace(lines(self.negative), "missing-p26")
        self.assertEqual(r["observed_steps"], 3)
        self.assertFalse(r["guest_procd_after_switch_root"])

    def test_sha_mismatch_blocks_without_mount(self):
        result = check.check_trace(lines(self.sha_bad), "sha-mismatch")
        self.assertEqual(result["status"], "QEMU_OBSERVED_SHA_MISMATCH_PASS")

    def test_order_reversal_does_not_pass(self):
        reordered = self.positive.copy()
        reordered[4], reordered[5] = reordered[5], reordered[4]
        with self.assertRaisesRegex(ValueError, "QEMU_BOOT_MARKER_ORDER"):
            check.check_trace(lines(reordered), "positive")

    def test_missing_or_duplicate_marker_does_not_pass(self):
        for items in (self.positive[:-1],
                      self.positive + [check.POSITIVE[-1]]):
            with self.subTest(items=items), self.assertRaisesRegex(ValueError, "QEMU_BOOT_MARKER_CARDINALITY"):
                check.check_trace(lines(items), "positive")

    def test_marker_without_actual_kernel_init_rejected(self):
        with self.assertRaisesRegex(ValueError, "QEMU_BOOT_MARKER_CARDINALITY"):
            check.check_trace(lines(check.POSITIVE), "positive")

    def test_unexpected_blocker_prevents_positive(self):
        with self.assertRaisesRegex(ValueError, "QEMU_BOOT_UNEXPECTED_BLOCKER"):
            check.check_trace(lines(self.positive +
                                     ["AIR6_BOOT_BLOCKED_UNKNOWN"]), "positive")

    def test_negative_cannot_continue_past_block(self):
        with self.assertRaisesRegex(ValueError, "QEMU_BOOT_FAILED_CLOSED_BUT_ADVANCED"):
            check.check_trace(lines(self.negative +
                                     ["AIR6_SWITCH_ROOT_BEGIN"]), "missing-p26")

    def test_panic_and_exec_failure_never_accepted(self):
        for fatal in check.FATAL[:2]:
            with self.subTest(fatal=fatal), self.assertRaisesRegex(ValueError, "PANIC_OR_LAUNCH"):
                check.check_trace(lines(self.positive + [fatal]), "positive")

    def test_native_workflow_requires_ordered_positive_and_sha_reject(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn('--mode missing-p26', workflow)
        self.assertIn('--mode sha-mismatch', workflow)
        self.assertIn('--mode positive', workflow)
        self.assertIn('PUBLIC_MT6990_QEMU_VIRTIO_POSITIVE_ORDERED_SHA_VERIFIED_PASS', workflow)
        self.assertIn('PUBLIC_MT6990_QEMU_VIRTIO_CORRUPT_P26_SHA_FAILCLOSED_PASS', workflow)
        self.assertIn("original[0] ^ 1", workflow)
        self.assertIn('dst=/CorruptP26,readonly', workflow)
        self.assertIn('dst=/SyntheticP26,readonly', workflow)
        self.assertIn('--network none --read-only', workflow)
        self.assertLess(workflow.index('PUBLIC_MT6990_QEMU_VIRTIO_CORRUPT_P26_SHA_FAILCLOSED_PASS'),
                        workflow.index('PUBLIC_MT6990_QEMU_VIRTIO_P26_RAM_OVERLAY_SWITCHROOT_PROCD_PID1_PASS'))

    def test_wrong_negative_marker_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "QEMU_BOOT_MARKER_CARDINALITY"):
            check.check_trace(lines(self.sha_bad), "missing-p26")


if __name__ == "__main__":
    unittest.main()
