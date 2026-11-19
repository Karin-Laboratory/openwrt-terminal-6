import unittest
from scripts.air6_ethernet_dts_preflight import validate

GOOD = """
&netsys { compatible = "mediatek,mt6990-netsys", "simple-bus";
#address-cells = <2>; #size-cells = <2>; ranges; status = "okay"; };
&eth { clocks = <&topckgen 1>, <&topckgen 2>;
clock-names = "a", "b";
interrupts-extended = <&gic 1>, <&gic 2>, <&gic 3>, <&gic 4>, <&gic 5>, <&gic 6>, <&pio 7>, <&pio 8>;
status = "okay"; };
&sgmiisys1 { status = "okay"; };
&gmac0 { status = "disabled"; };
&gmac1 { status = "okay"; };
"""
class SourcePreflightTests(unittest.TestCase):
    def test_valid_synthetic(self):
        self.assertEqual(validate(GOOD), [])
    def test_missing_clock(self):
        self.assertTrue(any("clock/name" in x for x in validate(GOOD.replace('<&topckgen 2>', '<&other 2>'))))
    def test_missing_irq(self):
        self.assertTrue(any("8 IRQ" in x for x in validate(GOOD.replace(', <&pio 8>', ''))))
    def test_wrong_mac(self):
        self.assertTrue(any("gmac0" in x for x in validate(GOOD.replace('status = "disabled"', 'status = "okay"'))))
if __name__ == "__main__":
    unittest.main()
