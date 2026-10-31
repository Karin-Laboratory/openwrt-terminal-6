#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Build musl from pinned public source and compile a static ARM64 BusyBox stage.
# Research-only, ephemeral and noninstallable: never run/ship the binaries.
set -euo pipefail
umask 077
if (( EUID == 0 )); then
  echo 'Refusing musl build as root' >&2
  exit 2
fi
[[ "$(uname -m)" == aarch64 ]] || {
  echo 'Requires a native GitHub-hosted AArch64 environment' >&2
  exit 2
}
for tool in git make gcc timeout mktemp sha256sum python3; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool" >&2; exit 2; }
done
if (( $# != 0 && $# != 2 )); then
  echo 'usage: build-arm64-musl-busybox-stage.sh [NEW_CPIO_GZ NEW_MANIFEST]' >&2
  exit 2
fi
if (( $# == 2 )); then
  [[ "$1" != "$2" && ! -e "$1" && ! -L "$1" && ! -e "$2" && ! -L "$2" ]] || {
    echo 'Initramfs outputs must be distinct and absent' >&2; exit 2;
  }
  stage_mode=native-musl-static-initramfs
else
  stage_mode=native-musl-static-stage
fi
tmp="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-musl.XXXXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT

# Public upstream musl 1.2.5 mirror. The tag is NOT a floating branch:
# refuse a changed target, and never execute arbitrary donor build scripts.
timeout 180s git -c protocol.version=2 clone --quiet --depth 1 \
  --single-branch --branch v1.2.5 \
  https://github.com/ifduyue/musl.git "$tmp/musl"
test "$(git -C "$tmp/musl" rev-parse HEAD)" = \
  0784374d561435f7c787a555aeab8ede699ed298 || {
  echo 'Pinned musl source revision mismatch' >&2
  exit 1
}
(
  cd "$tmp/musl"
  ./configure --prefix="$tmp/musl-prefix" \
    --syslibdir="$tmp/musl-prefix/lib" --disable-shared
  timeout 360s make -j2
  timeout 180s make install
)
# Musl intentionally does not ship Linux UAPI headers. Install them from
# the SAME pinned upstream Linux v6.18 used by our ARM64 Image research
# build, rather than accidentally falling back to glibc's host headers.
timeout 600s git -c protocol.version=2 clone --quiet --depth 1 \
  --filter=blob:none --single-branch --branch v6.18 \
  https://github.com/torvalds/linux.git "$tmp/linux"
test "$(git -C "$tmp/linux" rev-parse HEAD)" = \
  7d0a66e4bb9081d75c82ec4957c50034cb0ea449 || {
  echo 'Pinned Linux UAPI revision mismatch' >&2
  exit 1
}
timeout 240s make -C "$tmp/linux" ARCH=arm64 \
  INSTALL_HDR_PATH="$tmp/kernel-headers" headers_install
cp -a "$tmp/kernel-headers/include/." "$tmp/musl-prefix/include/"
test -f "$tmp/musl-prefix/include/linux/kd.h"
muslcc="$tmp/musl-prefix/bin/musl-gcc"
test -x "$muslcc"
# Compiler and libc are native ARM64; no prebuilt cross SDK or donor firmware.
# The BusyBox helper independently checks pinned source, ELF64 AArch64,
# static linkage, deterministic archive and noninstallable manifest.
SBAT6_MUSL_CC="$muslcc" \
  bash "$(dirname "${BASH_SOURCE[0]}")/build-arm64-busybox-smoke.sh" \
  "$stage_mode" "$@"
if (( $# == 2 )); then
  test -s "$1" && test -s "$2"
  python3 - "$2" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    manifest = json.load(stream)
assert manifest["libc"] == "musl-static"
assert manifest["scope"] == "NONINSTALLABLE_MUSL_STATIC_BUSYBOX_PID1_INITRAMFS"
assert manifest["rights_review"] == "pending"
print("SBAT6_NATIVE_MUSL_STATIC_PID1_INITRAMFS_PASS")
PY
else
  echo 'SBAT6_NATIVE_MUSL_STATIC_BUSYBOX_STAGE_PASS'
fi
# Build the actual OpenWrt libubox core with the same pinned musl toolchain
# only in the explicit hosted userland dependency job, not the Image job.
if [[ "${SBAT6_BUILD_LIBUBOX_CORE:-0}" == 1 ]]; then
  bash "$(dirname "${BASH_SOURCE[0]}")/build-arm64-musl-libubox-core.sh" "$muslcc"
fi
echo 'LIMIT: not an OpenWrt-built musl toolchain, procd/netifd rootfs, AP or release.'
