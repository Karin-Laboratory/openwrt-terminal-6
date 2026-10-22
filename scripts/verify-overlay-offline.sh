#!/usr/bin/env bash
# Synthetic DT fixture only. No hardware, vendor DTB, or firmware modification.
set -euo pipefail
for cmd in dtc fdtoverlay fdtget; do command -v "$cmd" >/dev/null || exit 2; done
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
dtc -I dts -O dtb -o "$temp/base.dtb" "$root/tests/fixtures/sgmii-base.dts"
dtc -@ -I dts -O dtb -o "$temp/patch.dtbo" "$root/board/mt6990-air-terminal-6-sgmii1-experimental.dtso"
fdtoverlay -i "$temp/base.dtb" -o "$temp/merged.dtb" "$temp/patch.dtbo"
for path in /sgmiiphy@11E60000 /sgmiisys@11305000; do
  test "$(fdtget -t s "$temp/merged.dtb" "$path" status)" = disabled
done
test "$(fdtget -t s "$temp/merged.dtb" /sgmiiphy@11E60000 compatible)" = mediatek,mt6990-sgmii-phy
test "$(fdtget -t s "$temp/merged.dtb" /sgmiisys@11305000 compatible)" = mediatek,mt6990-sgmiisys
echo 'PASS: synthetic base + overlay merge, both nodes remain disabled'
echo 'NOT a physical board validation, dtbs_check, or firmware build'
