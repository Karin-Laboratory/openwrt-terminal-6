import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "board/mt6990-observed-peripherals.dtsi"


def node_body(source: str, node_name: str) -> str:
    match = re.search(rf"(?m)^\s*(?:[A-Za-z0-9_]+:\s*)?{re.escape(node_name)}\s*\{{", source)
    if not match:
        raise AssertionError(f"missing node {node_name}")
    start = source.find("{", match.start())
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"unterminated node {node_name}")


class ObservedPeripheralDtsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()

    def test_observed_peripherals_stay_disabled(self):
        nodes = [
            "serial@11002000", "mmc@11230000", "pcie@11280000",
            "pcie@11288000", "pcie@11290000", "netsys@15100000",
            "syscon@11036000", "syscon@10000000", "syscon@1200C000",
            "syscon@12013000", "power-controller@12001000",
            "sgmiisys@11305000", "sgmiiphy@11E60000", "sgmiipll@10014000",
        ]
        for name in nodes:
            with self.subTest(node=name):
                self.assertRegex(node_body(self.source, name), r'\bstatus\s*=\s*"disabled"')

    def test_pcie_phy_links_and_domains_are_recorded(self):
        for i, addr in enumerate(("11310000", "11e00000", "11e20000")):
            with self.subTest(domain=i):
                body = node_body(self.source, f"pcie@{('11280000','11288000','11290000')[i]}")
                self.assertIn(f"phys = <&pcie_phy{i}>", body)
                phy = node_body(self.source, f"pcie_phy{i}: phy@{addr}")
                self.assertIn(f"phy-id = <{i}>", phy)

    def test_ethsys_reset_provider_is_recorded_but_disabled(self):
        ethsys = node_body(self.source, "ethsys: ethsys@15000000")
        self.assertRegex(ethsys, r'\bstatus\s*=\s*"disabled"')
        reset = node_body(self.source, "reset-controller")
        self.assertIn('compatible = "ti,syscon-reset"', reset)
        self.assertIn("#reset-cells = <1>", reset)
        self.assertIn("ti,reset-bits = <0x34 0x04 0x34 0x04 0x34 0x04 0x28>", reset)
        self.assertRegex(reset, r'\bstatus\s*=\s*"disabled"')

    def test_no_ram_range_is_selected(self):
        board = (ROOT / "board/sbat6d-incomplete.dts").read_text()
        self.assertNotRegex(board + self.source, r"memory(?:@80000000)?\s*\{")
        facts = (ROOT / "board/DT-HARDWARE-FACTS.md").read_text()
        self.assertIn("0x3e605000", facts)
        self.assertIn("0x1e800000", facts)

    def test_firmware_specific_sgmii_lists_are_not_encoded_as_phandles(self):
        for prop in (
            "mediatek,sgmiisys =", "mediatek,sgmiisys_phy =",
            "mediatek,sgmiisys_uxphy =", "mediatek,sgmii_pll =",
        ):
            with self.subTest(property=prop):
                self.assertNotIn(prop, self.source)
        facts = (ROOT / "board/DT-HARDWARE-FACTS.md").read_text()
        self.assertIn("not a standard", facts)


if __name__ == "__main__":
    unittest.main()
