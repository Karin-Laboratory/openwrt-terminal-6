#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent, fail-closed offline p26 full-byte and extracted-tree readback.

Run in a separate process from pack_p26_rootfs.py. No device, signing, or upload.
This verifier is deliberately not an attestation of OpenWrt source provenance.
"""
import argparse
import hashlib
import json
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
    # Reject symlinked ancestors as well as leaf symlinks. A staging root
    # reached through an alias could otherwise point outside the verified
    # workspace, while an image path could be swapped through a linked parent.
    for candidate in (root, p26, raw):
        if candidate.is_symlink() or any(parent.is_symlink() for parent in candidate.parents):
            raise ValueError("INVALID_INPUT")
    if not root.is_dir() or not p26.is_file() or not raw.is_file():
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


def attest(producer_receipt, attestation, p26, raw, verified_sha):
    """Separate readback attestation, never mutate producer's provisional receipt.

    Caller MUST invoke this only after verify(root, p26, raw) succeeds.
    """
    for path in (producer_receipt, p26, raw):
        if (not path.is_file() or path.is_symlink()
                or any(parent.is_symlink() for parent in path.parents)):
            raise ValueError("ATTEST_INPUT_INVALID")
    if (attestation.exists() or attestation.is_symlink()
            or any(parent.is_symlink() for parent in attestation.parents)):
        raise ValueError("ATTEST_OUTPUT_EXISTS_OR_SYMLINK")
    # Independent verification happened before this call. Rehash the actual
    # partition again immediately before attestation so an intervening
    # modification cannot inherit an obsolete verified_sha from the caller.
    if p26.stat().st_size != SIZE or sha(p26) != verified_sha:
        raise ValueError("ATTEST_P26_CHANGED_AFTER_VERIFY")
    # A zero-length or oversized replacement would otherwise pass the prefix
    # comparison vacuously (or consume partition padding). Mirror verify().
    if not 0 < raw.stat().st_size < SIZE:
        raise ValueError("ATTEST_SQUASHFS_SIZE")
    # Bind the SquashFS used for attestation to the verified partition bytes.
    # A modified raw image plus a rewritten producer receipt must not turn a
    # previously verified p26 into an attestation for a different filesystem.
    with raw.open("rb") as source, p26.open("rb") as partition:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            if partition.read(len(block)) != block:
                raise ValueError("ATTEST_SQUASHFS_CHANGED_AFTER_VERIFY")
    record = json.loads(producer_receipt.read_text())
    required = {"schema": 1, "status": "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK",
                "partition_bytes": SIZE, "signed": False,
                "hardware": "NONE", "public_binary": False}
    if not isinstance(record, dict) or any(record.get(k) != v for k, v in required.items()):
        raise ValueError("ATTEST_PRODUCER_SCOPE")
    if (record.get("p26_sha256") != verified_sha
            or record.get("squashfs_sha256") != sha(raw)
            or record.get("squashfs_bytes") != raw.stat().st_size
            or p26.stat().st_size != SIZE):
        raise ValueError("ATTEST_PRODUCER_IDENTITY")
    evidence = {
        "schema": 1, "status": "P26_INDEPENDENT_FS_READBACK_VERIFIED",
        "p26_sha256": verified_sha,
        "producer_receipt_sha256": sha(producer_receipt),
        "partition_bytes": SIZE,
        "squashfs_sha256": record["squashfs_sha256"],
        "squashfs_bytes": record["squashfs_bytes"],
        "verification": "INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA",
        "signed": False, "hardware": "NONE",
        "public_binary": False,
        "not_proven": ["physical Air6 boot", "LK acceptance",
                       "radio/runtime behavior", "publication rights"]
    }
    # Exclusive creation prevents a stale or previously attested result from
    # silently surviving a later changed p26 producer run.
    # An exception after exclusive creation must not leave a partial file
    # that looks like an independent success attestation.
    created = False
    try:
        with attestation.open("x", encoding="utf-8") as f:
            created = True
            payload = json.dumps(evidence, sort_keys=True, indent=2) + "\n"
            if f.write(payload) != len(payload):
                raise OSError("ATTEST_SHORT_WRITE")
    except BaseException:
        if created:
            attestation.unlink(missing_ok=True)
        raise
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--p26", type=Path, required=True)
    parser.add_argument("--squashfs", type=Path, required=True)
    parser.add_argument("--producer-receipt", type=Path)
    parser.add_argument("--attestation", type=Path)
    args = parser.parse_args()
    if (args.producer_receipt is None) != (args.attestation is None):
        parser.error("receipt and attestation must be specified together")
    checked_sha = verify(args.rootfs, args.p26, args.squashfs)
    if args.producer_receipt is not None:
        result = attest(args.producer_receipt, args.attestation, args.p26,
                        args.squashfs, checked_sha)
        print("P26_INDEPENDENT_ATTESTATION_PASS", result["p26_sha256"])
    print("P26_INDEPENDENT_READBACK_PASS", checked_sha)
