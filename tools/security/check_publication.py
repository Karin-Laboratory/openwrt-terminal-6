#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative read-only scanner for source-publication candidates.

Scans tracked files and, with --history, all reachable blobs under *locally
available* Git refs. This cannot inspect Actions logs, GitHub PR discussions,
unreachable objects, forks, external archives, licenses or source semantics.
Never prints matched credentials or byte content.
"""
from pathlib import Path, PurePosixPath
import argparse
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_SIZE = 300_000
BLOCK_EXT = {
    ".img", ".bin", ".dtb", ".dtbo", ".cpio", ".pem", ".key", ".p12",
    ".pfx", ".ko", ".o", ".so", ".zip", ".tar", ".gz", ".sqlite",
}
BLOCK_FILES = {"id_rsa", "id_ed25519", "authorized_keys", "kernel.config"}
RULES = {
    "private key header": re.compile(
        b"-----BEGIN " + rb"(?:OPENSSH |RSA |EC |DSA )?" +
        b"PRIVATE " + b"KEY-----"
    ),
    "cloud access token": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,})"
    ),
    "device login endpoint": re.compile(
        b"(?:root|admin)" + b"@" + rb"(?:\d{1,3}\.){3}\d{1,3}"
    ),
    "private network endpoint": re.compile(
        rb"(?<![0-9])(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![0-9])"
    ),
    "internal build directory": re.compile(
        rb"/(?:home|root|mnt)/[A-Za-z0-9_.+-]+/"
    ),
    "embedded boot command line": re.compile(
        rb'CONFIG_CMDLINE\s*=\s*"[^"\n]{15,}"'
    ),
    "potential embedded credential": re.compile(
        rb"(?m)^(?:export\s+)?(?:API_KEY|ACCESS_TOKEN|PASSWORD|PASSWD|CLIENT_SECRET|PRIVATE_KEY)\s*=\s*['\"]?[^'\"\s#]{8,}"
    ),
}
def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).stdout

def scan(path: str, payload: bytes, findings: set) -> None:
    item = PurePosixPath(path)
    if item.name in BLOCK_FILES or item.suffix.lower() in BLOCK_EXT:
        findings.add((path, "restricted artifact filename/type"))
    if len(payload) > MAX_SIZE:
        findings.add((path, "large file requires manual inspection"))
        return
    if b"\x00" in payload:
        findings.add((path, "binary content requires manual inspection"))
        return
    for category, pattern in RULES.items():
        if pattern.search(payload):
            findings.add((path, category))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = set()
    scanned = 0
    if args.history:
        objects = git("rev-list", "--objects", "--all").splitlines()
        for row in objects:
            sha_bytes, sep, path_bytes = row.partition(b" ")
            if not sep:
                continue
            sha = sha_bytes.decode("ascii")
            if git("cat-file", "-t", sha).strip() != b"blob":
                continue
            path = path_bytes.decode("utf-8", errors="replace")
            size = int(git("cat-file", "-s", sha))
            if size > MAX_SIZE:
                findings.add((path, "oversized historical blob"))
                continue
            scan(path, git("cat-file", "blob", sha), findings)
            scanned += 1
    else:
        for path_bytes in git("ls-files", "-z").split(b"\x00"):
            if not path_bytes:
                continue
            path = path_bytes.decode("utf-8", errors="replace")
            location = ROOT / path
            if not location.is_file():
                findings.add((path, "tracked file absent"))
                continue
            scan(path, location.read_bytes(), findings)
            scanned += 1
    for path, category in sorted(findings):
        print(f"BLOCKED: {path}: {category}")
    print(f"Scanned={scanned}; findings={len(findings)}")
    print("Limits: PR/Issue text, logs, forks, unreachable objects, old public copies, rights review")
    return 1 if findings else 0

if __name__ == "__main__":
    sys.exit(main())
