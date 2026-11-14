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

            def fileno(self):
                return self.stream.fileno()

        def injected_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            if path == output and args and args[0] == 'xb':
                return ShortWrite(stream)
            return stream

        with patch.object(Path, 'open', injected_open):
            with self.assertRaisesRegex(OSError, 'short P26 hash payload write'):
                self.run_create()
        self.assertFalse(self.out.exists())

    def test_cleanup_failure_preserves_primary_write_error(self):
        real_open = Path.open
        real_unlink = Path.unlink
        output = self.out

        class FailedWrite:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def write(self, payload):
                self.stream.write(payload[:1])
                raise OSError('primary write failure')

            def flush(self):
                self.stream.flush()

            def fileno(self):
                return self.stream.fileno()

        def injected_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            if path == output and args and args[0] == 'xb':
                return FailedWrite(stream)
            return stream

        def injected_unlink(path, *args, **kwargs):
            if path == output:
                raise OSError('rollback failure')
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, 'open', injected_open), patch.object(Path, 'unlink', injected_unlink):
            with self.assertRaisesRegex(OSError, 'primary write failure') as caught:
                self.run_create()
        if hasattr(caught.exception, '__notes__'):
            self.assertIn('rollback failure', ' '.join(caught.exception.__notes__))
        # A failed cleanup leaves a partial file; never report successful evidence.
        self.assertEqual(self.out.read_bytes(), self.digest[:1].encode())

    def test_fsync_failure_removes_unverified_output(self):
        with patch.object(mod.os, 'fsync', side_effect=OSError('injected fsync failure')):
            with self.assertRaisesRegex(OSError, 'injected fsync failure'):
                self.run_create()
        self.assertFalse(self.out.exists())

    def test_success_syncs_file_then_parent_directory(self):
        import stat
        real_fsync = mod.os.fsync
        kinds = []
        def observed_fsync(fd):
            kinds.append('directory' if stat.S_ISDIR(mod.os.fstat(fd).st_mode) else 'file')
            return real_fsync(fd)
        with patch.object(mod.os, 'fsync', side_effect=observed_fsync):
            self.assertEqual(self.run_create(), self.digest)
        self.assertEqual(kinds, ['file', 'directory'])

    def test_directory_fsync_failure_removes_output(self):
        real_fsync = mod.os.fsync
        calls = []
        def injected_fsync(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('directory fsync failure')
            return real_fsync(fd)
        with patch.object(mod.os, 'fsync', side_effect=injected_fsync):
            with self.assertRaisesRegex(OSError, 'directory fsync failure'):
                self.run_create()
        # The failed publish sync is followed by a rollback directory sync.
        self.assertEqual(len(calls), 3)
        self.assertFalse(self.out.exists())

    def test_directory_sync_failure_persists_rollback_removal(self):
        import stat
        real_fsync = mod.os.fsync
        kinds = []
        def injected_fsync(fd):
            kind = 'directory' if stat.S_ISDIR(mod.os.fstat(fd).st_mode) else 'file'
            kinds.append(kind)
            if kinds == ['file', 'directory']:
                raise OSError('directory fsync failure')
            return real_fsync(fd)
        with patch.object(mod.os, 'fsync', side_effect=injected_fsync):
            with self.assertRaisesRegex(OSError, 'directory fsync failure'):
                self.run_create()
        self.assertEqual(kinds, ['file', 'directory', 'directory'])
        self.assertFalse(self.out.exists())

    def test_reject_boolean_schema_and_partition_size(self):
        # bool compares equal to 1 in Python, but is not a valid receipt integer.
        for receipt_path, field, replacement in (
            (self.producer, 'schema', True),
            (self.independent, 'schema', True),
            (self.producer, 'partition_bytes', True),
            (self.independent, 'partition_bytes', True),
        ):
            with self.subTest(receipt=receipt_path.name, field=field):
                original_bytes = receipt_path.read_bytes()
                try:
                    data = json.loads(original_bytes)
                    data[field] = replacement
                    receipt_path.write_text(json.dumps(data))
                    if receipt_path == self.producer:
                        independent_data = json.loads(self.independent.read_text())
                        independent_bytes = self.independent.read_bytes()
                        independent_data['producer_receipt_sha256'] = mod.sha256(self.producer)
                        self.independent.write_text(json.dumps(independent_data))
                    else:
                        independent_bytes = None
                    with self.assertRaisesRegex(ValueError, 'receipt mismatch|partition size mismatch'):
                        self.run_create()
                    self.assertFalse(self.out.exists())
                finally:
                    receipt_path.write_bytes(original_bytes)
                    if independent_bytes is not None:
                        self.independent.write_bytes(independent_bytes)

    def test_reject_non_object_receipts(self):
        # JSON permits scalar and array top-level values; receipts do not.
        for path in (self.producer, self.independent):
            for invalid in ([], None, 'text', 7, True):
                with self.subTest(receipt=path.name, invalid=invalid):
                    previous = path.read_bytes()
                    try:
                        path.write_text(json.dumps(invalid))
                        with self.assertRaisesRegex(ValueError, 'JSON objects'):
                            self.run_create()
                        self.assertFalse(self.out.exists())
                    finally:
                        path.write_bytes(previous)

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
