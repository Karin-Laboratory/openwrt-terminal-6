#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile the real upstream procd init target against pinned native ARM64 musl.
# Noninstallable stage only; never execute, sign, flash or deploy the binary.
set -euo pipefail
umask 077
if (( EUID == 0 )); then
  echo 'Refusing procd init build as root' >&2; exit 2
fi
[[ "$(uname -m)" == aarch64 && ( $# -eq 3 || $# -eq 9 ) && "$1" == /* &&
   "$2" == /* && "$3" == /* && -x "$1" && -s "$2" &&
   -f "$3/libubus.h" ]] || {
  echo 'usage: build-arm64-musl-procd-init.sh /absolute/musl-gcc /absolute/libubox.a /absolute/ubus-source [libubus.a libuci.a libblobmsg_json.a libjson-c.a json-c-source json-c-build]' >&2
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

# Opt-in real upstream /sbin/procd service-manager executable. Unlike the
# separate initd PID1, this is the service lifecycle, hotplug and ubus process.
# The full upstream CMake SOURCES list is compiled, not a stub or empty main.
# All inputs are pinned public sources, compiled with the same native musl ABI.
if (( $# == 9 )); then
  for input in "${@:4:4}"; do
    [[ "$input" == /* && -s "$input" ]] || {
      echo 'Missing static procd dependency archive' >&2; exit 2;
    }
  done
  [[ -f "$8/json_tokener.h" && -f "$9/json_config.h" ]] || {
    echo 'Missing pinned json-c headers' >&2; exit 2;
  }
  libubus_archive="$4"
  libuci_archive="$5"
  blobmsg_json_archive="$6"
  json_archive="$7"
  json_src="$8"
  json_build="$9"
  libubox_src="$libubox_root/libubox"
  test -f "$libubox_src/json_script.c"
  test -f "$libubox_src/udebug.c"
  timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$libubox_root" \
    -c "$libubox_src/json_script.c" -o "$tmp/json_script.o"
  timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$libubox_root" \
    -c "$libubox_src/udebug.c" -o "$tmp/udebug.o"
  # The procd <udebug.h> is the OpenWrt udebug ubus integration API,
  # NOT the lower-level libubox/udebug.h. Build the actual pinned library.
  udebug_src="$tmp/udebug-source"
  git init --quiet "$udebug_src"
  git -C "$udebug_src" remote add origin https://github.com/openwrt/udebug.git
  udebug_revision=6726e98ad69402e79b6d0b305012ace857ca0786
  timeout 180s git -C "$udebug_src" -c protocol.version=2 fetch --quiet --depth 1 origin "$udebug_revision"
  test "$(git -C "$udebug_src" rev-parse FETCH_HEAD)" = "$udebug_revision"
  git -C "$udebug_src" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$udebug_src" rev-parse HEAD)" = "$udebug_revision"
  timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$udebug_src" \
    -I "$libubox_root" -I "$ubus_src" \
    -c "$udebug_src/lib.c" -o "$tmp/udebug-ubus.o"
  procd_sources=(procd.c signal.c state.c hotplug-dispatch.c inittab.c
    rcS.c ubus.c system.c sysupgrade.c service/service.c
    service/instance.c service/validate.c service/trigger.c
    service/watch.c service/vrf.c utils/utils.c utils/cgroup.c
    watchdog.c plug/coldplug.c plug/hotplug.c)
  mkdir "$tmp/procd-obj"
  for file in "${procd_sources[@]}"; do
    test -f "$procd_src/$file"
    obj="${file//\//_}"
    timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE -DHAS_UDEBUG \
      -Werror=implicit-function-declaration -I "$libubox_root" \
      -I "$udebug_src" -I "$libubox_src" -I "$ubus_src" -I "$procd_src" \
      -I "$json_src" -I "$json_build" \
      -c "$procd_src/$file" -o "$tmp/procd-obj/${obj%.c}.o"
  done
  test "$(find "$tmp/procd-obj" -name '*.o' | wc -l)" -eq "${#procd_sources[@]}"
  timeout 120s "$compiler" -static "$tmp/procd-obj/"*.o \
    -Wl,--start-group "$tmp/json_script.o" "$tmp/udebug.o" "$tmp/udebug-ubus.o" \
    "$libubus_archive" "$libuci_archive" "$blobmsg_json_archive" \
    "$libubox_archive" "$json_archive" -Wl,--end-group -lm \
    -o "$tmp/procd-service"
  readelf -h "$tmp/procd-service" | grep -q 'Machine:.*AArch64'
  if readelf -l "$tmp/procd-service" | grep -q 'INTERP'; then
    echo 'Unexpected dynamic interpreter in procd service' >&2; exit 1
  fi
  test -s "$tmp/procd-service"
  if [[ -n "${SBAT6_MUSL_PROCD_SERVICE_OUTPUT:-}" ]]; then
    [[ "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT" == /* &&
       ! -e "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT" &&
       ! -L "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT" ]] || {
      echo 'Unsafe procd service staging output' >&2; exit 2;
    }
    cp -- "$tmp/procd-service" "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT"
    chmod 0600 "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT"
  fi
  sha256sum "$tmp/procd-service"
  echo 'SBAT6_MUSL_PROCD_SERVICE_STATIC_LINK_PASS'
fi
