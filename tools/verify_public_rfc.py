#!/usr/bin/env python3
"""Verify the exact source-only RFC archive member set and byte digests."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

from package_public_rfc import BASE, FILES


def verify(path: Path) -> None:
    expected = {f"{BASE}/{name}" for name in FILES}
    expected.add(f"{BASE}/manifest.json")
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != expected:
            raise ValueError("Archive member set mismatch: extra, missing or duplicate entry")
        if any(not m.isfile() or m.issym() or m.islnk() for m in members):
            raise ValueError("Archive contains a non-regular file")
        manifest = json.load(archive.extractfile(f"{BASE}/manifest.json"))
        if manifest.get("format") != "source-rfc-v1" or manifest.get("flashable") is not False:
            raise ValueError("Wrong archive format or flashable safety marker")
        records = manifest.get("files")
        if not isinstance(records, dict) or set(records) != set(FILES):
            raise ValueError("Unexpected manifest file set")
        for name in FILES:
            data = archive.extractfile(f"{BASE}/{name}").read()
            entry = records[name]
            if entry != {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}:
                raise ValueError(f"Integrity check failed: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    verify(args.archive)
    print("SOURCE_RFC_ARCHIVE_VERIFIED: source-only contents and hashes match")
