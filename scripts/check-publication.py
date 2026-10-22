#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative checks for accidentally committed binary firmware files."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK_SUFFIX = {".img", ".bin", ".itb", ".dtb", ".dtbo", ".trx",
                ".ubi", ".squashfs", ".ext4", ".pem", ".key", ".zip"}
BLOCK_PARTS = {"originals", "vendor-dumps", "private", "secrets"}
BLOCK_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "secrets.json"}

def main():
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = [pathlib.PurePosixPath(x.decode("utf-8")) for x in output.split(b"\0") if x]
    failures = []
    for path in paths:
        location = ROOT.joinpath(*path.parts)
        if (path.suffix.lower() in BLOCK_SUFFIX
            or path.name.lower() in BLOCK_NAMES
            or any(p.lower() in BLOCK_PARTS for p in path.parts)):
            failures.append(f"{path}: blocked name or directory")
        elif not location.is_file() or location.is_symlink():
            failures.append(f"{path}: non-regular file")
        elif location.stat().st_size > 1048576:
            failures.append(f"{path}: exceeds 1 MiB review threshold")
        elif b"\0" in location.read_bytes():
            failures.append(f"{path}: binary content")
    for failure in failures:
        print("FAIL:", failure)
    print(f"Checked {len(paths)} tracked files; {len(failures)} blocked")
    print("Manual origin, license, identity and credential review required.")
    return bool(failures)

if __name__ == "__main__":
    sys.exit(main())
