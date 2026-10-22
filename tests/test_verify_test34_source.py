"""Tests for the public, read-only Test34 source identity verifier."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_test34", ROOT / "tools/verify_test34_source.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class SourceIdentityTests(unittest.TestCase):
    def test_reported_digests_are_full_sha256(self):
        for pair in verifier.DIGESTS.values():
            self.assertEqual(set(pair), {"mtk_eth_soc.c", "mtk_eth_soc.h"})
            for value in pair.values():
                self.assertEqual(len(value), 64)
                self.assertTrue(all(ch in "0123456789abcdef" for ch in value))

    def test_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(verifier.verify(Path(directory), "test32"))

    def test_mismatched_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename in ("mtk_eth_soc.c", "mtk_eth_soc.h"):
                (Path(directory) / filename).write_text("synthetic mismatch only")
            self.assertFalse(verifier.verify(Path(directory), "test34"))


if __name__ == "__main__":
    unittest.main()
