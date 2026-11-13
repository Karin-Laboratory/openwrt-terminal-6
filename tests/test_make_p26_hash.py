# SPDX-License-Identifier: MIT
"""Host-only P26 hash input checks with tiny synthetic partitions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'tools/build/make_p26_hash.py'
spec = importlib.util.spec_from_file_location('make_p26_hash', MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HashInputTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.p26 = self.root / 'p26'
        self.p26.write_bytes(b'12345678')
        self.producer = self.root / 'producer.json'
        self.independent = self.root / 'independent.json'
        self.out = self.root / 'p26.sha256'
        self.digest = hashlib.sha256(b'12345678').hexdigest()
        self.producer.write_text(json.dumps(dict(schema=1, status='P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK', signed=False, hardware='NONE', partition_bytes=8, p26_sha256=self.digest, squashfs_sha256='a'*64, squashfs_bytes=4)))
        self.independent.write_text(json.dumps(dict(schema=1, status='P26_INDEPENDENT_FS_READBACK_VERIFIED', verification='INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA', signed=False, hardware='NONE', partition_bytes=8, p26_sha256=self.digest, squashfs_sha256='a'*64, squashfs_bytes=4, producer_receipt_sha256=mod.sha256(self.producer))))
        p = patch.object(mod, 'P26_BYTES', 8)
        p.start()
        self.addCleanup(p.stop)

    def run_create(self):
        return mod.create(self.p26, self.producer, self.independent, self.out)

    def test_exact_payload_and_no_overwrite(self):
        self.assertEqual(self.run_create(), self.digest)
        self.assertEqual(self.out.read_bytes(), (self.digest+'  /dev/mmcblk0p26\n').encode())
        with self.assertRaisesRegex(ValueError, 'output exists'):
            self.run_create()

    def test_short_write_removes_partial_output(self):
        real_open = Path.open
        output = self.out

        class ShortWrite:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def write(self, payload):
                self.stream.write(payload[:-1])
                return len(payload) - 1

            def flush(self):
                self.stream.flush()

        def injected_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            if path == output and args and args[0] == 'xb':
                return ShortWrite(stream)
            return stream

        with patch.object(Path, 'open', injected_open):
            with self.assertRaisesRegex(OSError, 'short P26 hash payload write'):
                self.run_create()
        self.assertFalse(self.out.exists())

    def test_reject_modified_image(self):
        self.p26.write_bytes(b'12345679')
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.run_create()
        self.assertFalse(self.out.exists())

    def test_reject_false_receipt(self):
        data = json.loads(self.independent.read_text())
        data['verification'] = 'NONE'
        self.independent.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            self.run_create()

    def test_reject_missing_or_malformed_squashfs_identity(self):
        for bad_hash, bad_size in ((None, None), ('not-a-digest', 4), ('a'*64, 0), ('a'*64, True), ('a'*64, 9)):
            with self.subTest(hash=bad_hash, size=bad_size):
                producer = json.loads(self.producer.read_text())
                independent = json.loads(self.independent.read_text())
                producer['squashfs_sha256'] = bad_hash
                producer['squashfs_bytes'] = bad_size
                independent['squashfs_sha256'] = bad_hash
                independent['squashfs_bytes'] = bad_size
                self.producer.write_text(json.dumps(producer))
                independent['producer_receipt_sha256'] = mod.sha256(self.producer)
                self.independent.write_text(json.dumps(independent))
                with self.assertRaisesRegex(ValueError, 'invalid SquashFS identity metadata'):
                    self.run_create()
                self.assertFalse(self.out.exists())

    def test_reject_changed_producer(self):
        data = json.loads(self.producer.read_text())
        data['squashfs_bytes'] = 5
        self.producer.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            self.run_create()

if __name__ == '__main__':
    unittest.main()
