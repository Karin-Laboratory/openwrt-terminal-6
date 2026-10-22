import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit", ROOT / "tools" / "dts_compat_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class TestDtsAudit(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            file = pathlib.Path(temp) / "sample.dts"
            file.write_text('/ { compatible = "vendor,device", "mediatek,mt6990"; };')
            self.assertEqual(audit.parse(file), ["mediatek,mt6990", "vendor,device"])

    def test_compare(self):
        result = audit.compare(["a", "b"], ["b", "c"])
        self.assertEqual(result["shared"], ["b"])
        self.assertEqual(result["target_only"], ["a"])
        self.assertEqual(result["reference_only"], ["c"])

if __name__ == "__main__":
    unittest.main()
