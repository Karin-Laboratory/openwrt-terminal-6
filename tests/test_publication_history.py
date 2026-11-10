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

    def test_public_ref_name_with_synthetic_token_is_blocked_without_echo(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        # Assemble the synthetic token so no token-shaped fixture is committed.
        fake_token = "ghp_" + "A" * 35
        git(self.root, "branch", "audit-" + fake_token)
        issues = set()
        gate.history_findings(issues)
        self.assertTrue(any(path.startswith("@ref/") and
                            category == "cloud access token"
                            for path, category in issues), issues)
        self.assertNotIn(fake_token, repr(issues))

    def test_replace_ref_fails_closed_before_history_traversal(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root
        ).decode().strip()
        # A synthetic self-replacement makes normal Git traversal fail.
        # Reject it explicitly before rev-list can hide/replace any object.
        git(self.root, "update-ref", "refs/replace/" + head, head)
        with self.assertRaisesRegex(ValueError, "replace ref"):
            gate.history_findings(set())

    def test_lightweight_tag_to_uncommitted_blob_is_blocked(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        (self.root / "uncommitted.txt").write_text("synthetic only\\n")
        blob = subprocess.check_output(
            ["git", "hash-object", "-w", "uncommitted.txt"], cwd=self.root
        ).decode().strip()
        git(self.root, "tag", "blob-target", blob)
        with self.assertRaisesRegex(ValueError, "non-commit Git ref"):
            gate.history_findings(set())

    def test_annotated_tag_to_tree_is_blocked(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        tree = subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=self.root
        ).decode().strip()
        git(self.root, "tag", "-a", "tree-target", "-m", "synthetic", tree)
        with self.assertRaisesRegex(ValueError, "non-commit Git ref"):
            gate.history_findings(set())

    def test_annotated_tag_object_under_custom_ref_is_scanned(self):
        (self.root / "safe.txt").write_text("safe\\n")
        self.commit("safe commit")
        # An annotated tag object can remain reachable outside refs/tags
        # after its normal tag ref is deleted. Its message must be audited.
        git(self.root, "tag", "-a", "temporary", "-m",
            "PASS" + "WORD=synthetic_demo_value_not_real")
        tag_sha = subprocess.check_output(
            ["git", "rev-parse", "refs/tags/temporary"], cwd=self.root
        ).decode().strip()
        git(self.root, "update-ref", "refs/audit/retained-tag", tag_sha)
        git(self.root, "tag", "-d", "temporary")
        issues = set()
        gate.history_findings(issues)
        self.assertTrue(any(path.startswith("@tag/") and
                            category == "potential embedded credential"
                            for path, category in issues), issues)

    def test_sensitive_filename_in_history_is_detected_without_echo(self):
        fake_token = "ghp_" + "A" * 35
        (self.root / (fake_token + ".txt")).write_text("harmless\\n")
        self.commit("synthetic filename metadata")
        issues = set()
        gate.history_findings(issues)
        self.assertTrue(any(path.startswith("@path/") and
                            category == "path metadata: cloud access token"
                            for path, category in issues), issues)
        self.assertNotIn(fake_token, repr(issues))

    def test_sensitive_current_path_retains_artifact_type_check(self):
        fake_name = "PASS" + "WORD=synthetic_value_not_real.img"
        (self.root / fake_name).write_bytes(b"harmless\\n")
        self.commit("synthetic filename and restricted extension")
        issues = set()
        gate.current_findings(issues)
        self.assertTrue(any(path.startswith("@path/") and
                            category == "path metadata: potential embedded credential"
                            for path, category in issues), issues)
        self.assertTrue(any(path.startswith("@path/") and
                            category == "restricted artifact filename/type"
                            for path, category in issues), issues)
        self.assertNotIn(fake_name, repr(issues))

    def test_only_documented_generic_lan_profile_address_is_exempt(self):
        path = "config/sbat6-stage/usr/libexec/sba6d/rc14-management.sh"
        gateway = b"192.168." + b"1.1"
        different = b"192.168." + b"7.71"
        findings = set()
        gate.scan(path, b"bind " + gateway + b":22", findings)
        self.assertEqual(findings, set())
        gate.scan(path, b"bind " + gateway + b"; peer " + different, findings)
        self.assertIn((path, "private network endpoint"), findings)
        findings.clear()
        gate.scan("other-script.sh", b"bind " + gateway + b":22", findings)
        self.assertIn(("other-script.sh", "private network endpoint"), findings)
        findings.clear()
        gate.scan(path, b"root@" + gateway, findings)
        self.assertIn((path, "device login endpoint"), findings)
        findings.clear()
        gate.scan("tests/test_public_rc14_management.py",
                  b"literal " + gateway, findings)
        self.assertEqual(findings, set())

    def test_historical_waivers_are_exact_blob_identifiers_only(self):
        self.assertEqual(len(gate.KNOWN_PUBLIC_FIXTURE_BLOBS), 2)
        self.assertIn(("tools/security/check_publication.py",
                       "20339d624278a436450d35cd1ce0066713816bcc"),
                      gate.KNOWN_PUBLIC_FIXTURE_BLOBS)
        self.assertIn(("tests/test_publication_history.py",
                       "bef753648c68721448bdd83d73e0b79cf3082efa"),
                      gate.KNOWN_PUBLIC_FIXTURE_BLOBS)
        # Test fixture source revisions are never a global source/path waiver:
        # an unrelated endpoint under the same path must be rejected.
        token = b"10." + b"2.3.4"
        problems = set()
        gate.scan("tests/test_publication_history.py", b"peer " + token, problems)
        self.assertIn(("tests/test_publication_history.py",
                       "private network endpoint"), problems)

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
