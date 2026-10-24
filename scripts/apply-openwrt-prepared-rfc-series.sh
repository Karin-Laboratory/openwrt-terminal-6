#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Apply the reviewed sequence only to the pinned OpenWrt prepared-source snapshot.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 /path/to/openwrt/build_dir/target-.../linux-.../linux-6.18.55" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TREE="$1"

python3 "$ROOT/tools/check_openwrt_prepared_blobs.py" "$TREE" --require-exact

(cd "$TREE" && patch --batch --fuzz=0 --dry-run -p1 < "$ROOT/patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch")
(cd "$TREE" && patch --batch --fuzz=0 -p1 < "$ROOT/patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch")
(cd "$TREE" && patch --batch --fuzz=0 --dry-run -p1 < "$ROOT/patches/rfc/0002-openwrt-6.18.55-serialize-reset-requeue.patch")
(cd "$TREE" && patch --batch --fuzz=0 -p1 < "$ROOT/patches/rfc/0002-openwrt-6.18.55-serialize-reset-requeue.patch")

python3 "$ROOT/tools/check_mediatek_rfc_series.py" --source "$TREE"
echo "PASS: RFC1 plus the OpenWrt 6.18.55 rebase applied to the pinned source snapshot."
echo "This performs source edits only; compile, runtime and SBAT6D compatibility are separate checks."
