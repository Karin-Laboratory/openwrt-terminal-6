#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent p26 verifier regression tests; synthetic bytes only."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/build/verify_p26_independent.py"
spec = importlib.util.spec_from_file_location("verify_p26_independent", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class IndependentP26Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "root"
        self.root.mkdir()
        (self.root / "etc").mkdir()
        (self.root / "etc" / "test").write_bytes(b"payload")
        (self.root / "link").symlink_to("etc/test")
        self.raw = self.base / "root.squashfs"
        self.raw.write_bytes(b"hsqs" + b"synthetic")
        self.p26 = self.base / "p26.img"
        self.p26.write_bytes(self.raw.read_bytes() + bytes(128 - self.raw.stat().st_size))
        self.size = patch.object(mod, "SIZE", 128)
        self.size.start()
        self.addCleanup(self.size.stop)

    def fake_unsquashfs(self, command, **kwargs):
        shutil.copytree(self.root, Path(command[command.index("-d") + 1]), symlinks=True)
        return None

    def test_synthetic_matching_tree(self):
        with patch.object(mod.subprocess, "run", side_effect=self.fake_unsquashfs):
            self.assertEqual(mod.verify(self.root, self.p26, self.raw), mod.sha(self.p26))

    def test_partition_size_rejected(self):
        self.p26.write_bytes(b"short")
        with self.assertRaisesRegex(ValueError, "PARTITION_SIZE"):
            mod.verify(self.root, self.p26, self.raw)

    def test_prefix_corruption_rejected(self):
        data = bytearray(self.p26.read_bytes())
        data[0] ^= 1
        self.p26.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "PREFIX_MISMATCH"):
            mod.verify(self.root, self.p26, self.raw)

    def test_nonzero_padding_rejected(self):
        data = bytearray(self.p26.read_bytes())
        data[-1] = 1
        self.p26.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "NONZERO_PADDING"):
            mod.verify(self.root, self.p26, self.raw)

    def test_extracted_content_mismatch_rejected(self):
        def changed(command, **kwargs):
            self.fake_unsquashfs(command, **kwargs)
            dest = Path(command[command.index("-d") + 1])
            (dest / "etc" / "test").write_bytes(b"changed")
        with patch.object(mod.subprocess, "run", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "TREE_METADATA_OR_CONTENT_MISMATCH"):
                mod.verify(self.root, self.p26, self.raw)

    def test_root_directory_mode_mismatch_rejected(self):
        def changed_root(command, **kwargs):
            self.fake_unsquashfs(command, **kwargs)
            dest = Path(command[command.index("-d") + 1])
            dest.chmod(0o700 if (self.root.stat().st_mode & 0o777) != 0o700 else 0o755)
        with patch.object(mod.subprocess, "run", side_effect=changed_root):
            with self.assertRaisesRegex(ValueError, "TREE_METADATA_OR_CONTENT_MISMATCH"):
                mod.verify(self.root, self.p26, self.raw)

    def test_extracted_symlink_target_mismatch_rejected(self):
        def changed_link(command, **kwargs):
            self.fake_unsquashfs(command, **kwargs)
            dest = Path(command[command.index("-d") + 1])
            (dest / "link").unlink()
            (dest / "link").symlink_to("etc/other")
        with patch.object(mod.subprocess, "run", side_effect=changed_link):
            with self.assertRaisesRegex(ValueError, "TREE_METADATA_OR_CONTENT_MISMATCH"):
                mod.verify(self.root, self.p26, self.raw)

    def test_extracted_file_mode_mismatch_rejected(self):
        def changed_mode(command, **kwargs):
            self.fake_unsquashfs(command, **kwargs)
            dest = Path(command[command.index("-d") + 1])
            target = dest / "etc" / "test"
            target.chmod(0o600 if (target.stat().st_mode & 0o777) != 0o600 else 0o644)
        with patch.object(mod.subprocess, "run", side_effect=changed_mode):
            with self.assertRaisesRegex(ValueError, "TREE_METADATA_OR_CONTENT_MISMATCH"):
                mod.verify(self.root, self.p26, self.raw)

    def test_hardlink_relationship_mismatch_rejected(self):
        # Same bytes and permissions are insufficient when the image silently
        # turns two hardlinked files into independent regular files.
        (self.root / "hardlink").hardlink_to(self.root / "etc" / "test")
        with patch.object(mod.subprocess, "run", side_effect=self.fake_unsquashfs):
            with self.assertRaisesRegex(ValueError, "TREE_METADATA_OR_CONTENT_MISMATCH"):
                mod.verify(self.root, self.p26, self.raw)

    def test_hardlink_relationship_preserved(self):
        (self.root / "hardlink").hardlink_to(self.root / "etc" / "test")
        def preserve(command, **kwargs):
            self.fake_unsquashfs(command, **kwargs)
            dest = Path(command[command.index("-d") + 1])
            (dest / "hardlink").unlink()
            (dest / "hardlink").hardlink_to(dest / "etc" / "test")
        with patch.object(mod.subprocess, "run", side_effect=preserve):
            self.assertEqual(mod.verify(self.root, self.p26, self.raw), mod.sha(self.p26))

    def test_symlinked_input_parent_rejected(self):
        # A linked directory must not bypass the verifier input boundary.
        alias = self.base / "linked-parent"
        alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            mod.verify(alias / "root", self.p26, self.raw)
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            mod.verify(self.root, alias / "p26.img", self.raw)
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            mod.verify(self.root, self.p26, alias / "root.squashfs")

    def test_symlink_input_rejected(self):
        alias = self.base / "alias"
        alias.symlink_to(self.p26)
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            mod.verify(self.root, alias, self.raw)


if __name__ == "__main__":
    unittest.main()
