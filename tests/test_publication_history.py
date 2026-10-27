# SPDX-License-Identifier: MIT
"""Run synthetic history tests with local temporary repos; no secrets or network."""
from pathlib import Path
import importlib.util
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "public_gate_history", ROOT / "tools/security/check_publication.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def git(root, *args):
    subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True
    )

class HistoryScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        self.original = gate.ROOT
        gate.ROOT = self.root
        self.addCleanup(setattr, gate, "ROOT", self.original)

    def commit(self, message):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", message)

    def test_deleted_historical_image_is_still_blocked(self):
        p = self.root / "temporary.img"
        p.write_bytes(b"synthetic bytes")
        self.commit("temporary synthetic image")
        p.unlink()
        (self.root / "README.md").write_text("harmless\n")
        self.commit("remove image")
        issues = set()
        self.assertGreater(gate.history_findings(issues), 0)
        self.assertIn(("temporary.img", "restricted artifact filename/type"), issues)

    def test_same_blob_different_path_detects_risky_alias(self):
        data = b"same harmless content\n"
        (self.root / "safe.txt").write_bytes(data)
        self.commit("safe file")
        (self.root / "other.img").write_bytes(data)
        self.commit("same blob under forbidden name")
        issues = set()
        gate.history_findings(issues)
        self.assertIn(("other.img", "restricted artifact filename/type"), issues)

    def test_symlink_is_reviewed(self):
        (self.root / "file.txt").write_text("ok\n")
        os.symlink("file.txt", self.root / "alias")
        self.commit("synthetic symlink")
        issues = set()
        gate.history_findings(issues)
        self.assertIn(("alias", "symlink requires manual review"), issues)

    def test_sensitive_commit_message_is_detected(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("PASS" + "WORD=synthetic_demo_value_not_real")
        issues = set()
        gate.history_findings(issues)
        self.assertTrue(any(category == "potential embedded credential"
                            for _, category in issues))

    def test_annotated_tag_body_is_detected(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        git(self.root, "tag", "-a", "v0", "-m", "PASS" + "WORD=synthetic_demo_value_not_real")
        issues = set()
        gate.history_findings(issues)
        self.assertTrue(any(path.startswith("@tag/") and
                            category == "potential embedded credential"
                            for path, category in issues))

    def test_benign_history_stays_clean(self):
        (self.root / "first.txt").write_text("hello\n")
        self.commit("first safe document")
        (self.root / "second.txt").write_text("world\n")
        self.commit("second safe document")
        issues = set()
        self.assertGreater(gate.history_findings(issues), 0)
        self.assertEqual(issues, set())

if __name__ == "__main__":
    unittest.main()
