import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sgmii", ROOT / "tools/audit_sgmii_dts.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestSgmii(unittest.TestCase):
    def test_missing(self):
        report = module.audit("/dts-v1/; / { };")
        self.assertFalse(report["nodes"]["/sgmiisys@11305000"]["present"])

    def test_incomplete(self):
        text = '/sgmiisys@11305000 { compatible = "x"; status = "disabled"; };'
        report = module.audit(text)["nodes"]["/sgmiisys@11305000"]
        self.assertTrue(report["present"])
        self.assertIn("phys", report["missing"])
        self.assertEqual(report["status"], "disabled")

if __name__ == "__main__":
    unittest.main()
