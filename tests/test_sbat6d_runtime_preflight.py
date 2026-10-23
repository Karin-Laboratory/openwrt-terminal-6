import importlib.util
import sys
from pathlib import Path
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("preflight_sbat6d_runtime_dts", TOOLS / "preflight_sbat6d_runtime_dts.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RuntimeDtsPreflightTests(unittest.TestCase):
    def test_absent_nodes_are_reported(self):
        result = mod.assess("/dts-v1/; / { };")
        self.assertEqual(len(result["missing"]), 2)
        self.assertEqual(result["status"], "TEXT_INVENTORY_ONLY")

    def test_present_nodes_still_not_approved(self):
        dts = '/ { sgmiisys@11305000 { compatible = "syscon"; }; sgmiiphy@11E60000 { compatible = "syscon"; }; };'
        result = mod.assess(dts)
        self.assertFalse(result["missing"])
        self.assertEqual(result["status"], "TEXT_INVENTORY_ONLY")

if __name__ == "__main__":
    unittest.main()
