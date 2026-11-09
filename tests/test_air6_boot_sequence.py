# SPDX-License-Identifier: MIT
import unittest
from tools.boot import air6_boot_sequence as boot


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 64
        self.r = {"partition_bytes": 134217728, "p26_sha256": self.sha}
        self.b = {"expected_p26_sha256": self.sha,
                  "policy": "read-only-sha256-before-switch-root"}
        self.trace = ["AIR6_" + s for s in boot.STAGES]
        self.trace[4] += " PID=1"
        self.trace += ["AIR6_CONFIG_GENERATE_OK", "AIR6_MOUNT_ROOT_CALLED"]

    def test_full_pair_binding_and_trace(self):
        self.assertEqual(boot.bound_pair(self.r, self.b), self.sha)
        self.assertEqual(boot.validate_trace(self.trace)["status"], "OFFLINE_TRACE_ORDER_PASS")

    def test_p26_change_invalidates_old_initramfs(self):
        self.r["p26_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_MISMATCH"):
            boot.bound_pair(self.r, self.b)

    def test_preinit_done_does_not_prove_procd_pid1(self):
        self.trace[4] = "AIR6_PROCD_PID1"
        with self.assertRaisesRegex(ValueError, "BOOT_PROCD_PID1_UNPROVEN"):
            boot.validate_trace(self.trace)

    def test_configuration_hook_once(self):
        self.trace += ["AIR6_CONFIG_GENERATE_OK"]
        with self.assertRaisesRegex(ValueError, "BOOT_CONFIG_GENERATE_ONCE"):
            boot.validate_trace(self.trace)

    def test_bad_order(self):
        self.trace[2], self.trace[3] = self.trace[3], self.trace[2]
        with self.assertRaisesRegex(ValueError, "BOOT_MARKER_ORDER"):
            boot.validate_trace(self.trace)

    def test_target_busybox_applets_and_ram_only(self):
        text = "\n".join(("sh", "sha256sum", "mount", "switch_root",
                          "cat", "grep", "awk"))
        self.assertEqual(len(boot.required_applets(text)), 7)
        with self.assertRaisesRegex(ValueError, "TARGET_BUSYBOX_MISSING_APPLETS"):
            boot.required_applets("sh\nmount")
        self.assertEqual(boot.validate_trace(self.trace[:2], "ram-only")["mode"], "ram-only")


if __name__ == "__main__":
    unittest.main()
