#!/usr/bin/env python3
"""Release capability gate for the public SBAT6D tree.

Only SOURCE_RFC may pass until a real board DTS and public image build evidence
exist. Reject any request to label this repository as device-installable.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATCHES = (
    ROOT / "patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch",
    ROOT / "patches/rfc/0002-mediatek-serialize-reset-requeue.patch",
)


def evaluate(root: Path) -> dict:
    board = json.loads((root / "board/air-terminal-6.json").read_text())
    patches = [
        "patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch",
        "patches/rfc/0002-mediatek-serialize-reset-requeue.patch",
    ]
    missing = [p for p in patches if not (root / p).is_file()]
    reasons = []
    if board.get("status") != "experimental-evidence-only":
        reasons.append("Unreviewed board metadata status")
    if board.get("board_dts") == "NOT_YET_AVAILABLE":
        reasons.append("Validated SBAT6D board Device Tree absent")
    else:
        reasons.append("Board DTS claim requires independent build and hardware evidence")
    reasons.append("No independently reproduced complete SBAT6D OpenWrt image")
    reasons.append("No third-party approved install and recovery validation")
    return {
        "schema": "public-readiness-v1",
        "repository": "Karin-Laboratory/openwrt-terminal-6",
        "source_rfc_ready": not missing,
        "source_rfc_missing": missing,
        "firmware_release_ready": False,
        "device_install_ready": False,
        "blockers": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--require", choices=("source-rfc", "firmware"), default="source-rfc")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.root)
    output = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output, end="")
    if args.require == "firmware":
        print("NO-GO: device-ready release blocked pending independent evidence", file=sys.stderr)
        return 1
    return 0 if result["source_rfc_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
