#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile the real upstream procd init target against pinned native ARM64 musl.
# Noninstallable stage only; never execute, sign, flash or deploy the binary.
set -euo pipefail
umask 077
if (( EUID == 0 )); then
  echo 'Refusing procd init build as root' >&2; exit 2
fi
[[ "$(uname -m)" == aarch64 && $# -eq 3 && "$1" == /* &&
   "$2" == /* && "$3" == /* && -x "$1" && -s "$2" &&
   -f "$3/libubus.h" ]] || {
  echo 'usage: build-arm64-musl-procd-init.sh /absolute/musl-gcc /absolute/libubox.a /absolute/ubus-source' >&2
  exit 2
}
compiler="$1"
libubox_archive="$2"
ubus_src="$3"
libubox_root="$(dirname "$libubox_archive")"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-procd-init.XXXXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT
procd_src="$tmp/procd"
  git init --quiet "$procd_src"
  git -C "$procd_src" remote add origin https://github.com/openwrt/procd.git
  procd_revision=5aef7c33b01455157c1373a14e2a3fa47d024c6c
  timeout 180s git -C "$procd_src" -c protocol.version=2 fetch --quiet --depth 1 origin "$procd_revision"
  test "$(git -C "$procd_src" rev-parse FETCH_HEAD)" = "$procd_revision"
  git -C "$procd_src" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$procd_src" rev-parse HEAD)" = "$procd_revision"
  # Exactly the init target's seven C sources in upstream CMakeLists.txt.
  procd_init_sources=(initd/init.c initd/early.c initd/preinit.c
    initd/mkdev.c sysupgrade.c watchdog.c utils/utils.c)
  mkdir "$tmp/procd-init-obj"
  for file in "${procd_init_sources[@]}"; do
    test -f "$procd_src/$file"
    obj="${file//\//_}"
    timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
      -Werror=implicit-function-declaration -I "$libubox_root" \
      -I "$libubox_root/libubox" -I "$procd_src" -I "$ubus_src" -c "$procd_src/$file" \
      -o "$tmp/procd-init-obj/${obj%.c}.o"
  done
  test "$(find "$tmp/procd-init-obj" -name '*.o' | wc -l)" -eq "${#procd_init_sources[@]}"
  timeout 120s "$compiler" -static "$tmp/procd-init-obj/"*.o \
    "$libubox_archive" -o "$tmp/procd-init"
  readelf -h "$tmp/procd-init" | grep -q 'Machine:.*AArch64'
  if readelf -l "$tmp/procd-init" | grep -q 'INTERP'; then
    echo 'Unexpected dynamic interpreter in procd init' >&2; exit 1
  fi
  test -s "$tmp/procd-init"
  if [[ -n "${SBAT6_MUSL_PROCD_INIT_OUTPUT:-}" ]]; then
    [[ "$SBAT6_MUSL_PROCD_INIT_OUTPUT" == /* &&
       ! -e "$SBAT6_MUSL_PROCD_INIT_OUTPUT" &&
       ! -L "$SBAT6_MUSL_PROCD_INIT_OUTPUT" ]] || {
      echo 'Unsafe procd init staging output' >&2; exit 2;
    }
    cp -- "$tmp/procd-init" "$SBAT6_MUSL_PROCD_INIT_OUTPUT"
    chmod 0600 "$SBAT6_MUSL_PROCD_INIT_OUTPUT"
  fi
  sha256sum "$tmp/procd-init"
  echo 'SBAT6_MUSL_PROCD_INIT_STATIC_PID1_LINK_PASS'
