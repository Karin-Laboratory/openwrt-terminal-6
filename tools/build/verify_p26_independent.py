#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent, fail-closed offline p26 full-byte and extracted-tree readback.

Run in a separate process from pack_p26_rootfs.py. No device, signing, or upload.
This verifier is deliberately not an attestation of OpenWrt source provenance.
"""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile

SIZE = 134_217_728

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def inventory(root):
    result = {}
    # The SquashFS root inode also carries ownership, mode and xattrs.
    # Omitting it can falsely accept a rootfs whose / permissions differ.
    root_stat = root.lstat()
    try:
        root_attrs = {key: os.getxattr(root, key, follow_symlinks=False).hex()
                      for key in os.listxattr(root, follow_symlinks=False)}
    except OSError as exc:
        raise ValueError("XATTR_INSPECTION_FAILED: .") from exc
    result["."] = ("dir", "", stat.S_IMODE(root_stat.st_mode),
                   root_stat.st_uid, root_stat.st_gid, root_attrs)
    hardlink_groups = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            st = p.lstat()
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISLNK(st.st_mode):
                kind, value = "link", os.readlink(p)
            elif stat.S_ISDIR(st.st_mode):
                kind, value = "dir", ""
            elif stat.S_ISREG(st.st_mode):
                kind, value = "file", sha(p)
                if st.st_nlink > 1:
                    hardlink_groups.setdefault((st.st_dev, st.st_ino), []).append(rel)
            else:
                raise ValueError("SPECIAL_FILE: " + rel)
            try:
                attrs = {key: os.getxattr(p, key, follow_symlinks=False).hex()
                         for key in os.listxattr(p, follow_symlinks=False)}
            except OSError as exc:
                raise ValueError("XATTR_INSPECTION_FAILED: " + rel) from exc
            result[rel] = (kind, value, mode, st.st_uid, st.st_gid, attrs)
            if kind == "link" and name in dirs:
                dirs.remove(name)
    # Compare hardlink equivalence classes, never raw inode numbers (which
    # differ between staging and a separately extracted SquashFS image).
    for paths in hardlink_groups.values():
        if len(paths) > 1:
            group = tuple(sorted(paths))
            for rel in group:
                result[rel] += (group,)
    return result

def verify(root, p26, raw):
    if root.is_symlink() or not root.is_dir() or p26.is_symlink() or raw.is_symlink():
        raise ValueError("INVALID_INPUT")
    if p26.stat().st_size != SIZE:
        raise ValueError("PARTITION_SIZE")
    raw_size = raw.stat().st_size
    if not 0 < raw_size < SIZE:
        raise ValueError("SQUASHFS_SIZE")
    with raw.open("rb") as source, p26.open("rb") as partition:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            if partition.read(len(block)) != block:
                raise ValueError("PREFIX_MISMATCH")
        for block in iter(lambda: partition.read(1024 * 1024), b""):
            if any(block):
                raise ValueError("NONZERO_PADDING")
    with tempfile.TemporaryDirectory(prefix="p26-independent-") as tmp:
        dest = Path(tmp) / "extracted"
        subprocess.run(["unsquashfs", "-no-progress", "-d", str(dest), str(raw)],
                       check=True, timeout=1800)
        expected = inventory(root)
        actual = inventory(dest)
        if expected != actual:
            differences = sorted(k for k in expected.keys() | actual.keys()
                                 if expected.get(k) != actual.get(k))
            raise ValueError("TREE_METADATA_OR_CONTENT_MISMATCH: " + repr(differences[:12]))
    return sha(p26)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--p26", type=Path, required=True)
    parser.add_argument("--squashfs", type=Path, required=True)
    args = parser.parse_args()
    print("P26_INDEPENDENT_READBACK_PASS", verify(args.rootfs, args.p26, args.squashfs))
