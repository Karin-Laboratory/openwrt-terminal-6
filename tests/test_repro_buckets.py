# SPDX-License-Identifier: MIT
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('repro_buckets', Path(__file__).resolve().parents[1] / 'tools/build/repro_buckets.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BucketTests(unittest.TestCase):
    def test_repeat_and_content_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a').write_text('one')
            first = module.fingerprints(root)
            self.assertEqual(first, module.fingerprints(root))
            (root / 'a').write_text('two')
            second = module.fingerprints(root)
            self.assertEqual([x[3] for x in first], [x[3] for x in second])
            self.assertNotEqual([x[2] for x in first], [x[2] for x in second])

    def test_mode_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / 'a'
            file.write_text('one')
            first = module.fingerprints(root)
            file.chmod(0o700)
            second = module.fingerprints(root)
            self.assertEqual([x[2] for x in first], [x[2] for x in second])
            self.assertNotEqual([x[3] for x in first], [x[3] for x in second])
            (root / 'link').symlink_to('a')
            third = module.fingerprints(root)
            (root / 'link').unlink()
            (root / 'link').symlink_to('missing')
            fourth = module.fingerprints(root)
            self.assertNotEqual([x[2] for x in third], [x[2] for x in fourth])


if __name__ == '__main__':
    unittest.main()
