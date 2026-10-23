import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/package_public_rfc.py"
spec = importlib.util.spec_from_file_location("package_public_rfc", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BundleTests(unittest.TestCase):
    def test_reproducible_and_manifest(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / "src"
            root.mkdir()
            for name in mod.FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("sample source file: " + name + "\n")
            first, second = Path(work) / "first.tar.gz", Path(work) / "second.tar.gz"
            mod.pack(root, first)
            mod.pack(root, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with tarfile.open(first) as archive:
                manifest = json.load(archive.extractfile(f"{mod.BASE}/manifest.json"))
                self.assertFalse(manifest["flashable"])
                for name, record in manifest["files"].items():
                    contents = archive.extractfile(f"{mod.BASE}/{name}").read()
                    self.assertEqual(hashlib.sha256(contents).hexdigest(), record["sha256"])
                    self.assertEqual(len(contents), record["bytes"])
                self.assertEqual(len(manifest["files"]), len(mod.FILES))

    def test_refuses_missing_input(self):
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaises(ValueError):
                mod.pack(Path(work), Path(work) / "out.tar.gz")


if __name__ == "__main__":
    unittest.main()
