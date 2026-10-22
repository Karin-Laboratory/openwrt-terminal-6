import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fdt_inventory", ROOT / "tools/inventory_sgmii_fdt.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class TestInventory(unittest.TestCase):
    def test_runtime_nodes(self):
        source = """
/ {
  sgmiisys@11305000 {
    compatible = "mediatek,colgin-sgmiisys_1", "syscon";
    phandle = <0x6e>;
  };
  sgmiiphy@11E60000 {
    compatible = "mediatek,colgin-sgmiisys_phy_1";
    power-domains = <0x23 0x11>;
  };
};
"""
        nodes = tool.inspect(source)["targets"]
        self.assertTrue(nodes["sgmiisys@11305000"]["present"])
        self.assertEqual(nodes["sgmiisys@11305000"]["properties"]["phandle"], "<0x6e>")
        self.assertEqual(nodes["sgmiiphy@11E60000"]["properties"]["power-domains"], "<0x23 0x11>")
    def test_no_nodes(self):
        self.assertFalse(tool.inspect("/ { };")["targets"]["sgmiiphy@11E60000"]["present"])

if __name__ == "__main__":
    unittest.main()
