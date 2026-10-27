# SPDX-License-Identifier: MIT
"""Synthetic, no-device tests for source-only reproducibility contract."""
from pathlib import Path
import hashlib
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "source_catalog_check", ROOT / "tools/build/verify_source_catalog.py")
check = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check
spec.loader.exec_module(check)


class SourceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = "patches/rfc/synthetic.patch"
        f = self.root / self.path
        f.parent.mkdir(parents=True)
        self.data = b"synthetic source content\n"
        f.write_bytes(self.data)
        self.entry = {
            "path": self.path,
            "component": "ethernet",
            "origin": "linux-v6.18-derived",
            "license": "GPL-2.0-only",
            "git_blob_sha1": hashlib.sha1(
                b"blob " + str(len(self.data)).encode() + b"\x00" + self.data
            ).hexdigest(),
            "rights_review": "pending",
            "contains_flashable_payload": False,
        }
        self.catalog = {
            "schema": 1, "policy": "SOURCE_ONLY",
            "warning": "Git identity is not source authenticity",
            "inputs": [self.entry],
            "missing_dependencies": [{"component": "kernel",
                                      "reason": "synthetic incomplete source"}],
        }

    def test_exact_source_contract_passes(self):
        self.assertEqual(check.validate(self.root, self.catalog), [])

    def test_altered_source_is_rejected(self):
        (self.root / self.path).write_bytes(b"modified\n")
        self.assertIn("source bytes differ", str(check.validate(self.root, self.catalog)))

    def test_public_build_is_fail_closed(self):
        problems = check.validate(self.root, self.catalog, public=True)
        self.assertTrue(any("rights review pending" in p for p in problems))
        self.assertTrue(any("missing build dependencies" in p for p in problems))

    def test_traversal_and_duplicate_are_rejected(self):
        self.entry["path"] = "patches/../private.key"
        self.assertTrue(check.validate(self.root, self.catalog))
        self.entry["path"] = self.path
        self.catalog["inputs"].append(self.entry.copy())
        self.assertTrue(any("duplicate" in p for p in check.validate(self.root, self.catalog)))

    def test_reject_payload_and_invalid_license(self):
        self.entry["contains_flashable_payload"] = True
        self.entry["license"] = "unknown-license"
        errors = check.validate(self.root, self.catalog)
        self.assertTrue(any("flashable payload" in p for p in errors))
        self.assertTrue(any("SPDX" in p for p in errors))

    def test_source_publication_gate_independent_of_firmware_readiness(self):
        problems = check.validate(self.root, self.catalog, source_public=True)
        self.assertTrue(any("rights review pending" in x for x in problems))
        self.assertFalse(any("missing build dependencies" in x for x in problems))
        self.entry["rights_review"] = "approved"
        self.assertEqual(check.validate(self.root, self.catalog, source_public=True), [])
        self.assertTrue(any("missing build dependencies" in x
                            for x in check.validate(self.root, self.catalog, public=True)))

    def test_empty_rights_label_is_not_publication_approval(self):
        self.entry["rights_review"] = ""
        self.assertTrue(check.validate(self.root, self.catalog, source_public=True))

    def test_reject_symlink(self):
        f = self.root / self.path
        f.unlink()
        target = self.root / "real.txt"
        target.write_bytes(self.data)
        f.symlink_to(target)
        self.assertTrue(any("symbolic-link" in p for p in check.validate(self.root, self.catalog)))


if __name__ == "__main__":
    unittest.main()
