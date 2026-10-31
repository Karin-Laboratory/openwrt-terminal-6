# SPDX-License-Identifier: MIT
"""Synthetic, network-free tests for the optional pinned feed object verifier."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "feed_git_objects", ROOT / "tools/build/verify_feed_git_objects.py")
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


class FeedGitObjectTests(unittest.TestCase):
    def git(self, directory, *args, input_data=b""):
        env = os.environ.copy()
        env.update(GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        return subprocess.run(["git", "--git-dir", str(directory), *args],
                              input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True, env=env).stdout.strip().decode()

    def fixture(self, root):
        bare = root / "feed.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
        blob = self.git(bare, "hash-object", "-w", "--stdin", input_data=b"fixture readme\n")
        tree = self.git(bare, "mktree", input_data=f"100644 blob {blob}\tREADME.md\n".encode())
        commit = self.git(bare, "commit-tree", tree, input_data=b"Synthetic feed commit\n")
        return bare, commit, tree

    def test_local_commit_and_tree_raw_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, commit, tree = self.fixture(Path(tmp))
            self.assertEqual(checker.inspect_one(repo, commit, tree), [])
            self.assertEqual(checker.inspect({"packages": repo}, {"packages": (commit, tree)}), [])

    def test_wrong_tree_and_missing_commit_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, commit, tree = self.fixture(Path(tmp))
            self.assertIn("does not reference", str(checker.inspect_one(repo, commit, "0" * 40)))
            self.assertIn("unavailable", str(checker.inspect_one(repo, "f" * 40, tree)))

    def test_symlink_and_missing_feed_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, commit, tree = self.fixture(root)
            alias = root / "alias.git"
            alias.symlink_to(repo, target_is_directory=True)
            self.assertTrue(checker.inspect_one(alias, commit, tree))
            self.assertTrue(checker.inspect({"packages": repo}))

    def test_commit_tree_bytes_are_independently_rehashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, commit, tree = self.fixture(Path(tmp))
            commit_bytes = checker.object_bytes(repo, "commit", commit)
            tree_bytes = checker.object_bytes(repo, "tree", tree)
            self.assertEqual(checker.object_id("commit", commit_bytes), commit)
            self.assertEqual(checker.object_id("tree", tree_bytes), tree)
            self.assertNotEqual(checker.object_id("commit", commit_bytes + b"x"), commit)


if __name__ == "__main__":
    unittest.main()
