#!/usr/bin/env bash
# Compile-only validation. Never applies overlays or creates a flashable image.
set -euo pipefail
command -v dtc >/dev/null || { echo 'dtc required' >&2; exit 2; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/board/mt6990-air-terminal-6-sgmii1-experimental.dtso"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
dtc -@ -I dts -O dtb -o "$out/candidate.dtbo" "$src"
dtc -I dtb -O dts -o "$out/candidate.dts" "$out/candidate.dtbo" 2>/dev/null
grep -q 'sgmiiphy@11E60000' "$out/candidate.dts"
grep -q 'sgmiisys@11305000' "$out/candidate.dts"
grep -q 'status = "disabled"' "$out/candidate.dts"
echo "PASS: isolated DT overlay syntax, NOT a functional board DTS"
