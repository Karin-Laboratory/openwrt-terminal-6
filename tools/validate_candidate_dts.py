#!/usr/bin/env python3
"""Check independent DT source for unresolved external references, no device writes.

Invokes dtc for syntax/reference diagnostics if installed. Refuses missing tools.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

def validate(source: Path):
    if not source.is_file() or source.suffix not in {".dts", ".dtso"}:
        return {"pass": False, "reason": "input must be an existing .dts or .dtso source"}
    dtc = shutil.which("dtc")
    if not dtc:
        return {"pass": False, "reason": "dtc not installed"}
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "probe.dtb"
        proc = subprocess.run([dtc, "-@", "-I", "dts", "-O", "dtb",
                               "-i", str(source.resolve().parent),
                               "-o", str(dest), str(source.resolve())],
                              text=True, capture_output=True, timeout=90)
        return {"pass": proc.returncode == 0 and dest.is_file(),
                "returncode": proc.returncode,
                "stderr": proc.stderr[-12000:],
                "note": "dtc syntax only; dtbs_check and real hardware validation pending"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    result = validate(args.source)
    print(json.dumps(result, indent=2))
    return int(args.require_pass and not result["pass"])

if __name__ == "__main__":
    sys.exit(main())
