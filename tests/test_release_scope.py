import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/check_release_scope.py"
spec = importlib.util.spec_from_file_location("check_release_scope", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReleaseScopeTests(unittest.TestCase):
    def test_public_tree_is_source_only(self):
        result = mod.evaluate(SCRIPT.parents[1])
        self.assertTrue(result["source_rfc_ready"])
        self.assertFalse(result["firmware_release_ready"])
        self.assertFalse(result["device_install_ready"])
        self.assertTrue(any("Device Tree" in x for x in result["blockers"]))

    def test_missing_patch_blocks_source_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "board").mkdir()
            (root / "board/air-terminal-6.json").write_text(
                json.dumps({"status": "experimental-evidence-only",
                            "board_dts": "NOT_YET_AVAILABLE"}))
            result = mod.evaluate(root)
            self.assertFalse(result["source_rfc_ready"])
            self.assertEqual(len(result["source_rfc_missing"]), 2)
            self.assertFalse(result["firmware_release_ready"])


if __name__ == "__main__":
    unittest.main()
