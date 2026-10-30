# SPDX-License-Identifier: MIT
"""Synthetic checks for conservative publication gate; no real secrets or endpoints."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "public_gate", ROOT / "tools/security/check_publication.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class PublicationGateTests(unittest.TestCase):
    def test_scanner_uses_repository_root(self):
        self.assertEqual(gate.ROOT, ROOT)

    def test_safe_source(self):
        issues = set()
        gate.scan("examples/reference.c", b"int main(void){return 0;}\n", issues)
        self.assertEqual(issues, set())

    def test_restricted_artifact(self):
        issues = set()
        gate.scan("out/build" + ".img", b"data", issues)
        self.assertIn(("out/build.img", "restricted artifact filename/type"), issues)

    def test_secret_match_never_echoes_content(self):
        issues = set()
        sample = b"-----BEGIN " + b"PRIVATE " + b"KEY-----"
        gate.scan("notes/a.txt", sample, issues)
        self.assertIn(("notes/a.txt", "private key header"), issues)
        self.assertNotIn(sample.decode(), str(issues))

    def test_private_host_path(self):
        issues = set()
        sample = b"/home/" + b"buildworker/source"
        gate.scan("notes/b.txt", sample, issues)
        self.assertIn(("notes/b.txt", "internal build directory"), issues)

    def test_indented_credential_assignments_are_blocked(self):
        # Split synthetic fixture names to avoid embedding credentials in tests.
        cases = (
            b"    PASS" + b"WORD=synthetic_value_not_real",
            b"\t export ACCESS_" + b"TOKEN = 'synthetic_value_not_real'",
            b"    API_" + b"KEY = synthetic_value_not_real",
        )
        for sample in cases:
            with self.subTest(prefix=sample.split(b"=")[0]):
                issues = set()
                gate.scan("fixtures/synthetic.env", sample, issues)
                self.assertIn(("fixtures/synthetic.env",
                               "potential embedded credential"), issues)
                self.assertNotIn("synthetic_value_not_real", str(issues))

    def test_unrelated_indented_assignments_remain_clean(self):
        issues = set()
        gate.scan("fixtures/safe.env",
                  b"    TIMEOUT = 30\n    DESCRIPTION = synthetic_value_not_real",
                  issues)
        self.assertEqual(issues, set())

    def test_default_config_block(self):
        issues = set()
        gate.scan("config/" + "kernel.config", b"CONFIG_SOMETHING=y\n", issues)
        self.assertIn(("config/kernel.config", "restricted artifact filename/type"), issues)

if __name__ == "__main__":
    unittest.main()
