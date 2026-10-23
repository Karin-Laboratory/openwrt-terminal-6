import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import zlib
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/package_public_rfc.py"
spec = importlib.util.spec_from_file_location("package_public_rfc", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
VERIFY = SCRIPT.with_name("verify_public_rfc.py")
verify_spec = importlib.util.spec_from_file_location("verify_public_rfc", VERIFY)
verifier = importlib.util.module_from_spec(verify_spec)
import sys
sys.path.insert(0, str(SCRIPT.parent))
verify_spec.loader.exec_module(verifier)


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
            verifier.verify(first)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with tarfile.open(first) as archive:
                manifest = json.load(archive.extractfile(f"{mod.BASE}/manifest.json"))
                self.assertFalse(manifest["flashable"])
                for name, record in manifest["files"].items():
                    contents = archive.extractfile(f"{mod.BASE}/{name}").read()
                    self.assertEqual(hashlib.sha256(contents).hexdigest(), record["sha256"])
                    self.assertEqual(len(contents), record["bytes"])
                self.assertEqual(len(manifest["files"]), len(mod.FILES))

    def test_rejects_tampered_archive(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / "src"
            root.mkdir()
            for name in mod.FILES:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("original")
            archive = Path(work) / "bundle.tar.gz"
            mod.pack(root, archive)
            data = bytearray(archive.read_bytes())
            data[len(data) // 2] ^= 0xFF
            archive.write_bytes(data)
            with self.assertRaises((ValueError, tarfile.TarError, EOFError, OSError, json.JSONDecodeError, zlib.error)):
                verifier.verify(archive)

    def test_rejects_valid_archive_with_changed_source(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / "src"
            root.mkdir()
            for name in mod.FILES:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("original\n")
            original = Path(work) / "original.tar.gz"
            changed = Path(work) / "changed.tar.gz"
            mod.pack(root, original)
            with tarfile.open(original, "r:gz") as reader:
                with tarfile.open(changed, "w:gz") as writer:
                    for member in reader.getmembers():
                        contents = reader.extractfile(member).read()
                        if member.name.endswith(mod.FILES[0]):
                            contents = b"tampered\n"
                        member.size = len(contents)
                        import io
                        writer.addfile(member, io.BytesIO(contents))
            with self.assertRaisesRegex(ValueError, "Integrity check failed"):
                verifier.verify(changed)

    def test_refuses_missing_input(self):
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaises(ValueError):
                mod.pack(Path(work), Path(work) / "out.tar.gz")


if __name__ == "__main__":
    unittest.main()
