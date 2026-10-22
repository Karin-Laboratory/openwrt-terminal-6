import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sgmii_phandle", ROOT / "tools/check_sgmii_phandles.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

VALID = """
/dts-v1/;
/ {
  sgmiisys@11305000 {
    phys = <&phy1>;
    phy-names = "sgmii";
  };
  phy1: sgmiiphy@11E60000 {
    mediatek,sgmii-pll = <&pll>;
    mediatek,spm = <&spm>;
    power-domains = <&spm 1>;
  };
};
"""

class TestSgmiiPhandle(unittest.TestCase):
    def test_reference_present(self):
        self.assertEqual(tool.check(VALID), [])
    def test_missing_provider_reference(self):
        self.assertTrue(tool.check(VALID.replace("&phy1", "&missing")))
    def test_missing_power_dependency(self):
        self.assertTrue(tool.check(VALID.replace("power-domains = <&spm 1>;", "")))
    def test_missing_nodes(self):
        self.assertTrue(tool.check("/dts-v1/; / { };"))

if __name__ == "__main__":
    unittest.main()
