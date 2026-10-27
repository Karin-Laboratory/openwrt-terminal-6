# SPDX-License-Identifier: MIT
"""Synthetic local files only; never device/SDK/image access."""
from pathlib import Path
import hashlib
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "input_verify", ROOT / "tools/boot/verify_build_inputs.py"
)
verify = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = verify
spec.loader.exec_module(verify)


class BuildInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = b"synthetic bytes, not actual firmware"
        (self.root / "kernel.mock").write_bytes(self.data)
        self.entry = {
            "role": "kernel", "path": "kernel.mock",
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "size_bytes": len(self.data),
        }
        self.manifest = {
            "schema": 1, "build_revision": "a" * 40,
            "inputs": [self.entry],
        }

    def test_match_is_identity_only(self):
        self.assertEqual(verify.verify(self.root, self.manifest), [])

    def test_hash_mismatch_is_blocked(self):
        self.entry["sha256"] = "b" * 64
        self.assertIn("SHA-256 mismatch", str(verify.verify(self.root, self.manifest)))

    def test_size_mismatch_is_blocked(self):
        self.entry["size_bytes"] -= 1
        self.assertIn("size mismatch", str(verify.verify(self.root, self.manifest)))

    def test_reject_secret_filename_and_path_traversal(self):
        self.entry["path"] = "../outside.bin"
        self.assertTrue(verify.verify(self.root, self.manifest))
        self.entry["path"] = "private.key"
        self.assertIn("forbidden artifact path", str(verify.verify(self.root, self.manifest)))

    def test_symlink_is_not_followed(self):
        (self.root / "linked.mock").symlink_to(self.root / "kernel.mock")
        self.entry["path"] = "linked.mock"
        self.assertIn("symbolic link", str(verify.verify(self.root, self.manifest)))

    def test_unknown_role_and_duplicated_input(self):
        self.entry["role"] = "private-signing-key"
        self.manifest["inputs"].append(self.entry.copy())
        issues = verify.verify(self.root, self.manifest)
        self.assertTrue(any("unsupported role" in x for x in issues))
        self.assertTrue(any("duplicated" in x for x in issues))

    def test_reject_bool_size_and_missing_revision(self):
        self.entry["size_bytes"] = True
        self.manifest["build_revision"] = "not-a-revision"
        errors = verify.verify(self.root, self.manifest)
        self.assertTrue(any("invalid bounded" in x for x in errors))
        self.assertTrue(any("invalid build" in x for x in errors))


if __name__ == "__main__":
    unittest.main()
