#!/usr/bin/env python3
"""Generate a review checklist from verified/missing board evidence, never a DTS."""
import argparse
import json
from pathlib import Path
from check_sbat6d_dts_evidence import REQUIRED, audit

def render(document):
    result = audit(document)
    checks = document.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    lines = ["# SBAT6D Device Tree evidence checklist", "",
             "Research only. No official DTS, firmware or write instructions.", "",
             "| Dependency | Evidence status | Next required proof |",
             "| --- | --- | --- |"]
    for key in REQUIRED:
        item = checks.get(key, {})
        is_verified = key in result["verified"]
        source = item.get("evidence") if isinstance(item, dict) else None
        provenance = source.get("source", "") if isinstance(source, dict) else ""
        lines.append(f"| `{key}` | {'VERIFIED' if is_verified else 'BLOCKED'} | "
                     + (f"Reviewed source: `{provenance}`" if is_verified else
                        "Independently reviewed source + SHA-256 + binding evidence required") + " |")
    lines += ["", f"**Ready for DTS review:** {'YES' if result['ready_for_board_dts_review'] else 'NO'}", "",
              "A reviewed record alone does not prove bootability. Validate the future independent DTS with dtc, dtbs_check, kernel integration and hardware tests.", ""]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    markdown = render(json.loads(args.evidence.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown)
    else:
        print(markdown, end="")

if __name__ == "__main__":
    main()
