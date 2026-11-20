"""Offline regression tests for independent pair receipt comparison.

Origin: independently authored; SPDX-License-Identifier: MIT.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build/compare_pair_repro_receipts.py"
spec = importlib.util.spec_from_file_location("pair_repro", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReceiptComparisonTest(unittest.TestCase):
    def setUp(self):
        self.a = {field: "a" * 64 for field in mod.FIELDS}

    def test_identical(self):
        self.assertEqual(mod.compare(self.a, dict(self.a)), [])

    def test_each_digest_is_checked(self):
        for field in mod.FIELDS:
            with self.subTest(field=field):
                b = dict(self.a)
                b[field] = "b" * 64
                self.assertEqual(mod.compare(self.a, b), [field])

    def test_malformed_and_missing_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            for value in ([], {}, {**self.a, "p25_sha256": "X" * 64}):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    mod.load(path)

    def test_all_digest_fields_reject_noncanonical_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            bad_values = ("A" * 64, "a" * 63, "a" * 65, "g" * 64, " " + "a" * 63, 123, None)
            for field in mod.FIELDS:
                for value in bad_values:
                    with self.subTest(field=field, value=repr(value)):
                        candidate = dict(self.a)
                        candidate[field] = value
                        path.write_text(json.dumps(candidate), encoding="utf-8")
                        with self.assertRaisesRegex(ValueError, "missing or malformed SHA-256"):
                            mod.load(path)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            original = json.dumps(self.a)
            path.write_text(original[:-1] + ', "p25_sha256": "' + "b" * 64 + '"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                mod.load(path)

    def test_nonstandard_json_constants_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(constant=constant):
                    path.write_text(json.dumps(self.a)[:-1] + ', "extra": ' + constant + '}')
                    with self.assertRaisesRegex(ValueError, "nonstandard JSON constant"):
                        mod.load(path)

    def test_overflowed_json_number_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            for exponent in ("1e1000000", "-1e1000000"):
                with self.subTest(exponent=exponent):
                    path.write_text(json.dumps(self.a)[:-1] + ', "extra": ' + exponent + '}')
                    with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                        mod.load(path)

    def test_finite_json_number_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(self.a)[:-1] + ', "extra": 1.25e2}')
            self.assertEqual(mod.load(path)["extra"], 125.0)

    def test_same_receipt_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(self.a))
            command = [sys.executable, str(SCRIPT), str(path), str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("different receipt files", result.stderr)

    def test_hard_linked_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a))
            b.hardlink_to(a)
            command = [sys.executable, str(SCRIPT), str(a), str(b)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("different receipt files", result.stderr)

    def test_invalid_utf8_receipt_returns_invalid_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a), encoding="utf-8")
            b.write_bytes(bytes((0xff, 0xfe)))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(a), str(b)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("REPRO_RECEIPT_INVALID:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_each_mismatch_without_false_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a), encoding="utf-8")
            for field in mod.FIELDS:
                with self.subTest(field=field):
                    changed = dict(self.a)
                    changed[field] = "b" * 64
                    b.write_text(json.dumps(changed), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(a), str(b)],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("REPRO_RECEIPT_MISMATCH: " + field, result.stdout)
                    self.assertNotIn("REPRO_RECEIPT_HASHES_MATCH", result.stdout)
                    for checked in mod.FIELDS:
                        status = "DIFF" if checked == field else "MATCH"
                        self.assertIn("REPRO_" + checked.upper() + "=" + status, result.stdout)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO support required")
    def test_fifo_receipt_is_rejected_without_hanging(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "fifo.json"
            a.write_text(json.dumps(self.a), encoding="utf-8")
            os.mkfifo(b)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(a), str(b)],
                capture_output=True, text=True, timeout=3,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("regular file", result.stderr)

    def test_oversized_receipt_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a), encoding="utf-8")
            b.write_bytes(b" " * (mod.MAX_RECEIPT_BYTES + 1))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(a), str(b)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("receipt exceeds maximum size", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_deeply_nested_json_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a), encoding="utf-8")
            b.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(a), str(b)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("REPRO_RECEIPT_INVALID:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps(self.a))
            b.write_text(json.dumps(self.a))
            command = [sys.executable, str(SCRIPT), str(a), str(b)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            changed = dict(self.a)
            changed["kernel_image_sha256"] = "b" * 64
            b.write_text(json.dumps(changed))
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
            b.write_text("{}")
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
