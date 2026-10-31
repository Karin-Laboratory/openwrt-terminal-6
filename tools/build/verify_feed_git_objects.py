#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in, offline byte check of five pinned feed Git commit/root-tree objects.

Never clones, checks out, installs feeds, builds packages or accesses hardware.
The caller must independently obtain local bare Git repositories first.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess

# Commit/root-tree identities previously observed on OpenWrt's GitHub mirrors.
# These are comparison values, NOT independent canonical-origin proof.
EXPECTED = {
    "packages": ("11396c3434272b73294d29aa9d86497b25cf33da", "1abd824e12b18302572254ec0caffa6f4dc34d34"),
    "luci": ("a8c110bed82375b69eb3881b2e54e617520e8c7d", "c62ac511b11737e28cef7298d0533d6f1df3f93a"),
    "routing": ("4b9891b9136259f93294a424507ed24c5e8c1cbd", "73aada2640ec15608d4bc3dc05fb5eaf009f34ca"),
    "telephony": ("5d68d53c160a325ea9d03fce393e051573bcc736", "5993343af44fb2eff7621f4e3da2549dbc753d4b"),
    "video": ("644a66261288b4a95dbc6e46fe805d33cb9f71d9", "32f2324f3fc85de1725e89f55183aa9dc46075a8"),
}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
MAX_OBJECT_BYTES = 1024 * 1024


def object_bytes(git_dir: Path, kind: str, oid: str) -> bytes:
    """Read an object through Git, without checkout, hooks or Git replacements."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "--git-dir", str(git_dir),
         "cat-file", kind, oid],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=env, timeout=15, check=False,
    )
    if result.returncode or len(result.stdout) > MAX_OBJECT_BYTES:
        raise ValueError("missing, invalid or oversized Git object")
    return result.stdout


def object_id(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()


def inspect_one(git_dir: Path, commit_sha: str, tree_sha: str) -> list[str]:
    """Verify raw Git object bytes and the commit's root-tree relationship."""
    if (not git_dir.is_dir() or git_dir.is_symlink()
            or not HEX40.fullmatch(commit_sha) or not HEX40.fullmatch(tree_sha)):
        return ["invalid local Git directory or expected object IDs"]
    try:
        commit = object_bytes(git_dir, "commit", commit_sha)
        if object_id("commit", commit) != commit_sha:
            return ["commit object bytes differ from pinned identity"]
        if commit.split(b"\n", 1)[0] != b"tree " + tree_sha.encode("ascii"):
            return ["commit does not reference the pinned root tree"]
        tree = object_bytes(git_dir, "tree", tree_sha)
        if object_id("tree", tree) != tree_sha:
            return ["root tree object bytes differ from pinned identity"]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return ["pinned commit/tree unavailable or unsafe"]
    return []


def inspect(repos: dict[str, Path], expected=EXPECTED) -> list[str]:
    if set(repos) != set(expected):
        return ["exactly five named feed Git directories are required"]
    errors = []
    for name, (commit, tree) in expected.items():
        errors.extend(name + ": " + message for message in inspect_one(repos[name], commit, tree))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline pinned feed Git-object byte audit")
    parser.add_argument("--repo", action="append", default=[], metavar="NAME=GIT_DIR",
                        help="one local bare Git directory per feed; all five required")
    args = parser.parse_args()
    repos = {}
    for item in args.repo:
        name, sep, path = item.partition("=")
        if not sep or name not in EXPECTED or not path or name in repos:
            print("FEED_OBJECTS_BLOCKED: invalid or duplicate --repo entry")
            return 2
        repos[name] = Path(path)
    problems = inspect(repos)
    for problem in problems:
        print("FEED_OBJECTS_BLOCKED:", problem)
    if problems:
        return 1
    print("FEED_OBJECTS_PASS (five local commit/tree byte identities only)")
    print("No canonical-origin attestation, full source verification, license approval or rootfs build.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
