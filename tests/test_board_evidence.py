import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("board_evidence", ROOT/"tools/validate_board_evidence.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class BoardEvidenceTests(unittest.TestCase):
    def test_current(self):
        data = json.loads((ROOT/"board/air-terminal-6.json").read_text())
        self.assertEqual(tool.validate(data), [])
    def test_unverified_6ghz(self):
        data = json.loads((ROOT/"board/air-terminal-6.json").read_text())
        data["wifi"]["confirmed_bands_ghz"].append(6)
        self.assertTrue(tool.validate(data))

if __name__ == "__main__":
    unittest.main()
