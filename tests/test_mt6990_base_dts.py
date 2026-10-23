import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "board" / "sbat6d-incomplete.dts"


@unittest.skipUnless(shutil.which("dtc") and shutil.which("fdtget"),
                     "dtc and fdtget are required")
class Mt6990BaseDtsTests(unittest.TestCase):
    def test_observed_cpu_psci_gic_and_timer_data_compile(self):
        with tempfile.TemporaryDirectory() as temp:
            dtb = Path(temp) / "sbat6d.dtb"
            subprocess.run([
                "dtc", "-I", "dts", "-O", "dtb", "-i", str(ROOT / "board"),
                "-o", str(dtb), str(BOARD),
            ], check=True, capture_output=True, text=True)

            compatible = subprocess.check_output(
                ["fdtget", str(dtb), "/", "compatible"], text=True
            ).split()
            self.assertEqual(compatible, [
                "mediatek,evb6990_cpe_mt7990_emmc", "mediatek,mt6990"
            ])

            cpus = subprocess.check_output(
                ["fdtget", "-l", str(dtb), "/cpus"], text=True
            ).split()
            self.assertEqual(cpus, ["cpu@0", "cpu@100", "cpu@200", "cpu@300"])
            mpidrs = [subprocess.check_output(
                ["fdtget", "-t", "x", str(dtb), f"/cpus/{cpu}", "reg"],
                text=True,
            ).strip() for cpu in cpus]
            self.assertEqual(mpidrs, ["0", "100", "200", "300"])

            gic_reg = subprocess.check_output(
                ["fdtget", "-t", "x", str(dtb),
                 "/interrupt-controller@c000000", "reg"], text=True
            ).split()
            self.assertEqual(gic_reg, ["0", "c000000", "0", "40000",
                                       "0", "c040000", "0", "200000"])
            timer_irqs = subprocess.check_output(
                ["fdtget", "-t", "x", str(dtb), "/timer", "interrupts"],
                text=True,
            ).split()
            self.assertEqual(timer_irqs,
                             ["1", "d", "4", "1", "e", "4",
                              "1", "b", "4", "1", "a", "4"])

            psci = subprocess.check_output(
                ["fdtget", str(dtb), "/psci", "compatible"], text=True
            ).strip()
            self.assertEqual(psci, "arm,psci-1.0")

    def test_partial_tree_does_not_assert_ambiguous_memory_map(self):
        source = (ROOT / "board" / "mt6990.dtsi").read_text()
        self.assertNotIn("memory@", source)
        self.assertNotIn("reserved-memory", source)


if __name__ == "__main__":
    unittest.main()
