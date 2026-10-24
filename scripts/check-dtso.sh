#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile-only validation. Never applies overlays or creates a flashable image.
set -euo pipefail
command -v dtc >/dev/null || { echo 'dtc required' >&2; exit 2; }
command -v fdtget >/dev/null || { echo 'fdtget required' >&2; exit 2; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/board/mt6990-air-terminal-6-sgmii1-experimental.dtso"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
dtc -@ -I dts -O dtb -o "$out/candidate.dtbo" "$src"
dtc -I dtb -O dts -o "$out/candidate.dts" "$out/candidate.dtbo" 2>/dev/null
test "$(fdtget -t s "$out/candidate.dtbo" /fragment@0 target-path)" = /sgmiiphy@11E60000
test "$(fdtget -t s "$out/candidate.dtbo" /fragment@0/__overlay__ status)" = disabled
test "$(fdtget -t s "$out/candidate.dtbo" /fragment@1 target-path)" = /sgmiisys@11305000
test "$(fdtget -t s "$out/candidate.dtbo" /fragment@1/__overlay__ status)" = disabled
test "$(fdtget -t s "$out/candidate.dtbo" /fragment@1/__overlay__ phy-names)" = sgmii
test -n "$(fdtget -t x "$out/candidate.dtbo" /fragment@1/__overlay__ phys)"
! fdtget "$out/candidate.dtbo" /fragment@0/__overlay__ power-domains >/dev/null 2>&1
! fdtget "$out/candidate.dtbo" /fragment@1/__overlay__ power-domains >/dev/null 2>&1
echo "PASS: isolated DT overlay syntax and disabled-node/phandle invariants"
echo "NOT a functional board DTS, binding validation, or evidence of correct runtime wiring"
