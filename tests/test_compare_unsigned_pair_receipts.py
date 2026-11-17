# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('compare', Path(__file__).resolve().parents[1] / 'tools/build/compare_unsigned_pair_receipts.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.a = Path(self.temp.name) / 'a.json'
        self.b = Path(self.temp.name) / 'b.json'
        self.receipt = {'status':'UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED', 'signed':False, 'device_writes':False, 'public_binary':False}
        self.receipt.update({k:'a'*64 for k in mod.FIELDS})
        self.save()
    def save(self):
        self.a.write_text(json.dumps(self.receipt))
        self.b.write_text(json.dumps(self.receipt))
    def test_equal(self):
        self.assertEqual(mod.compare(self.a,self.b), [])
    def test_same_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'RECEIPTS_NOT_INDEPENDENT_FILES'):
            mod.compare(self.a, self.a)
    def test_hardlink_rejected(self):
        self.b.unlink()
        self.b.hardlink_to(self.a)
        with self.assertRaisesRegex(ValueError, 'RECEIPTS_NOT_INDEPENDENT_FILES'):
            mod.compare(self.a, self.b)
    def test_first_receipt_replaced_while_second_is_read(self):
        original_load = mod.load
        calls = 0
        def replacing_load(path):
            nonlocal calls
            calls += 1
            result = original_load(path)
            if calls == 2:
                self.a.write_text(json.dumps(dict(self.receipt, p25_sha256='b'*64)))
            return result
        with mock.patch.object(mod, 'load', side_effect=replacing_load):
            with self.assertRaisesRegex(ValueError, 'FIRST_RECEIPT_CHANGED_DURING_COMPARISON'):
                mod.compare(self.a, self.b)

    def test_second_receipt_replaced_during_final_recheck(self):
        original_load = mod.load
        calls = 0
        def replacing_load(path):
            nonlocal calls
            calls += 1
            result = original_load(path)
            if calls == 3:
                self.b.write_text(json.dumps(dict(self.receipt, p25_sha256='b'*64)))
            return result
        with mock.patch.object(mod, 'load', side_effect=replacing_load):
            with self.assertRaisesRegex(ValueError, 'SECOND_RECEIPT_CHANGED_DURING_COMPARISON'):
                mod.compare(self.a, self.b)

    def test_changed_p26(self):
        self.b.write_text(json.dumps(dict(self.receipt, p26_sha256='b'*64)))
        self.assertEqual(mod.compare(self.a,self.b), ['p26_sha256'])
    def test_invalid_receipt(self):
        self.b.write_text('{"status":"UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED","signed":false,"signed":false}')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):
            mod.compare(self.a,self.b)
    def test_symlink_rejected(self):
        self.b.unlink()
        self.b.symlink_to(self.a)
        with self.assertRaises(OSError):
            mod.compare(self.a, self.b)
    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX FIFO support')
    def test_fifo_rejected_without_blocking(self):
        self.b.unlink()
        os.mkfifo(self.b)
        with self.assertRaisesRegex(ValueError, 'RECEIPT_NOT_REGULAR'):
            mod.compare(self.a, self.b)

    def test_cli_matching_receipts(self):
        cli = Path(__file__).resolve().parents[1] / 'tools/build/compare_unsigned_pair_receipts.py'
        result = subprocess.run([sys.executable, str(cli), str(self.a), str(self.b)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PUBLIC_PAIR_CROSS_WORKSPACE_RECEIPT_IDENTITIES_MATCH', result.stdout)
        self.assertIn('INDEPENDENT_BUILD_PROVENANCE_NOT_VERIFIED', result.stdout)

    def test_cli_mismatch_returns_nonzero(self):
        self.b.write_text(json.dumps(dict(self.receipt, p25_sha256='b'*64)))
        cli = Path(__file__).resolve().parents[1] / 'tools/build/compare_unsigned_pair_receipts.py'
        result = subprocess.run([sys.executable, str(cli), str(self.a), str(self.b)],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PUBLIC_PAIR_CROSS_WORKSPACE_DIFFERENCE p25_sha256', result.stdout)
        self.assertNotIn('PUBLIC_PAIR_CROSS_WORKSPACE_RECEIPT_IDENTITIES_MATCH', result.stdout)
        self.assertNotIn('INDEPENDENT_BUILD_PROVENANCE_NOT_VERIFIED', result.stdout)

    def test_directory_rejected(self):
        self.b.unlink()
        self.b.mkdir()
        with self.assertRaisesRegex(ValueError, 'RECEIPT_NOT_REGULAR'):
            mod.compare(self.a, self.b)
    def test_receipt_truncated_during_read_rejected(self):
        original = mod.os.fstat
        calls = 0
        def changing_stat(fd):
            nonlocal calls
            calls += 1
            result = original(fd)
            if calls == 4:
                class Changed:
                    st_dev = result.st_dev
                    st_ino = result.st_ino
                    st_size = result.st_size - 1
                    st_mtime_ns = result.st_mtime_ns
                    st_ctime_ns = result.st_ctime_ns
                return Changed()
            return result
        with mock.patch.object(mod.os, 'fstat', side_effect=changing_stat):
            with self.assertRaisesRegex(ValueError, 'RECEIPT_CHANGED_DURING_READ'):
                mod.compare(self.a, self.b)

    def test_oversized_rejected(self):
        self.b.write_bytes(b' ' * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, 'RECEIPT_TOO_LARGE'):
            mod.compare(self.a, self.b)
    def test_malformed_json_rejected(self):
        self.b.write_bytes(b'{broken')
        with self.assertRaisesRegex(ValueError, 'INVALID_RECEIPT_JSON'):
            mod.compare(self.a, self.b)
    def test_invalid_utf8_rejected(self):
        self.b.write_bytes(bytes([0xff]))
        with self.assertRaisesRegex(ValueError, 'INVALID_RECEIPT_JSON'):
            mod.compare(self.a, self.b)
    def test_nonstandard_json_constants_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value):
                self.b.write_text(json.dumps(self.receipt)[:-1] + ',"extra":' + value + '}')
                with self.assertRaisesRegex(ValueError, 'INVALID_RECEIPT_JSON_CONSTANT'):
                    mod.compare(self.a, self.b)
    def test_excessive_json_nesting_rejected(self):
        self.b.write_text('[' * 10000 + '0' + ']' * 10000)
        with self.assertRaisesRegex(ValueError, 'INVALID_RECEIPT_JSON|INVALID_PAIR_RECEIPT'):
            mod.compare(self.a, self.b)

    def test_each_digest_rejects_invalid_values(self):
        for field in mod.FIELDS:
            for bad in ('A' * 64, 'g' * 64, 'a' * 63, 123, None):
                with self.subTest(field=field, bad=bad):
                    self.b.write_text(json.dumps(dict(self.receipt, **{field: bad})))
                    with self.assertRaisesRegex(ValueError, 'INVALID_DIGEST_' + field):
                        mod.compare(self.a, self.b)

    def test_each_unsafe_flag_rejected(self):
        for field in ('signed', 'device_writes', 'public_binary'):
            for bad in (True, 0, None):
                with self.subTest(field=field, bad=bad):
                    self.b.write_text(json.dumps(dict(self.receipt, **{field: bad})))
                    with self.assertRaisesRegex(ValueError, 'INVALID_PAIR_RECEIPT'):
                        mod.compare(self.a, self.b)

    def test_all_digest_differences_reported(self):
        changed = dict(self.receipt)
        for field in mod.FIELDS:
            changed[field] = 'b' * 64
        self.b.write_text(json.dumps(changed))
        self.assertEqual(mod.compare(self.a, self.b), list(mod.FIELDS))

    def test_false_status(self):
        self.b.write_text(json.dumps(dict(self.receipt, signed=True)))
        with self.assertRaisesRegex(ValueError,'INVALID_PAIR_RECEIPT'):
            mod.compare(self.a,self.b)

if __name__ == '__main__':
    unittest.main()
