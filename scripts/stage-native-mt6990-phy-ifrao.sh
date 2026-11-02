#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Stage byte-pinned, GPL-labelled MT6990 analog PHY + IFRAO clock sources
# into an EPHEMERAL native OpenWrt kernel build tree. Not a release/rights gate.
set -euo pipefail
if [[ $# -ne 1 || "$1" != /* || ! -d "$1" ]]; then
  echo 'usage: bash scripts/stage-native-mt6990-phy-ifrao.sh /absolute/linux-build-dir' >&2
  exit 2
fi
kernel="$(realpath "$1")"
repo="$(cd "$(dirname "$0")/.." && pwd -P)"
test -f "$kernel/drivers/phy/mediatek/Kconfig"
test -f "$kernel/drivers/clk/mediatek/Kconfig"
test -x "$kernel/scripts/config"
for command in git curl; do
  command -v "$command" >/dev/null
done
donor='https://raw.githubusercontent.com/13179415360/openwrt-mt6990-lg6851f/a40df9a5afb46716dea799acea69f17480df4d82/target/linux/mediatek/files-6.18'
fetch_checked() {
  local url="$1" dest="$2" expected="$3"
  if [[ -e "$dest" || -L "$dest" ]]; then
    echo "Refusing to overwrite MT6990 kernel input: $dest" >&2
    exit 1
  fi
  curl --fail --silent --show-error --location --retry 3 --max-time 90 \
    "$url" -o "$dest"
  if [[ "$(git hash-object "$dest")" != "$expected" ]]; then
    echo "MT6990 source identity mismatch: $dest" >&2
    exit 1
  fi
}
if grep -Eq 'config (PHY_MTK_MT6990_SGMII|COMMON_CLK_MT6990_IFRAO_AIR6_RESEARCH)' \
    "$kernel/drivers/phy/mediatek/Kconfig" "$kernel/drivers/clk/mediatek/Kconfig"; then
  echo 'MT6990 source integration already present; refusing duplicate Kconfig' >&2
  exit 1
fi
fetch_checked "$donor/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c" \
  "$kernel/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c" \
  598f9c8d0a905bf6e293157d2fd475fef54bfacd
fetch_checked "$donor/drivers/clk/mediatek/clk-mt6990-ifrao.c" \
  "$kernel/drivers/clk/mediatek/clk-mt6990-ifrao.c" \
  298a335231da6d1c7c150a49106211f2adf36128
mkdir -p "$kernel/include/dt-bindings/clock"
clock_binding="$kernel/include/dt-bindings/clock/mt6990-clk.h"
if [[ -e "$clock_binding" ]]; then
  # Same source was already pinned when compiling both Air6 DTBs.
  test ! -L "$clock_binding"
  test "$(git hash-object "$clock_binding")" = \
    eea7fbe58a5d5b7357c5ddb83eff6ffb74b3801a
else
  fetch_checked "$donor/include/dt-bindings/clock/mt6990-clk.h" \
    "$clock_binding" eea7fbe58a5d5b7357c5ddb83eff6ffb74b3801a
fi
(
  cd "$kernel"
  for patch in 0002-air6-avoid-sgmii-top-cycle.patch \
               0003-air6-check-sgmii-pll-errors.patch; do
    git apply --check "$repo/patches/mt6990/$patch"
    git apply "$repo/patches/mt6990/$patch"
  done
)
if grep -q 'mt6990_sgmii_top_cycle' \
    "$kernel/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c"; then
  echo 'Unsafe destructive SGMII TOP cycle remains' >&2
  exit 1
fi
cat >> "$kernel/drivers/phy/mediatek/Kconfig" <<'EOF'

config PHY_MTK_MT6990_SGMII
  bool "MT6990 SGMII analog PHY (Air6 noninstallable research)"
  depends on OF && ARCH_MEDIATEK && MFD_SYSCON
  select GENERIC_PHY
EOF
cat >> "$kernel/drivers/phy/mediatek/Makefile" <<'EOF'
obj-$(CONFIG_PHY_MTK_MT6990_SGMII) += phy-mtk-mt6990-sgmii.o
EOF
cat >> "$kernel/drivers/clk/mediatek/Kconfig" <<'EOF'

config COMMON_CLK_MT6990_IFRAO_AIR6_RESEARCH
  bool "MT6990 IFRAO clock provider (Air6 noninstallable research)"
  depends on ARCH_MEDIATEK && OF
  select COMMON_CLK_MEDIATEK
EOF
cat >> "$kernel/drivers/clk/mediatek/Makefile" <<'EOF'
obj-$(CONFIG_COMMON_CLK_MT6990_IFRAO_AIR6_RESEARCH) += clk-mt6990-ifrao.o
EOF
echo 'PUBLIC_MT6990_NATIVE_PHY_IFRAO_PINNED_SOURCES_STAGED'
echo 'LIMIT: sources and patches staged in ephemeral kernel only; compile, probe, hardware and redistribution rights NOT proven.'
