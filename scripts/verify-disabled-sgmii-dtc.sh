#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Non-installable, non-root host-only Device Tree overlay syntax verification.
# Device Tree Compiler v1.7.2, exact source commit, not bundled.
# No SDK, signing, firmware, hardware access or persistent build artifacts.
set -euo pipefail
if (( EUID == 0 )); then
  echo 'Refusing to compile research Device Tree as root' >&2
  exit 2
fi
for tool in git make cc flex bison mktemp grep timeout python3; do
  command -v "$tool" >/dev/null || { echo "Missing preinstalled tool: $tool" >&2; exit 2; }
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO/board/mt6990-air-terminal-6-sgmii1-experimental.dtso"
test -f "$SOURCE" && test ! -L "$SOURCE"
# Lexical fail-closed checks must pass *before* invoking dtc.
python3 "$REPO/tools/board/verify_sgmii_overlay.py" --source "$SOURCE"

temporary="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-dtc-verify.XXXXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

# Tiny, independently maintained dtc source. A full Linux clone repeatedly
# timed out on the isolated runner; do not fetch an entire kernel for this test.
timeout 150s git clone --quiet --depth 1 --single-branch --branch v1.7.2 \
  https://github.com/dgibson/dtc.git "$temporary/dtc"
test "$(git -C "$temporary/dtc" rev-parse HEAD)" = \
  2d10aa2afe35527728db30b35ec491ecb6959e5c
timeout 150s make -C "$temporary/dtc" -j2 NO_PYTHON=1 dtc
DTC="$temporary/dtc/dtc"
test -x "$DTC"
"$DTC" -@ -I dts -O dtb -o "$temporary/sgmii-disabled.dtbo" "$SOURCE"
test -s "$temporary/sgmii-disabled.dtbo"
"$DTC" -I dtb -O dts -o "$temporary/roundtrip.dts" "$temporary/sgmii-disabled.dtbo"
test "$(grep -c 'status = "disabled";' "$temporary/roundtrip.dts")" -eq 2
if grep -Eq 'status = "(okay|ok)";' "$temporary/roundtrip.dts"; then
  echo 'FAIL: unexpectedly enabled SGMII fragment' >&2
  exit 1
fi
echo 'PINNED_STANDALONE_DTC_V1_7_2_DISABLED_SGMII_OVERLAY_PASS'
echo 'SOURCE-ONLY: a valid, bootable SBAT6 board DTS has NOT been established.'
