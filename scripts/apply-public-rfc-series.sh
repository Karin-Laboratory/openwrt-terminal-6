#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Stage the two public Ethernet RFCs in a checked-out upstream Linux v6.18 tree.
# This touches source files only. Default mode is read-only preflight.
set -euo pipefail

usage() {
  echo "Usage: $0 [--apply] /path/to/linux-v6.18" >&2
  echo "Default: verify the two RFCs can apply. --apply: modify the kernel source tree." >&2
}
MODE=check
if [[ "${1:-}" == "--apply" ]]; then MODE=apply; shift; fi
if [[ $# -ne 1 ]]; then usage; exit 2; fi
SOURCE="$(realpath -e "$1")"
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C=drivers/net/ethernet/mediatek/mtk_eth_soc.c
H=drivers/net/ethernet/mediatek/mtk_eth_soc.h
P1="$PROJECT/patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch"
P2="$PROJECT/patches/rfc/0002-mediatek-serialize-reset-requeue.patch"
[[ -d "$SOURCE/.git" || -f "$SOURCE/.git" ]] || { echo "FAIL: kernel source must be a Git worktree" >&2; exit 3; }
[[ -f "$SOURCE/$C" && -f "$SOURCE/$H" ]] || { echo "FAIL: missing MediaTek upstream files" >&2; exit 3; }
[[ "$(git -C "$SOURCE" hash-object "$C")" == e68997a29191b2a8ce0868873dcfe95c79e10e56 ]] || { echo "FAIL: C blob is not pinned Linux v6.18" >&2; exit 4; }
[[ "$(git -C "$SOURCE" hash-object "$H")" == 0168e2fbc6197a6aa9fe159767166e86915accbc ]] || { echo "FAIL: header blob is not pinned Linux v6.18" >&2; exit 4; }
[[ -z "$(git -C "$SOURCE" status --porcelain -- "$C" "$H")" ]] || { echo "FAIL: existing source edits must not be overwritten" >&2; exit 5; }

# Apply RFC1 in a private temporary copy, then verify RFC2 on that same copy.
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
mkdir -p "$TEMP/drivers/net/ethernet/mediatek"
cp "$SOURCE/$C" "$TEMP/$C"
cp "$SOURCE/$H" "$TEMP/$H"
git -C "$TEMP" apply --check "$P1"
git -C "$TEMP" apply "$P1"
git -C "$TEMP" apply --check "$P2"
git -C "$TEMP" apply "$P2"
echo "PASS: RFC1 then RFC2 apply to pinned upstream files"
if [[ "$MODE" == apply ]]; then
  # Prepare final output entirely off-tree. Copy only after both patches pass.
  # This avoids leaving half-applied RFC1 changes if RFC2 fails.
  cp "$TEMP/$C" "$SOURCE/$C"
  cp "$TEMP/$H" "$SOURCE/$H"
  git -C "$SOURCE" diff --check
  echo "PASS: verified RFC series copied into source tree; no firmware produced"
else
  echo "CHECK ONLY: no source files were modified; use --apply for explicit source changes"
fi
