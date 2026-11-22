"""Exercise the actual CI GitHub Contents fallback decoder without network access."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/source-only-ci.yml'


def decoder_source():
    workflow = WORKFLOW.read_text(encoding='utf-8')
    marker = 'python3 - "$tmp/github-content.json" "$destination" <<\'PY\'\n'
    if workflow.count(marker) != 1:
        raise AssertionError('CI fallback decoder missing or ambiguous')
    return textwrap.dedent(workflow.split(marker, 1)[1].split('\n          PY', 1)[0])


class ContentsFallbackTests(unittest.TestCase):
    def run_decoder(self, data, previous=b'original'):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / 'record.json'
            destination = Path(tmp) / 'source.c'
            record.write_text(json.dumps(data), encoding='utf-8')
            destination.write_bytes(previous)
            proc = subprocess.run(
                [sys.executable, '-c', decoder_source(), str(record), str(destination)],
                capture_output=True, text=True, check=False,
            )
            return proc.returncode, destination.read_bytes()

    def fixture(self, payload=b'int main(void) { return 0; }\n'):
        sha = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
        return {
            'encoding': 'base64', 'type': 'file',
            'content': base64.b64encode(payload).decode(),
            'size': len(payload), 'sha': sha,
        }

    def test_valid_wrapped_base64(self):
        record = self.fixture()
        encoded = record['content']
        record['content'] = encoded[:12] + '\n' + encoded[12:24] + '\r\n' + encoded[24:]
        status, output = self.run_decoder(record)
        self.assertEqual(status, 0)
        self.assertEqual(output, b'int main(void) { return 0; }\n')

    def test_invalid_character_rejected_without_overwrite(self):
        record = self.fixture()
        record['content'] = record['content'][:8] + '!' + record['content'][8:]
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')

    def test_wrong_size_rejected(self):
        record = self.fixture()
        record['size'] += 1
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')

    def test_wrong_blob_sha_rejected(self):
        record = self.fixture()
        record['sha'] = '0' * 40
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')

    def test_same_length_tampering_rejected_without_overwrite(self):
        record = self.fixture()
        record['content'] = base64.b64encode(b'X' * record['size']).decode()
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')

    def test_invalid_base64_padding_rejected_without_overwrite(self):
        record = self.fixture()
        record['content'] = record['content'].rstrip('=')
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')

    def test_missing_metadata_rejected_without_overwrite(self):
        for field in ('size', 'sha', 'content', 'encoding'):
            with self.subTest(field=field):
                record = self.fixture()
                del record[field]
                status, output = self.run_decoder(record)
                self.assertNotEqual(status, 0)
                self.assertEqual(output, b'original')

    def test_duplicate_metadata_key_rejected_without_overwrite(self):
        record = self.fixture()
        for field, duplicate in (('sha', '0' * 40), ('size', 0), ('encoding', 'none')):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    source = Path(tmp) / 'record.json'
                    destination = Path(tmp) / 'source.c'
                    # Preserve duplicate keys on disk; a dict would collapse them.
                    raw = json.dumps(record)
                    raw = raw[:-1] + ',' + json.dumps(field) + ':' + json.dumps(duplicate) + '}'
                    source.write_text(raw, encoding='utf-8')
                    destination.write_bytes(b'original')
                    proc = subprocess.run(
                        [sys.executable, '-c', decoder_source(), str(source), str(destination)],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertEqual(destination.read_bytes(), b'original')

    def test_wrong_api_shape_rejected(self):
        record = self.fixture()
        record['type'] = 'dir'
        status, output = self.run_decoder(record)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, b'original')


if __name__ == '__main__':
    unittest.main()
