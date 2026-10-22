#!/usr/bin/env python3
"""Read-only, conservative Git history gate. Print paths, never blob contents."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD_EXT = {".img", ".bin", ".itb", ".dtb", ".dtbo", ".trx", ".ubi", ".squashfs", ".ext4", ".pem", ".key", ".zip"}
BAD_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "secrets.json"}
BAD_DIRS = {"originals", "vendor-dumps", "private", "secrets"}
MAX_BYTES = 1048576
SIGNATURES = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
)
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)
def main():
    # Inspect reachable commit/tree blob objects, including deleted files.
    records = git("rev-list", "--objects", "--all").splitlines()
    seen = set()
    violations = []
    blobs = 0
    # Check every name across history, including files renamed or deleted.
    historical_names = git("log", "--all", "--pretty=format:", "--name-only", "-z").split(b"\0")
    for raw_name in historical_names:
        if not raw_name.strip():
            continue
        historical_path = raw_name.decode("utf-8", "backslashreplace").strip()
        historical = pathlib.PurePosixPath(historical_path)
        if (historical.suffix.lower() in BAD_EXT or historical.name.lower() in BAD_NAMES
                or any(part.lower() in BAD_DIRS for part in historical.parts)):
            violations.append(("PATH", historical_path, "blocked historical filename"))
    for line in records:
        oid, _, raw_path = line.partition(b" ")
        if oid in seen:
            continue
        seen.add(oid)
        if git("cat-file", "-t", oid.decode()).strip() != b"blob":
            continue
        blobs += 1
        # A blob can be reachable by more than one pathname. This first path
        # is a screening hint, not proof every historical path was inspected.
        path = raw_path.decode("utf-8", "backslashreplace")
        p = pathlib.PurePosixPath(path)
        if p.suffix.lower() in BAD_EXT or p.name.lower() in BAD_NAMES or any(x.lower() in BAD_DIRS for x in p.parts):
            violations.append((oid.decode()[:12], path, "blocked historical filename"))
            continue
        length = int(git("cat-file", "-s", oid.decode()))
        if length > MAX_BYTES:
            violations.append((oid.decode()[:12], path, "historical blob >1 MiB"))
            continue
        data = git("cat-file", "blob", oid.decode())
        if b"\0" in data:
            violations.append((oid.decode()[:12], path, "historical binary content"))
        elif any(sig.search(data) for sig in SIGNATURES):
            violations.append((oid.decode()[:12], path, "possible historical secret"))
    violations = sorted(set(violations))
    for oid, path, reason in violations:
        print(f"FAIL: {oid} {path}: {reason}")
    print(f"Checked {blobs} unique reachable blobs; {len(violations)} flagged")
    print("This heuristic cannot certify absence of all secrets, licensing problems or inaccessible git refs.")
    return 1 if violations else 0
if __name__ == "__main__":
    sys.exit(main())
