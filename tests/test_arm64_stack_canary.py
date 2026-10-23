from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Arm64StackCanaryTests(unittest.TestCase):
    def test_mt6990_kernel_config_keeps_per_task_stack_protector(self):
        patch = (ROOT / "integration/mt6990-target.patch").read_text()
        self.assertIn("+CONFIG_STACKPROTECTOR_PER_TASK=y", patch)

    def test_integrated_uart_binding_patch_tracks_observed_compatible(self):
        patch = (ROOT / "integration/mt6990-target.patch").read_text()
        self.assertIn("981-dt-bindings-serial-mediatek-add-observed-mt6873-uart-compatible.patch", patch)
        self.assertIn("+              - mediatek,mt6873-uart", patch)

    def test_ci_recreates_and_checks_kernel_canary_offset(self):
        workflow = (ROOT / ".github/workflows/mt6990-target-build.yml").read_text()
        self.assertIn("CONFIG_STACKPROTECTOR_PER_TASK=y", workflow)
        self.assertIn("HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++", workflow)
        self.assertIn("make -C \"$tree\" ARCH=arm64", workflow)
        self.assertIn("TSK_STACK_CANARY", workflow)
        self.assertIn('echo "Per-task arm64 stack-canary flags', workflow)


if __name__ == "__main__":
    unittest.main()
