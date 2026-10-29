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
mkdir -p "$TEMP/include/dt-bindings/interrupt-controller" "$TEMP/include/dt-bindings/gpio" "$TEMP/include/dt-bindings/power" "$TEMP/include/dt-bindings/clock"
BASE=https://raw.githubusercontent.com/13179415360/openwrt-mt6990-lg6851f/a40df9a5afb46716dea799acea69f17480df4d82
get_pinned() {
  local url="$1" target="$2" blob="$3"
  if ! curl --fail --silent --show-error --location --retry 2 --max-time 60 "$url" -o "$target"; then
    # Exact pinned revision is encoded in BASE; never use an unpinned HEAD.
    local rel="${url#"$BASE"/}"
    curl --fail --silent --show-error --retry 2 --max-time 60 \
      -H 'Accept: application/vnd.github+json' \
      "https://api.github.com/repos/13179415360/openwrt-mt6990-lg6851f/contents/$rel?ref=a40df9a5afb46716dea799acea69f17480df4d82" \
      -o "$TEMP/donor-source.json"
    python3 - "$TEMP/donor-source.json" "$target" <<'PY'
import base64, json, pathlib, sys
record = json.loads(pathlib.Path(sys.argv[1]).read_text())
if record.get('encoding') != 'base64' or record.get('type') != 'file':
    raise SystemExit('Unexpected pinned GitHub source response')
pathlib.Path(sys.argv[2]).write_bytes(base64.b64decode(record['content'], validate=False))
PY
  fi
  test "$(git hash-object "$target")" = "$blob" || {
    echo "Unexpected source identity: $target" >&2; exit 1;
  }
}
get_pinned "$BASE/target/linux/mediatek/patches-6.18/969-arm64-dts-mediatek-add-mt6990-soc.patch" \
  "$TEMP/mt6990-soc.patch" 4f24ec8183c5495a312ec5f1109164d7b770a770
get_pinned "$BASE/target/linux/mediatek/files-6.18/include/dt-bindings/power/mt6990-power.h" \
  "$TEMP/include/dt-bindings/power/mt6990-power.h" c221b322fb437683d052ec4241a33afaecb33979
get_pinned "$BASE/target/linux/mediatek/files-6.18/include/dt-bindings/clock/mt6990-clk.h" \
  "$TEMP/include/dt-bindings/clock/mt6990-clk.h" eea7fbe58a5d5b7357c5ddb83eff6ffb74b3801a
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
  output="$TEMP/include/dt-bindings/$item"
  if ! curl --fail --silent --show-error --location --retry 2 --max-time 60 \
      "$LINUX/$item" -o "$output"; then
    curl --fail --silent --show-error --retry 2 --max-time 60 \
      -H 'Accept: application/vnd.github+json' \
      "https://api.github.com/repos/torvalds/linux/contents/include/dt-bindings/$item?ref=v6.18" \
      -o "$TEMP/linux-header.json"
    python3 - "$TEMP/linux-header.json" "$output" <<'PY'
import base64, json, pathlib, sys
record = json.loads(pathlib.Path(sys.argv[1]).read_text())
if record.get('encoding') != 'base64' or record.get('type') != 'file':
    raise SystemExit('Unexpected Linux binding header response')
pathlib.Path(sys.argv[2]).write_bytes(base64.b64decode(record['content'], validate=False))
PY
  fi
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

# Build the opt-in Ethernet/PHY variant against the same pinned SoC DTSI.
# The default board .dts remains a distinct safe baseline.
cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I "$TEMP/include" -I "$TEMP" -I "$ROOT/board" \
  "$ROOT/board/mt6990-air-terminal-6-ethernet-test.dts" "$TEMP/air6-ethernet.preprocessed.dts"
"$TEMP/dtc/dtc" -I dts -O dtb -o "$TEMP/air6-ethernet.dtbin" "$TEMP/air6-ethernet.preprocessed.dts"
"$TEMP/dtc/dtc" -I dtb -O dts -o "$TEMP/air6-ethernet.roundtrip.dts" "$TEMP/air6-ethernet.dtbin"
python3 - "$TEMP/air6-ethernet.roundtrip.dts" <<'PY'
from pathlib import Path
import re
import sys
tree = Path(sys.argv[1]).read_text()
def node(body, needle):
    match = re.search(r'(?m)^\s*' + re.escape(needle) + r'\s*\{', body)
    if not match:
        raise SystemExit('missing DT node: ' + needle)
    i = match.end()
    depth = 1
    while depth:
        if i == len(body):
            raise SystemExit('unclosed DT node: ' + needle)
        depth += (body[i] == '{') - (body[i] == '}')
        i += 1
    return body[match.end():i-1]
parent = node(tree, 'netsys@15100000')
eth = node(parent, 'ethernet@15100000')
pcs = node(tree, 'syscon@11305000')
phy = node(tree, 'phy@11e60000')
pll = node(tree, 'syscon@10014000')
for name, block, token in [
    ('NETSYS bus', parent, '"simple-bus"'),
    ('NETSYS bus cells', parent, '#address-cells = <0x02>;'),
    ('NETSYS translate', parent, 'ranges;'),
    ('Ethernet enabled', eth, 'status = "okay";'),
    ('PCS enabled', pcs, 'status = "okay";'),
    ('PHY enabled', phy, 'status = "okay";'),
    ('PHY provider', phy, '#phy-cells = <0x00>;'),
    ('PLL syscon', pll, '"syscon"'),
    ('MDIO switch', eth, 'switch@1f'),
    ('MAC1', eth, 'mac@1'),
    ('CPU5', eth, 'port@5')]:
    if token not in block:
        raise SystemExit(name + ': missing ' + token)
if 'ethernet@15100000' not in parent or 'phy@11e60000' not in tree:
    raise SystemExit('topology absent after DTB roundtrip')
if 'sgmii-pwr0' in parent or 'sgmii-pwr1' in parent:
    raise SystemExit('obsolete SGMII power helper survived NETSYS bus enable')
print('AIR6_NETSYS_SGMII1_DTC_PASS (SOURCE ONLY; NO COLD-BOOT CLAIM)')
PY

# Validate a narrow, GPL-aware reset change against the exact donor PHY
# source. The base file remains outside this repository; no kernel image.
mkdir -p "$TEMP/phy-source/drivers/phy/mediatek"
get_pinned "$BASE/target/linux/mediatek/files-6.18/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c" \
  "$TEMP/phy-source/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c" 598f9c8d0a905bf6e293157d2fd475fef54bfacd
(
  cd "$TEMP/phy-source"
  git apply --check "$ROOT/patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch"
  git apply "$ROOT/patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch"
  if grep -q 'mt6990_sgmii_top_cycle' drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c; then
    echo 'FAIL: destructive TOP cycle still referenced' >&2
    exit 1
  fi
)
echo 'AIR6_SGMII_PHY_RESET_SOURCE_PATCH_PASS (NO KERNEL BUILD)'
