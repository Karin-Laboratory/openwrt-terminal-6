#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Source-only Air6 board DTS syntax check against pinned LGPL/GPL-reviewed texts.
# Builds nothing flashable; no hardware, signing, sudo, or device credentials.
set -euo pipefail
if (( EUID == 0 )); then
  echo 'Refuse root execution' >&2
  exit 2
fi
for tool in curl git python3 cpp make cc flex bison sha256sum mktemp; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d "${TMPDIR:-/tmp}/air6-board-dtc.XXXXXXXX")"
trap 'rm -rf -- "$TEMP"' EXIT
mkdir -p "$TEMP/include/dt-bindings/interrupt-controller" "$TEMP/include/dt-bindings/gpio" "$TEMP/include/dt-bindings/power"
BASE=https://raw.githubusercontent.com/13179415360/openwrt-mt6990-lg6851f/a40df9a5afb46716dea799acea69f17480df4d82
get_pinned() {
  local url="$1" target="$2" blob="$3"
  curl --fail --silent --show-error --location --retry 3 --max-time 60 "$url" -o "$target"
  test "$(git hash-object "$target")" = "$blob" || {
    echo "Unexpected source identity: $target" >&2; exit 1;
  }
}
get_pinned "$BASE/target/linux/mediatek/patches-6.18/969-arm64-dts-mediatek-add-mt6990-soc.patch" \
  "$TEMP/mt6990-soc.patch" 4f24ec8183c5495a312ec5f1109164d7b770a770
get_pinned "$BASE/target/linux/mediatek/files-6.18/include/dt-bindings/power/mt6990-power.h" \
  "$TEMP/include/dt-bindings/power/mt6990-power.h" c221b322fb437683d052ec4241a33afaecb33979
# Only the SoC-specific license-identified text is extracted. No LG6851F
# board DTS, firmware, EEPROM, calibration, rootfs or donor checkout.
python3 - "$TEMP/mt6990-soc.patch" "$TEMP/mt6990.dtsi" <<'PY'
from pathlib import Path
import sys
patch = Path(sys.argv[1]).read_text().splitlines()
out = []
active = False
for line in patch:
    if line.startswith('@@ -0,0 +1,'):
        active = True
        continue
    if active and line.startswith('+'):
        out.append(line[1:])
if len(out) < 400 or not out[0].startswith('// SPDX-License-Identifier:'):
    raise SystemExit('Unrecognized MT6990 SoC source patch')
Path(sys.argv[2]).write_text('\n'.join(out) + '\n')
PY
LINUX=https://raw.githubusercontent.com/torvalds/linux/v6.18/include/dt-bindings
for item in interrupt-controller/arm-gic.h interrupt-controller/irq.h gpio/gpio.h; do
  curl --fail --silent --show-error --location --retry 3 --max-time 60 \
    "$LINUX/$item" -o "$TEMP/include/dt-bindings/$item"
done
# GCC cpp supplies the Linux DTS preprocessor for symbolic irq and power cells.
cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I "$TEMP/include" -I "$TEMP" \
  "$ROOT/board/mt6990-air-terminal-6.dts" "$TEMP/air6.preprocessed.dts"
# Same fixed public DTC release used by the existing source-only board test.
git clone -q --depth 1 --single-branch --branch v1.7.2 \
  https://github.com/dgibson/dtc.git "$TEMP/dtc"
test "$(git -C "$TEMP/dtc" rev-parse HEAD)" = 2d10aa2afe35527728db30b35ec491ecb6959e5c
make -s -C "$TEMP/dtc" -j2 NO_PYTHON=1 dtc
"$TEMP/dtc/dtc" -I dts -O dtb -o "$TEMP/air6.dtbin" "$TEMP/air6.preprocessed.dts"
"$TEMP/dtc/dtc" -I dtb -O dts -o "$TEMP/air6.roundtrip.dts" "$TEMP/air6.dtbin"
python3 - "$TEMP/air6.roundtrip.dts" <<'PY'
from pathlib import Path
import sys
tree=Path(sys.argv[1]).read_text()
must=('softbank,air-terminal-6','mediatek,mt7531','label = "lan2";',
      'label = "cpu";','phy-mode = "2500base-x";')
for token in must:
    if token not in tree:
        raise SystemExit('Missing required board DT string: ' + token)
print('AIR6_INDEPENDENT_BOARD_DTS_SYNTAX_PASS (not a bootable firmware claim)')
PY
