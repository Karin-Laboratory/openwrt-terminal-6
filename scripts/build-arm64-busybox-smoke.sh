#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile an upstream ARM64 BusyBox binary ONLY. Never install or execute it.
set -euo pipefail
umask 077
if (( EUID == 0 )); then
  echo 'Refusing public-source build as root' >&2
  exit 2
fi
for tool in git make timeout mktemp sha256sum python3 grep sed; do
  command -v "$tool" >/dev/null || { echo "Missing preinstalled tool: $tool" >&2; exit 2; }
done
# Explicit native mode is only valid on a GitHub-hosted AArch64 runner.
# The original cross-compiler mode remains unchanged for local toolchains.
prefix="${1:-aarch64-openwrt-linux-musl-}"
if [[ "$prefix" == native ]]; then
  [[ "$(uname -m)" == aarch64 ]] || {
    echo 'Native BusyBox build requires an AArch64 host' >&2; exit 2;
  }
  prefix=""
else
  if [[ ! "$prefix" =~ ^[a-z0-9_-]{6,60}-$ ]]; then
    echo 'Compiler prefix must be a literal, non-path AArch64 tool prefix' >&2
    exit 2
  fi
fi
command -v "${prefix}gcc" >/dev/null || { echo 'Missing preinstalled ARM64 compiler' >&2; exit 2; }
"${prefix}gcc" --version | head -n 1
tmp="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-busybox-src.XXXXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT

# The tag target and Makefile are pinned, preventing a floating master build.
timeout 180s git clone --quiet --depth 1 --single-branch --branch 1_36_1 \
  https://github.com/mirror/busybox.git "$tmp/busybox"
test "$(git -C "$tmp/busybox" rev-parse HEAD)" = \
  1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4
test "$(git -C "$tmp/busybox" hash-object Makefile)" = \
  fa8cb761443388730372eaf260e7ca1a0235bc43

timeout 120s make -C "$tmp/busybox" ARCH=arm64 CROSS_COMPILE="$prefix" defconfig
# This is a limited cross-toolchain smoke, not a device rootfs profile.
# BusyBox 1.36.1's optional tc/CBQ applet needs older Linux UAPI types.
# Disable only that legacy applet, without patching host kernel headers.
grep -q '^CONFIG_TC=y$' "$tmp/busybox/.config"
sed -i 's/^CONFIG_TC=y$/# CONFIG_TC is not set/' "$tmp/busybox/.config"
grep -q '^# CONFIG_TC is not set$' "$tmp/busybox/.config"

timeout 450s make -C "$tmp/busybox" ARCH=arm64 CROSS_COMPILE="$prefix" -j2 busybox
test -s "$tmp/busybox/busybox"

# Read only the ELF header; never execute the cross-compiled binary.
python3 - "$tmp/busybox/busybox" <<'PY'
import pathlib
import struct
import sys

with pathlib.Path(sys.argv[1]).open("rb") as infile:
    header = infile.read(64)
if (len(header) < 64 or header[:4] != b'\x7fELF'
        or header[4] != 2 or header[5] != 1
        or struct.unpack_from("<H", header, 18)[0] != 183):
    raise SystemExit("BLOCKED: BusyBox is not little-endian ELF64 AArch64")
print("BUSYBOX_ARM64_ELF_HEADER_PASS")
PY
digest="$(sha256sum "$tmp/busybox/busybox" | cut -d' ' -f1)"
bytes="$(wc -c < "$tmp/busybox/busybox")"
echo "BusyBox 1.36.1 ARM64 ELF size_bytes=$bytes sha256=$digest"
echo 'ARM64_BUSYBOX_SOURCE_COMPILE_PASS'
echo 'LIMIT: not an OpenWrt rootfs or board firmware; no output is released.'
