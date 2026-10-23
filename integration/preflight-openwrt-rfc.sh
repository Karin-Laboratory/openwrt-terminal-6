#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Safe gate for integration into an already prepared, user-owned OpenWrt kernel tree.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/prepared/openwrt/linux-tree" >&2
  exit 2
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TREE="$1"
python3 "$ROOT/tools/check_openwrt_rfc_compat.py" "$TREE" --require-exact
bash "$ROOT/scripts/apply-public-rfc-series.sh" "$TREE"
echo "PASS: source is eligible for an explicitly reviewed RFC application."
echo "This preflight changed no source files, generated no firmware and ran no device commands."
