# SPDX-License-Identifier: MIT
"""Synthetic, no-device tests for source-only reproducibility contract."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
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

    def test_unregistered_dtso_is_blocked(self):
        overlay = self.root / "board" / "unexpected.dtso"
        overlay.parent.mkdir()
        overlay.write_text("/dts-v1/;\\n")
        errors = check.validate(self.root, self.catalog)
        self.assertTrue(any("uncatalogued source/test: board/unexpected.dtso" in x
                            for x in errors))

    def test_symlink_parent_of_cataloged_file_is_blocked(self):
        original_directory = self.root / "patches" / "rfc"
        new_directory = self.root / "real"
        original_directory.rename(new_directory)
        original_directory.symlink_to(new_directory, target_is_directory=True)
        errors = check.validate(self.root, self.catalog)
        self.assertTrue(any("symbolic-link source" in x for x in errors))

    def test_symlinked_source_root_is_blocked(self):
        original = self.root / "board"
        target = self.root / "real_board"
        target.mkdir()
        original.symlink_to(target, target_is_directory=True)
        errors = check.validate(self.root, self.catalog)
        self.assertTrue(any("source directory must not be symlink" in x
                            for x in errors))

    def test_new_dts_dtsi_and_mk_must_be_cataloged(self):
        for name in ("board/future.dts", "board/base.dtsi", "scripts/build.mk"):
            destination = self.root / name
            destination.parent.mkdir(exist_ok=True, parents=True)
            destination.write_text("synthetic test only")
        findings = check.validate(self.root, self.catalog)
        for name in ("board/future.dts", "board/base.dtsi", "scripts/build.mk"):
            self.assertTrue(any(name in finding and "uncatalogued" in finding
                                for finding in findings))

    def test_untracked_binary_and_unrelated_symlink_fail_closed(self):
        (self.root / "board").mkdir()
        (self.root / "board" / "secret.img").write_bytes(b"synthetic")
        (self.root / "board" / "redirect").symlink_to(self.root / "real_file")
        findings = check.validate(self.root, self.catalog)
        self.assertTrue(any("unapproved binary/secret artifact" in x for x in findings))
        self.assertTrue(any("symlinked source-tree entry" in x for x in findings))

    def test_reject_symlink(self):
        f = self.root / self.path
        f.unlink()
        target = self.root / "real.txt"
        target.write_bytes(self.data)
        f.symlink_to(target)
        self.assertTrue(any("symbolic-link" in p for p in check.validate(self.root, self.catalog)))


    def test_documented_catalog_inventory_matches_source_of_truth(self):
        """Release/status rights numbers may never drift from current catalog."""
        catalog = json.loads((ROOT / "config/source-catalog.json").read_text())
        inputs = catalog["inputs"]
        expected_pending = sum(
            item["rights_review"] == "pending" for item in inputs
        )
        docs = (
            "docs/STATUS.md",
            "docs/RIGHTS-REVIEW-20261030.md",
            "docs/RELEASE-GATES.md",
        )
        pattern = r"<!-- source-catalog-inventory: inputs=(\d+); pending=(\d+) -->"
        for relative in docs:
            with self.subTest(document=relative):
                document = (ROOT / relative).read_text()
                markers = re.findall(pattern, document)
                self.assertEqual(len(markers), 1, "Require one inventory marker")
                self.assertEqual(
                    (int(markers[0][0]), int(markers[0][1])),
                    (len(inputs), expected_pending),
                )

    def test_rights_review_origin_license_table_matches_catalog(self):
        """Every declared origin/license group is counted, not just grand total."""
        catalog = json.loads((ROOT / "config/source-catalog.json").read_text())
        counts = {}
        for item in catalog["inputs"]:
            key = (item["origin"], item["license"])
            counts[key] = counts.get(key, 0) + 1
        doc = (ROOT / "docs/RIGHTS-REVIEW-20261030.md").read_text()
        rows = re.findall(
            r"^\| ([a-z][a-z0-9-]*) / ([A-Za-z0-9.+-]+) \| (\d+) \|",
            doc,
            flags=re.MULTILINE,
        )
        observed = {(origin, license_): int(count) for origin, license_, count in rows}
        self.assertEqual(observed, counts)
        self.assertEqual(sum(observed.values()), len(catalog["inputs"]))


if __name__ == "__main__":
    unittest.main()
