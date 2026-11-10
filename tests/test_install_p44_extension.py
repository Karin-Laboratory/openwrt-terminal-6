# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/build/install_p44_extension.py"
spec = importlib.util.spec_from_file_location("p44install", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestP44Installer(unittest.TestCase):
    def test_stages_noncritical_hook(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "rootfs"
            root.mkdir()
            mod.install(root)
            runner = root / "usr/libexec/air6/p44-extension-runner"
            init = root / "etc/init.d/air6-p44-extension"
            self.assertEqual(runner.stat().st_mode & 0o777, 0o755)
            self.assertIn("timeout 15", runner.read_text())
            self.assertIn(" /overlay ext4 ", runner.read_text())
            self.assertIn("|| :", init.read_text())
            self.assertEqual((root / "etc/rc.d/S99air6-p44-extension").readlink(),
                             Path("../init.d/air6-p44-extension"))
            self.assertFalse((root / "overlay").exists())
            with self.assertRaises(ValueError):
                mod.install(root)

    def test_rejects_symlinked_etc(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "rootfs"
            root.mkdir()
            (root / "etc").symlink_to(Path(td))
            with self.assertRaises(ValueError):
                mod.install(root)

    def test_no_host_root(self):
        with self.assertRaises(ValueError):
            mod.install(Path("/"))

if __name__ == "__main__":
    unittest.main()
