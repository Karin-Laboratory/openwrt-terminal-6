#!/usr/bin/env python3
"""Create a local, untracked Test32 -> Test34 comparison report.

No source lines, diff hunks, private paths or firmware are printed or published.
Only exact pairs with known SHA-256 values can be compared.
"""
import argparse
import difflib
from pathlib import Path
import sys

from verify_test34_source import DIGESTS, verify

FILES = ("mtk_eth_soc.c", "mtk_eth_soc.h")


def summarize(before: Path, after: Path) -> bool:
    if not verify(before, "test32") or not verify(after, "test34"):
        print("NO-GO: identity check failed; no comparison performed")
        return False
    for filename in FILES:
        left = (before / filename).read_bytes().splitlines(keepends=True)
        right = (after / filename).read_bytes().splitlines(keepends=True)
        hunks = difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes()
        additions = sum(j2 - j1 for tag, i1, i2, j1, j2 in hunks
                        if tag in ("insert", "replace"))
        deletions = sum(i2 - i1 for tag, i1, i2, j1, j2 in hunks
                        if tag in ("delete", "replace"))
        print(f"{filename}: before={len(left)} lines after={len(right)} lines "
              f"added/replaced={additions} removed/replaced={deletions}")
    print("LOCAL METADATA ONLY; no patch emitted, uploaded or licensed")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-dir", required=True, type=Path)
    parser.add_argument("--after-dir", required=True, type=Path)
    args = parser.parse_args()
    return 0 if summarize(args.before_dir, args.after_dir) else 1


if __name__ == "__main__":
    sys.exit(main())
