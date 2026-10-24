import importlib.util
import sys
from pathlib import Path
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("report_sbat6d_dts_evidence", TOOLS / "report_sbat6d_dts_evidence.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

class DtsReportTests(unittest.TestCase):
    def test_missing_evidence_report_has_all_blockers(self):
        data = {"checks": {}}
        text = report.render(data)
        self.assertIn("Ready for DTS review:** NO", text)
        self.assertEqual(text.count("| BLOCKED |"), len(report.REQUIRED))

    def test_badly_formed_checks_do_not_crash(self):
        result = report.render({"checks": None})
        self.assertIn("Ready for DTS review:** NO", result)

if __name__ == "__main__":
    unittest.main()
