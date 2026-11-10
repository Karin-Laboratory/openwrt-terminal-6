# SPDX-License-Identifier: MIT
"""Offline tests for non-destructive P44 overlay-state initialization."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "tools/boot/prepare_p44_state.sh"


def run(root, action):
    return subprocess.run(["sh", str(HELPER), str(root), action],
                          text=True, capture_output=True, timeout=5)


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix().encode()
        info = path.lstat()
        digest.update(rel + b"\0" + oct(info.st_mode).encode() + b"\0")
        if path.is_symlink():
            digest.update(os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class P44StateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "p44"
        self.root.mkdir()
        (self.root / "lost+found").mkdir()

    def test_empty_ext4_layout_is_initialized_without_formatting(self):
        before = tree_digest(self.root)
        checked = run(self.root, "check")
        self.assertEqual(checked.returncode, 2, checked.stderr)
        self.assertEqual(tree_digest(self.root), before)

        initialized = run(self.root, "init")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertIn("AIR6_P44_EMPTY_EXT4_INITIALIZED", initialized.stdout)
        self.assertEqual((self.root / ".sba6d-rootfs-data-v1").read_text(),
                         "SBA6D_ROOTFS_DATA_V1\n")
        self.assertEqual((self.root / ".air6-p44-init-v1").read_text(),
                         "AIR6_P44_INIT_IN_PROGRESS_V1\n")
        self.assertEqual(os.readlink(self.root / ".fs_state"), "2")
        self.assertEqual((self.root / "upper").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "work").stat().st_mode & 0o777, 0o700)
        self.assertEqual(run(self.root, "check").returncode, 0)

    def test_existing_overlay_and_saved_data_are_preserved(self):
        (self.root / "upper").mkdir()
        (self.root / "work").mkdir()
        (self.root / ".fs_state").symlink_to("2")
        (self.root / ".sba6d-rootfs-data-v1").write_text(
            "SBA6D_ROOTFS_DATA_V1\n")
        saved = self.root / "upper/saved-config"
        saved.write_text("owner data\n")
        before = tree_digest(self.root)

        checked = run(self.root, "check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        initialized = run(self.root, "init")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertIn("AIR6_P44_EXISTING_STATE_PRESERVED", initialized.stdout)
        self.assertEqual(tree_digest(self.root), before)

    def test_unrecognized_existing_data_is_never_changed(self):
        sentinel = self.root / "owner-data"
        sentinel.write_text("keep\n")
        before = tree_digest(self.root)
        for action in ("check", "init"):
            result = run(self.root, action)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AIR6_P44_STATE_BLOCKED", result.stderr)
            self.assertEqual(tree_digest(self.root), before)

    def test_recognized_interrupted_initialization_resumes(self):
        (self.root / ".air6-p44-init-v1").write_text(
            "AIR6_P44_INIT_IN_PROGRESS_V1\n")
        (self.root / "upper").mkdir()
        self.assertEqual(run(self.root, "check").returncode, 3)
        result = run(self.root, "init")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(run(self.root, "check").returncode, 0)

    def test_interrupted_state_with_unrecognized_content_stops_unchanged(self):
        (self.root / ".air6-p44-init-v1").write_text(
            "AIR6_P44_INIT_IN_PROGRESS_V1\n")
        (self.root / "upper").mkdir()
        (self.root / "upper/owner-data").write_text("keep\n")
        before = tree_digest(self.root)
        for action in ("check", "init"):
            result = run(self.root, action)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(tree_digest(self.root), before)

    def test_symlinked_partition_mountpoint_is_rejected(self):
        link = self.root.parent / "p44-link"
        link.symlink_to(self.root, target_is_directory=True)
        result = run(link, "init")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
