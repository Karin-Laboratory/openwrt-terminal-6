import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "validate_candidate_dts.py"
spec = importlib.util.spec_from_file_location("validate_candidate_dts", MODULE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CandidateDtsIncludeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("dtc"), "dtc is required")
    def test_board_dts_resolves_local_soc_include(self):
        result = validator.validate(ROOT / "board" / "sbat6d-incomplete.dts")
        self.assertTrue(result["pass"], result)

    @unittest.skipUnless(shutil.which("dtc"), "dtc is required")
    def test_missing_include_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            board = Path(temp)
            source = board / "board.dts"
            source.write_text('/dts-v1/;\n/include/ "missing.dtsi"\n/ {};\n')
            result = validator.validate(source)
            self.assertFalse(result["pass"])


if __name__ == "__main__":
    unittest.main()
