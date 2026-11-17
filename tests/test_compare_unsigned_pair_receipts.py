# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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
    def test_directory_rejected(self):
        self.b.unlink()
        self.b.mkdir()
        with self.assertRaisesRegex(ValueError, 'RECEIPT_NOT_REGULAR'):
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
        self.b.write_bytes(b'\\xff')
        with self.assertRaisesRegex(ValueError, 'INVALID_RECEIPT_JSON'):
            mod.compare(self.a, self.b)
    def test_false_status(self):
        self.b.write_text(json.dumps(dict(self.receipt, signed=True)))
        with self.assertRaisesRegex(ValueError,'INVALID_PAIR_RECEIPT'):
            mod.compare(self.a,self.b)

if __name__ == '__main__':
    unittest.main()
