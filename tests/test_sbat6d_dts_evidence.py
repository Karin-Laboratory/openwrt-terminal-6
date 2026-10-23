import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/check_sbat6d_dts_evidence.py"
spec = importlib.util.spec_from_file_location("check_sbat6d_dts_evidence", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DtsEvidenceTests(unittest.TestCase):
    def test_empty_rejected(self):
        result = mod.audit({"checks": {}})
        self.assertFalse(result["ready_for_board_dts_review"])
        self.assertEqual(len(result["blocked"]), len(mod.REQUIRED))

    def test_evidence_required_for_every_check(self):
        data = {"checks": {name: {"status": "verified", "evidence": "source-reviewed"}
                           for name in mod.REQUIRED}}
        self.assertTrue(mod.audit(data)["ready_for_board_dts_review"])
        data["checks"]["clock_providers_and_ids"]["evidence"] = None
        self.assertFalse(mod.audit(data)["ready_for_board_dts_review"])

if __name__ == "__main__":
    unittest.main()
