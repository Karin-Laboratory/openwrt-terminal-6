#!/usr/bin/env python3
"""Static RFC patch checks; no kernel or device access.

Checks only visible diff structure. It does not prove runtime quiescence.
"""
from pathlib import Path
import sys

PATCH = Path("patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch")
CANCEL = (
    "+\tcancel_work_sync(&eth->pending_work);",
    "+\tcancel_delayed_work_sync(&eth->reset.monitor_work);",
)


def check(content: str) -> None:
    hunks = content.split("\n@@ ")
    if len(hunks) != 3:
        raise ValueError("expected exactly two diff hunks")
    cleanup, remove = hunks[1:]
    if "static int mtk_cleanup(struct mtk_eth *eth)" not in cleanup:
        raise ValueError("first hunk must modify mtk_cleanup")
    for code in CANCEL:
        if cleanup.count(code) != 1 or remove.count(code) != 1:
            raise ValueError(f"missing/duplicate cancellation: {code}")
    if cleanup.index(CANCEL[0]) > cleanup.index(" \tmtk_free_dev(eth);"):
        raise ValueError("cleanup cancellation must precede free")
    if remove.index(CANCEL[0]) > remove.index(" \tmtk_hw_deinit(eth);"):
        raise ValueError("remove cancellation must precede hardware teardown")
    if "requeue" not in content.lower():
        raise ValueError("known requeue limitation must remain documented")


if __name__ == "__main__":
    try:
        check(PATCH.read_text())
    except (OSError, ValueError) as exc:
        print(f"RFC STRUCTURE FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    print("RFC STRUCTURE PASS (static check only; no runtime safety claim)")
