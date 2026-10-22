import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("patchgate", ROOT / "tools" / "check_patch_series.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestPatchSeries(unittest.TestCase):
    def test_unapplied_then_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            repo = base / "source"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "hello.txt").write_text("alpha\n")
            subprocess.run(["git", "-C", str(repo), "add", "hello.txt"], check=True)
            patch = base / "test.patch"
            patch.write_text("--- a/hello.txt\n+++ b/hello.txt\n@@ -1 +1 @@\n-alpha\n+beta\n")
            self.assertEqual(module.examine(repo, [patch])["patches"][0]["status"], "applicable")
            subprocess.run(["git", "-C", str(repo), "apply", str(patch)], check=True)
            self.assertEqual(module.examine(repo, [patch])["patches"][0]["status"], "already-applied")

    def test_bad_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / ".git").mkdir()
            patch = root / "bad.patch"
            patch.write_text("not a patch")
            with self.assertRaises(ValueError):
                module.examine(root, [patch])

if __name__ == "__main__":
    unittest.main()
