import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("resolve", ROOT / "tools/resolve_fdt_phandles.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class TestResolve(unittest.TestCase):
    def test_three_providers(self):
        dts = """
/ {
    clock@0 {
        phandle = <0x24>;
    };
    sgmiisys@0 {
        phandle = <0x6d>;
    };
    sgmiisys@1 {
        linux,phandle = <0x6e>;
    };
};
"""
        report = tool.resolve(dts)
        self.assertTrue(all(x["status"] == "resolved" for x in report.values()))
        self.assertEqual(report["0x24"]["matches"][0]["node"], "/clock@0")
    def test_duplicate_fails(self):
        dts = "/ {\n a {\n phandle = <0x6d>;\n };\n b {\n phandle = <0x6d>;\n };\n};"
        self.assertEqual(tool.resolve(dts)["0x6d"]["status"], "duplicate")
    def test_legacy_alias_same_node(self):
        dts = "/ {\n a {\n phandle = <0x6d>;\n linux,phandle = <0x6d>;\n };\n};"
        result = tool.resolve(dts)["0x6d"]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(len(result["matches"]), 1)

    def test_missing_fails(self):
        self.assertEqual(tool.resolve("/ { };")["0x24"]["status"], "missing")

if __name__ == "__main__":
    unittest.main()
