#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative read-only scanner for source-publication candidates.

--history inspects every file path of every reachable commit on locally
available Git refs. It does NOT inspect unreachable/deleted Git objects,
remote PR/Issue conversations, Actions logs, external archives or licenses.
Results contain only category and escaped path, never matched secret bytes.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MAX_SIZE = 300_000
MAX_COMMITS = 20_000
BLOCK_EXT = {
    ".img", ".bin", ".dtb", ".dtbo", ".cpio", ".pem", ".key", ".p12",
    ".pfx", ".ko", ".o", ".so", ".zip", ".tar", ".gz", ".sqlite",
}
BLOCK_FILES = {"id_rsa", "id_ed25519", "authorized_keys", "kernel.config"}
RULES = {
    "private key header": re.compile(
        # Include encrypted PKCS#8 and OpenPGP secret-key armor, not only
        # unencrypted PEM/OpenSSH key blocks. Do not log matching bytes.
        b"-----BEGIN " +
        rb"(?:(?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"
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
    # Indented assignments can carry secrets too. Horizontal whitespace
    # prevents a preceding newline from acting as an export prefix.
    "potential embedded credential": re.compile(
        rb"(?m)^[ \t]*(?:export[ \t]+)?(?:API_KEY|ACCESS_TOKEN|PASSWORD|PASSWD|CLIENT_SECRET|PRIVATE_KEY)[ \t]*=[ \t]*['\"]?[^'\"\s#]{8,}"
    ),
}

def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout

def scan(path: str, payload: bytes, findings: set) -> None:
    item = PurePosixPath(path)
    if item.name.lower() in BLOCK_FILES or item.suffix.lower() in BLOCK_EXT:
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

def history_findings(findings: set) -> int:
    """Scan path/blob PAIRS, not only blob IDs: same blob may have risky alias."""
    if git("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("shallow clone: cannot certify reachable history")
    # Ref names are public metadata but are not commit/tree/blob contents.
    # Scan them without echoing the names: a name itself may contain a token.
    # Git replace refs can change what rev-list/cat-file appear to traverse.
    # rev-list --all walks commits, not standalone blobs/trees targeted by
    # lightweight tags or annotated tags. Such objects bypass blob scanning.
    # Reject those refs rather than claiming a complete reachable audit.
    # Enumerate names first: dereferencing object types can itself fail when
    # a replace ref creates a cycle. Reject replace refs before that lookup.
    refs = [ref for ref in git("for-each-ref", "--format=%(refname)", "refs").splitlines() if ref]
    ref_set = set(refs)
    if len(refs) != len(ref_set):
        raise ValueError("duplicate Git ref metadata")
    for ref in refs:
        if not ref.startswith(b"refs/") or ref.startswith(b"refs/replace/"):
            raise ValueError("unsupported or replace ref: history cannot be certified")
        opaque_path = "@ref/" + hashlib.sha256(ref).hexdigest()[:12]
        scan(opaque_path, ref, findings)
    # Fail closed if refs change between name enumeration and type inspection.
    seen = set()
    for row in git("for-each-ref",
                   "--format=%(refname)%00%(objecttype)%00%(*objecttype)",
                   "refs").splitlines():
        parts = row.split(b"\x00")
        if len(parts) != 3:
            raise ValueError("malformed Git ref metadata")
        ref, obj_type, peeled_type = parts
        if ref not in ref_set or ref in seen:
            raise ValueError("Git refs changed during audit")
        seen.add(ref)
        if not (obj_type == b"commit" or
                (obj_type == b"tag" and peeled_type == b"commit")):
            raise ValueError("non-commit Git ref: history cannot be certified")
    if seen != ref_set:
        raise ValueError("Git refs changed during audit")
    commits = [c for c in git("rev-list", "--all").splitlines() if c]
    if len(commits) > MAX_COMMITS:
        raise ValueError("commit safety limit exceeded; manual audit needed")
    pairs = set()
    scanned = 0
    for commit in commits:
        commit_sha = commit.decode("ascii")
        scan("@commit/" + commit_sha[:12], git("cat-file", "commit", commit_sha), findings)
        scanned += 1
        # NUL-delimited file paths avoid newline, tab and whitespace ambiguity.
        for entry in git("ls-tree", "-r", "-z", commit.decode("ascii")).split(b"\x00"):
            if not entry:
                continue
            meta, sep, path_raw = entry.partition(b"\t")
            if not sep:
                raise ValueError("malformed Git tree entry")
            mode, kind, sha_raw = meta.split(b" ")
            path = path_raw.decode("utf-8", errors="backslashreplace")
            if kind != b"blob":
                findings.add((path, "gitlink or unsupported object requires review"))
                continue
            if mode == b"120000":
                findings.add((path, "symlink requires manual review"))
            sha = sha_raw.decode("ascii")
            if (sha, path) in pairs:
                continue
            pairs.add((sha, path))
            size = int(git("cat-file", "-s", sha))
            if size > MAX_SIZE:
                findings.add((path, "oversized historical blob"))
                continue
            scan(path, git("cat-file", "blob", sha), findings)
            scanned += 1
    # Annotated tags may contain their own sensitive metadata even when the
    # commits and tree contents are clean.
    for row in git("for-each-ref", "--format=%(objectname) %(objecttype)", "refs/tags").splitlines():
        ref_sha, sep, ref_type = row.partition(b" ")
        if not sep:
            raise ValueError("malformed tag reference")
        if ref_type == b"tag":
            label = ref_sha.decode("ascii")
            scan("@tag/" + label[:12], git("cat-file", "tag", label), findings)
            scanned += 1
    return scanned

def current_findings(findings: set) -> int:
    scanned = 0
    for path_raw in git("ls-files", "-z").split(b"\x00"):
        if not path_raw:
            continue
        path = path_raw.decode("utf-8", errors="backslashreplace")
        location = ROOT / path
        if not location.is_file() or location.is_symlink():
            findings.add((path, "tracked file absent or symlink"))
            continue
        scan(path, location.read_bytes(), findings)
        scanned += 1
    return scanned

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = set()
    try:
        scanned = history_findings(findings) if args.history else current_findings(findings)
    except (subprocess.CalledProcessError, ValueError, OSError) as exc:
        print(f"BLOCKED: unable to complete Git audit ({type(exc).__name__})", file=sys.stderr)
        return 2
    for path, category in sorted(findings):
        # repr escapes control characters in paths; matched secret values are never shown.
        print(f"BLOCKED: {ascii(path)}: {category}")
    print(f"Scanned={scanned}; findings={len(findings)}")
    print("LIMITS: remote PR/Issue text, CI logs, forks, unreachable Git objects, old copies, rights")
    return 1 if findings else 0

if __name__ == "__main__":
    sys.exit(main())
