#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Non-installable, non-root host-only Device Tree overlay syntax verification.
# No SDK, signing, firmware, hardware access or persistent build artifacts.
set -euo pipefail
if (( EUID == 0 )); then
  echo 'Refusing to compile research Device Tree as root' >&2
  exit 2
fi
for tool in git make cc mktemp grep timeout; do
  command -v "$tool" >/dev/null || { echo "Missing preinstalled tool: $tool" >&2; exit 2; }
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO/board/mt6990-air-terminal-6-sgmii1-experimental.dtso"
test -f "$SOURCE" && test ! -L "$SOURCE"
# Lexical fail-closed checks must pass *before* invoking dtc.
python3 "$REPO/tools/board/verify_sgmii_overlay.py" --source "$SOURCE"

temporary="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-dtc-verify.XXXXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

timeout 240s git clone --quiet --depth 1 --single-branch --branch v6.18 \
  https://github.com/torvalds/linux.git "$temporary/linux"
test "$(git -C "$temporary/linux" rev-parse HEAD)" = \
  7d0a66e4bb9081d75c82ec4957c50034cb0ea449
test "$(git -C "$temporary/linux" hash-object drivers/net/ethernet/mediatek/mtk_eth_soc.c)" = \
  e68997a29191b2a8ce0868873dcfe95c79e10e56

timeout 120s make -C "$temporary/linux" ARCH=arm64 defconfig
timeout 240s make -C "$temporary/linux" ARCH=arm64 -j2 scripts_dtc
DTC="$temporary/linux/scripts/dtc/dtc"
test -x "$DTC"
"$DTC" -@ -I dts -O dtb -o "$temporary/sgmii-disabled.dtbo" "$SOURCE"
test -s "$temporary/sgmii-disabled.dtbo"
"$DTC" -I dtb -O dts -o "$temporary/roundtrip.dts" "$temporary/sgmii-disabled.dtbo"
test "$(grep -c 'status = "disabled";' "$temporary/roundtrip.dts")" -eq 2
if grep -Eq 'status = "(okay|ok)";' "$temporary/roundtrip.dts"; then
  echo 'FAIL: unexpectedly enabled SGMII fragment' >&2
  exit 1
fi
echo 'PINNED_LINUX_DTC_DISABLED_SGMII_OVERLAY_SYNTAX_PASS'
echo 'SOURCE-ONLY: a valid, bootable SBAT6 board DTS has NOT been established.'
