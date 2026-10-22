#!/usr/bin/env python3
"""Read-only applicability report for user-supplied textual git patches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def examine(kernel, files):
    if not (kernel / ".git").exists():
        raise ValueError("Expected a git-managed source tree")
    reports = []
    for patch in files:
        if not patch.is_file() or patch.is_symlink():
            raise ValueError(f"Not a regular patch file: {patch}")
        data = patch.read_bytes()
        if len(data) > 8_000_000 or b"\0" in data or b"--- a/" not in data or b"+++ b/" not in data:
            raise ValueError(f"Invalid text patch: {patch.name}")
        outcomes = []
        for reverse in (False, True):
            command = ["git", "-C", str(kernel), "apply", "--check"]
            if reverse:
                command.append("--reverse")
            command.append(str(patch))
            result = subprocess.run(command, capture_output=True, text=True, timeout=45)
            outcomes.append(result.returncode)
        fwd, rev = outcomes
        status = ("ambiguous" if fwd == 0 and rev == 0 else
                  "applicable" if fwd == 0 else
                  "already-applied" if rev == 0 else
                  "conflict-or-dependency")
        reports.append({"name": patch.name, "sha256": hashlib.sha256(data).hexdigest(),
                        "forward_rc": fwd, "reverse_rc": rev, "status": status})
    return {"mode": "READ_ONLY_NO_APPLY", "patches": reports,
            "caution": "Applicability does not prove licensing, compilation, runtime safety, or patch ordering."}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("patches", nargs="+", type=Path)
    args = p.parse_args()
    print(json.dumps(examine(args.source.resolve(), [x.resolve() for x in args.patches]), indent=2))

if __name__ == "__main__":
    main()
