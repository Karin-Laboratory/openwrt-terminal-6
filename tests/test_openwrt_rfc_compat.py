import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/check_openwrt_rfc_compat.py"
spec = importlib.util.spec_from_file_location("check_openwrt_rfc_compat", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CompatTests(unittest.TestCase):
    def test_missing_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result = mod.check(Path(d))
            self.assertFalse(result["rfc1_rfc2_direct_apply_eligible"])
            self.assertTrue(all(v["state"] == "missing" for v in result["kernel_tree_files"].values()))

    def test_different_blob_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in mod.FILES:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("not the pinned source")
            result = mod.check(root)
            self.assertFalse(result["rfc1_rfc2_direct_apply_eligible"])
            self.assertTrue(all(v["state"] == "different" for v in result["kernel_tree_files"].values()))

    def test_git_blob_calculation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / next(iter(mod.FILES))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"hello\n")
            result = mod.check(root)
            expected = hashlib.sha1(b"blob 6" + bytes([0]) + b"hello\n").hexdigest()
            self.assertEqual(result["kernel_tree_files"][next(iter(mod.FILES))]["git_blob"], expected)

if __name__ == "__main__":
    unittest.main()
