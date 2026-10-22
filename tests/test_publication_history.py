# SPDX-License-Identifier: MIT
"""Regression tests for read-only Git-history publication checks."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "publication_history", ROOT / "scripts/check-publication-history.py"
)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class HistoryScreenTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo,
                              check=True, capture_output=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "CI Fixture")
        self.git("config", "user.email", "ci-fixture@example.invalid")
        self.previous_root = scanner.ROOT
        scanner.ROOT = self.repo

    def tearDown(self):
        scanner.ROOT = self.previous_root
        self.temp.cleanup()

    def commit(self, name, content):
        file = self.repo / name
        file.write_text(content)
        self.git("add", name)
        self.git("commit", "-qm", "fixture")

    def scan(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return scanner.main()

    def test_clean_text_history(self):
        self.commit("notes.txt", "safe sample text\n")
        self.assertEqual(self.scan(), 0)

    def test_quoted_pem_marker_is_not_a_secret(self):
        # A line of source-code text quoting a marker is not a PEM block.
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.commit("notes.txt", 'example = "' + marker + '"\\n')
        self.assertEqual(self.scan(), 0)

    def test_deleted_sensitive_name_remains_blocked(self):
        self.commit("secret.key", "placeholder only, no actual secret\n")
        self.git("rm", "secret.key")
        self.git("commit", "-qm", "remove fixture")
        self.assertEqual(self.scan(), 1)

    def test_deleted_private_key_content_remains_blocked(self):
        # A synthetic token marker, never real signing material.
        self.commit("ordinary.txt", "-----BEGIN " + "PRIVATE KEY-----\n" + "A"*64 + "\n-----END " + "PRIVATE KEY-----\n")
        self.git("rm", "ordinary.txt")
        self.git("commit", "-qm", "remove sensitive content fixture")
        self.assertEqual(self.scan(), 1)

    def test_deleted_binary_content_remains_blocked(self):
        binary = self.repo / "ordinary.txt"
        binary.write_bytes(b"test\0binary")
        self.git("add", "ordinary.txt")
        self.git("commit", "-qm", "binary fixture")
        self.git("rm", "ordinary.txt")
        self.git("commit", "-qm", "remove binary fixture")
        self.assertEqual(self.scan(), 1)

    def test_renamed_sensitive_name_remains_blocked(self):
        self.commit("private.pem", "placeholder only\n")
        self.git("mv", "private.pem", "notes.txt")
        self.git("commit", "-qm", "rename fixture")
        self.assertEqual(self.scan(), 1)


if __name__ == "__main__":
    unittest.main()
