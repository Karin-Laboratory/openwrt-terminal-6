import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "tools/check_openwrt_kernel_version.py"
spec = importlib.util.spec_from_file_location("check_openwrt_kernel_version", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class KernelVersionTests(unittest.TestCase):
    def test_version_cannot_substitute_blob_check(self):
        for source in ("LINUX_VERSION:=6.18\n", "LINUX_VERSION-6.12 = .99\n", ""):
            result = mod.inspect(source)
            self.assertFalse(result["can_claim_direct_rfc_compatibility"])
            self.assertTrue(result["requires_exact_blob_match"])

if __name__ == "__main__":
    unittest.main()
