#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local-only SHA-256 verifier for independently obtained build artifacts.

Not a signing utility, key verifier, LK-acceptance test or firmware release
authorization. No network, device access, shell execution, or writes.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import sys

ALLOWED_ROLES = {"kernel", "rootfs", "dtb", "firmware-metadata"}
FORBIDDEN_NAMES = {"id_rsa", "id_ed25519", "authorized_keys"}
FORBIDDEN_EXT = {".key", ".pem", ".p12", ".pfx", ".der"}
MAX_ARTIFACT_SIZE = 4 * 1024 * 1024 * 1024
REQUIRED_KEYS = {"schema", "build_revision", "inputs"}


def verify(root: Path, manifest: dict) -> list[str]:
    issues = []
    if not isinstance(manifest, dict) or set(manifest) != REQUIRED_KEYS:
        return ["invalid manifest schema"]
    if manifest["schema"] != 1:
        issues.append("unsupported manifest schema")
    if not isinstance(manifest["build_revision"], str) or not re.fullmatch(
        "[0-9a-f]{40}", manifest["build_revision"]
    ):
        issues.append("invalid build source revision")
    files = manifest["inputs"]
    if not isinstance(files, list) or not files:
        return issues + ["no input records"]
    seen = set()
    for index, record in enumerate(files):
        label = f"input#{index}"
        if not isinstance(record, dict) or set(record) != {
            "role", "path", "sha256", "size_bytes"
        }:
            issues.append(label + ": unexpected fields")
            continue
        role, name, sha, size = (record[k] for k in (
            "role", "path", "sha256", "size_bytes"
        ))
        if not isinstance(role, str) or role not in ALLOWED_ROLES:
            issues.append(label + ": unsupported role")
        if (not isinstance(name, str) or not name or "\\" in name):
            issues.append(label + ": unsafe path")
            continue
        rel = PurePosixPath(name)
        if (rel.is_absolute() or "." in rel.parts or ".." in rel.parts
                or rel.name.lower() in FORBIDDEN_NAMES
                or rel.suffix.lower() in FORBIDDEN_EXT):
            issues.append(label + ": forbidden artifact path")
            continue
        if name in seen:
            issues.append(label + ": duplicated artifact")
            continue
        seen.add(name)
        if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
            issues.append(label + ": invalid SHA-256")
            continue
        if type(size) is not int or not 0 <= size <= MAX_ARTIFACT_SIZE:
            issues.append(label + ": invalid bounded artifact size")
            continue
        path = root.joinpath(*rel.parts)
        try:
            resolved_root = root.resolve(strict=True)
            resolved_path = path.resolve(strict=True)
            if not resolved_path.is_relative_to(resolved_root):
                issues.append(label + ": escaped input root")
                continue
            if any(part.is_symlink() for part in (
                root.joinpath(*rel.parts[:n]) for n in range(1, len(rel.parts) + 1)
            )):
                issues.append(label + ": symbolic link is forbidden")
                continue
            if not path.is_file() or path.stat().st_size != size:
                issues.append(label + ": missing or size mismatch")
                continue
            digest = hashlib.sha256()
            with path.open("rb") as file:
                while chunk := file.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != sha:
                issues.append(label + ": SHA-256 mismatch")
        except (OSError, RuntimeError):
            issues.append(label + ": unreadable input")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.manifest.is_symlink() or not args.manifest.is_file():
            raise ValueError("manifest unavailable")
        if args.manifest.stat().st_size > 128_000:
            raise ValueError("manifest too large")
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        issues = verify(args.root, data)
    except (OSError, UnicodeError, ValueError, TypeError):
        print("INPUT MANIFEST FAIL: invalid or unreadable manifest")
        return 2
    for issue in issues:
        print("INPUT MANIFEST BLOCKED:", issue)
    print(f"Input identity checks: {len(data.get('inputs', []))}; findings={len(issues)}")
    print("LIMIT: SHA-256 is not signing, firmware authorization or recovery proof")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
