#!/usr/bin/env bash
# Fictional providers exist only for validating phandle resolution off-device.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v dtc >/dev/null
command -v fdtget >/dev/null
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 "$ROOT/tools/check_sgmii_phandles.py" "$ROOT/tests/fixtures/sgmii-linked.dts"
dtc -I dts -O dtb -o "$TMP/linked.dtb" "$ROOT/tests/fixtures/sgmii-linked.dts"
for NODE in /sgmiiphy@11E60000 /sgmiisys@11305000; do
    test "$(fdtget -t s "$TMP/linked.dtb" "$NODE" status)" = disabled
done
test -n "$(fdtget -t x "$TMP/linked.dtb" /sgmiisys@11305000 phys)"
test -n "$(fdtget -t x "$TMP/linked.dtb" /sgmiiphy@11E60000 power-domains)"
echo "PASS: synthetic DTS phandle resolution, both nodes disabled."
echo "NOT real board binding validation or evidence of correct power-domain values."
