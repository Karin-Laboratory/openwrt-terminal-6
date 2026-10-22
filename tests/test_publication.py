"""Small self-contained tests for publication checks."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util

spec = importlib.util.spec_from_file_location("check_publication", ROOT / "scripts" / "check-publication.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class TestPublication(unittest.TestCase):
    def test_blocked_suffixes(self):
        self.assertIn(".img", checker.BLOCK_SUFFIX)
        self.assertIn(".pem", checker.BLOCK_SUFFIX)

    def test_sensitive_directories(self):
        self.assertIn("originals", checker.BLOCK_PARTS)
        self.assertIn("vendor-dumps", checker.BLOCK_PARTS)

    def test_blocked_names(self):
        self.assertIn(".env", checker.BLOCK_NAMES)
        self.assertIn("credentials", checker.BLOCK_NAMES)

if __name__ == "__main__":
    unittest.main()
