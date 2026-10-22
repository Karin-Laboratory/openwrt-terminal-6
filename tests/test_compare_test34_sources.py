"""Fail-closed tests for local-only Test32/Test34 comparison metadata."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location(
    "compare_test34", ROOT / "tools/compare_test34_sources.py"
)
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


class CompareTest34Tests(unittest.TestCase):
    def test_missing_sources_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(compare.summarize(Path(directory), Path(directory)))

    def test_incorrect_sources_rejected_without_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for filename in compare.FILES:
                (path / filename).write_text("synthetic sample, not original source\n")
            self.assertFalse(compare.summarize(path, path))


if __name__ == "__main__":
    unittest.main()
