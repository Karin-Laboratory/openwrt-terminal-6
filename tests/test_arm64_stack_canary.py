from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Arm64StackCanaryTests(unittest.TestCase):
    def test_kernel_stack_protector_uses_supported_arm64_per_task_abi(self):
        patch = (ROOT / "integration/mt6990-target.patch").read_text()
        self.assertIn("+CONFIG_STACKPROTECTOR=y", patch)
        self.assertIn("+CONFIG_CC_HAVE_STACKPROTECTOR_SYSREG=y", patch)
        self.assertIn("+CONFIG_STACKPROTECTOR_PER_TASK=y", patch)
        self.assertIn("-# CONFIG_STACKPROTECTOR_PER_TASK is not set", patch)

    def test_integrated_uart_binding_patch_tracks_observed_compatible(self):
        patch = (ROOT / "integration/mt6990-target.patch").read_text()
        self.assertIn("981-dt-bindings-serial-mediatek-add-observed-mt6873-uart-compatible.patch", patch)
        self.assertIn("+              - mediatek,mt6873-uart", patch)

    def test_ci_matches_external_module_flags_to_effective_kernel_abi(self):
        workflow = (ROOT / ".github/workflows/mt6990-target-build.yml").read_text()
        self.assertIn("CONFIG_STACKPROTECTOR=y", workflow)
        self.assertIn("CONFIG_STACKPROTECTOR_PER_TASK=y", workflow)
        self.assertIn("CONFIG_CC_HAVE_STACKPROTECTOR_SYSREG=y", workflow)
        self.assertIn("Kconfig did not enable it", workflow)
        self.assertIn("if ! grep -qx 'CONFIG_STACKPROTECTOR_PER_TASK=y'", workflow)
        self.assertIn("-mstack-protector-guard=sysreg", workflow)
        self.assertIn("TSK_STACK_CANARY", workflow)
        self.assertNotIn("-mstack-protector-guard=global", workflow)
        self.assertNotIn("__stack_chk_guard", workflow)
        self.assertIn("target-aarch64_generic_musl/linux-mediatek_mt6990/linux-6.18.55", workflow)
        self.assertIn("HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++", workflow)

    def test_direct_kernel_kbuild_calls_keep_the_cross_compiler(self):
        workflow = (ROOT / ".github/workflows/mt6990-target-build.yml").read_text()
        lines = workflow.splitlines()
        invocations = []
        i = 0
        while i < len(lines):
            if 'make -C "$tree"' not in lines[i]:
                i += 1
                continue
            command = [lines[i]]
            while command[-1].rstrip().endswith("\\") and i + 1 < len(lines):
                i += 1
                command.append(lines[i])
            invocations.append(" ".join(command))
            i += 1
        self.assertGreaterEqual(len(invocations), 5)
        for command in invocations:
            with self.subTest(command=command[:100]):
                self.assertIn('CC="$cc"', command)
                self.assertIn('CROSS_COMPILE="$cross"', command)


if __name__ == "__main__":
    unittest.main()
