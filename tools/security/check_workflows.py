#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative, dependency-free CI workflow policy check.

This is a text-level denylist, NOT a complete YAML semantic/security audit.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PROHIBITED = [
    ("untrusted privileged event", re.compile(r"\b(?:pull_request_target|workflow_run|repository_dispatch)\s*:")),
    ("self-hosted runner", re.compile(r"\bself-hosted\b")),
    ("secret expression", re.compile(r"\bsecrets\s*[\[.]")),
    ("privileged shell", re.compile(r"\bsudo\s")),
    ("token write permission", re.compile(r"\b(?:contents|actions|id-token|issues|pull-requests|packages)\s*:\s*write\b")),
    ("floating action reference", re.compile(r"(?m)^\s*-\s*uses:\s*[^\n@]+@(?![0-9a-f]{40}(?:\s|$))[^\s#]+")),
]

def check(text: str):
    violations = [category for category, pattern in PROHIBITED if pattern.search(text)]
    if not re.search(r"(?m)^\s+runs-on:\s+ubuntu-latest\s*$", text):
        violations.append("must use isolated GitHub-hosted ubuntu-latest")
    if not re.search(r"(?m)^\s+contents:\s+read\s*$", text):
        violations.append("must explicitly restrict contents permission to read")
    return violations

def main() -> int:
    paths = sorted((ROOT / ".github/workflows").glob("*.yml"))
    if not paths:
        print("BLOCKED: no workflows found")
        return 1
    failures = 0
    for path in paths:
        result = check(path.read_text(encoding="utf-8"))
        for category in result:
            print(f"BLOCKED: {path.name}: {category}")
        failures += len(result)
    print(f"Workflow files={len(paths)}, findings={failures}")
    print("LIMIT: static policy check does not validate workflow semantics or GitHub account settings")
    return int(bool(failures))

if __name__ == "__main__":
    sys.exit(main())
