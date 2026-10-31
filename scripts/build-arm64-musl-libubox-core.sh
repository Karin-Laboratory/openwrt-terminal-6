#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile pinned OpenWrt libubox core against the native AArch64 musl toolchain.
# Ephemeral build-only dependency step for #21; no package, install or execution.
set -euo pipefail
umask 077
if (( EUID == 0 )); then
  echo 'Refusing libubox build as root' >&2
  exit 2
fi
[[ "$(uname -m)" == aarch64 && $# -eq 1 && "$1" == /* && -x "$1" ]] || {
  echo 'usage: build-arm64-musl-libubox-core.sh /absolute/path/to/musl-gcc (native AArch64)' >&2
  exit 2
}
for tool in git timeout mktemp ar nm readelf sha256sum; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool" >&2; exit 2; }
done
compiler="$1"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-libubox.XXXXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT
src="$tmp/libubox"
git init --quiet "$src"
git -C "$src" remote add origin https://github.com/openwrt/libubox.git
# Fetch only a fixed, public OpenWrt source commit. No floating branch or donor blobs.
revision=da2d205a5cf3e877c45a2eec488218cbaf452e7d
timeout 180s git -C "$src" -c protocol.version=2 fetch --quiet --depth 1 origin "$revision"
test "$(git -C "$src" rev-parse FETCH_HEAD)" = "$revision"
git -C "$src" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$src" rev-parse HEAD)" = "$revision"

# Do not put the source root on the angle-include path: its custom assert.h
# includes the system assert.h, and -I src would cause self-shadowing.
# Same core source list as upstream libubox CMakeLists.txt, without optional
# JSON-C/Lua frontends. Build all 18 objects, not a placeholder or host libc.
sources=(avl.c avl-cmp.c blob.c blobmsg.c uloop.c usock.c ustream.c
  ustream-fd.c vlist.c utils.c safe_list.c runqueue.c md5.c kvlist.c
  ulog.c base64.c udebug.c udebug-remote.c)
mkdir "$tmp/obj"
for file in "${sources[@]}"; do
  test -f "$src/$file"
  timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$tmp" \
    -c "$src/$file" -o "$tmp/obj/${file%.c}.o"
done
ar rcs "$tmp/libubox.a" "$tmp/obj/"*.o
test "$(ar t "$tmp/libubox.a" | wc -l)" -eq "${#sources[@]}"
nm --defined-only "$tmp/libubox.a" > "$tmp/symbols.txt"
grep -Eq ' [TW] uloop_init$' "$tmp/symbols.txt"
grep -Eq ' [TW] blobmsg_add_string_buffer$' "$tmp/symbols.txt"

# Link an actual musl-static AArch64 ELF against the newly compiled archive.
# Never execute it. This proves libc and the event-loop link closure only.
cat > "$tmp/link-smoke.c" <<'EOF'
#include <libubox/uloop.h>
int main(void) {
    if (uloop_init() != 0) return 1;
    uloop_done();
    return 0;
}
EOF
timeout 90s "$compiler" -static -I "$tmp" \
  "$tmp/link-smoke.c" "$tmp/libubox.a" -o "$tmp/link-smoke"
readelf -h "$tmp/link-smoke" | grep -q 'Machine:.*AArch64'
if readelf -l "$tmp/link-smoke" | grep -q 'INTERP'; then
  echo 'Unexpected dynamic interpreter in musl-static smoke' >&2
  exit 1
fi
sha256sum "$tmp/libubox.a" "$tmp/link-smoke"
echo 'SBAT6_MUSL_LIBUBOX_CORE_OBJECTS_AND_STATIC_LINK_PASS'

# Opt-in actual OpenWrt ubus client library build against the same musl ABI.
# No system ubus, JSON-C, host libc, installed service or execution.
if [[ "${SBAT6_BUILD_UBUS_CORE:-0}" == 1 ]]; then
  ubus_src="$tmp/ubus"
  git init --quiet "$ubus_src"
  git -C "$ubus_src" remote add origin https://github.com/openwrt/ubus.git
  ubus_revision=db20eff5535fe3126c05dc0edc029caf0e82fe10
  timeout 180s git -C "$ubus_src" -c protocol.version=2 fetch --quiet --depth 1 origin "$ubus_revision"
  test "$(git -C "$ubus_src" rev-parse FETCH_HEAD)" = "$ubus_revision"
  git -C "$ubus_src" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$ubus_src" rev-parse HEAD)" = "$ubus_revision"
  ubus_sources=(libubus.c libubus-io.c libubus-obj.c
    libubus-sub.c libubus-req.c libubus-acl.c)
  mkdir "$tmp/ubus-obj"
  for file in "${ubus_sources[@]}"; do
    test -f "$ubus_src/$file"
    timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
      -DUBUS_UNIX_SOCKET='"/var/run/ubus/ubus.sock"' \
      -DUBUS_MAX_MSGLEN=1048576 -Werror=implicit-function-declaration \
      -I "$tmp" -I "$ubus_src" \
      -c "$ubus_src/$file" -o "$tmp/ubus-obj/${file%.c}.o"
  done
  ar rcs "$tmp/libubus.a" "$tmp/ubus-obj/"*.o
  test "$(ar t "$tmp/libubus.a" | wc -l)" -eq "${#ubus_sources[@]}"
  nm --defined-only "$tmp/libubus.a" > "$tmp/ubus-symbols.txt"
  grep -Eq ' [TW] ubus_connect$' "$tmp/ubus-symbols.txt"
  grep -Eq ' [TW] ubus_free$' "$tmp/ubus-symbols.txt"
  cat > "$tmp/ubus-link-smoke.c" <<'EOF'
#include "libubus.h"
int main(void) {
    struct ubus_context *ctx = ubus_connect(NULL);
    if (ctx) ubus_free(ctx);
    return 0;
}
EOF
  # Static AArch64 link only; never run or install the executable.
  timeout 90s "$compiler" -static -I "$tmp" -I "$ubus_src" \
    "$tmp/ubus-link-smoke.c" "$tmp/libubus.a" "$tmp/libubox.a" \
    -o "$tmp/ubus-link-smoke"
  readelf -h "$tmp/ubus-link-smoke" | grep -q 'Machine:.*AArch64'
  if readelf -l "$tmp/ubus-link-smoke" | grep -q 'INTERP'; then
    echo 'Unexpected dynamic interpreter in musl-static ubus smoke' >&2
    exit 1
  fi
  sha256sum "$tmp/libubus.a" "$tmp/ubus-link-smoke"
  echo 'SBAT6_MUSL_LIBUBUS_CORE_OBJECTS_AND_STATIC_LINK_PASS'
fi
# Optional actual ubusd daemon link. JSON-C is built from its own exact
# public commit with the SAME native musl compiler. No host json-c fallback.
# All objects remain in a temporary noninstallable directory and are never run.
if [[ "${SBAT6_BUILD_UBUSD:-0}" == 1 ]]; then
  [[ "${SBAT6_BUILD_UBUS_CORE:-0}" == 1 ]] || {
    echo 'ubusd requires the pinned ubus source build' >&2
    exit 2
  }
  command -v cmake >/dev/null || { echo 'Missing build tool: cmake' >&2; exit 2; }
  json_src="$tmp/json-c"
  json_build="$tmp/json-c-build"
  git init --quiet "$json_src"
  git -C "$json_src" remote add origin https://github.com/json-c/json-c.git
  json_revision=41a55cfcedb54d9c1874f2f0eb07b504091d7e37 # json-c 0.18
  timeout 180s git -C "$json_src" -c protocol.version=2 fetch --quiet --depth 1 origin "$json_revision"
  test "$(git -C "$json_src" rev-parse FETCH_HEAD)" = "$json_revision"
  git -C "$json_src" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$json_src" rev-parse HEAD)" = "$json_revision"
  timeout 180s cmake -S "$json_src" -B "$json_build" \
    -DCMAKE_C_COMPILER="$compiler" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON \
    -DBUILD_TESTING=OFF -DBUILD_APPS=OFF \
    -DDISABLE_EXTRA_LIBS=ON -DDISABLE_WERROR=ON
  timeout 300s cmake --build "$json_build" --target json-c --parallel 2
  test -s "$json_build/libjson-c.a"
  "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration \
    -I "$tmp" -I "$json_src" -I "$json_build" \
    -c "$src/blobmsg_json.c" -o "$tmp/blobmsg_json.o"
  ar rcs "$tmp/libblobmsg_json.a" "$tmp/blobmsg_json.o"
  nm --defined-only "$tmp/libblobmsg_json.a" | grep -Eq ' [TW] blobmsg_add_json_from_file$'
  ubusd_sources=(ubusd.c ubusd_proto.c ubusd_id.c ubusd_obj.c \
    ubusd_event.c ubusd_acl.c ubusd_monitor.c)
  mkdir "$tmp/ubusd-obj"
  for file in "${ubusd_sources[@]}"; do
    test -f "$ubus_src/$file"
    timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
      -DUBUS_UNIX_SOCKET='"/var/run/ubus/ubus.sock"' \
      -DUBUS_MAX_MSGLEN=1048576 -Werror=implicit-function-declaration \
      -I "$tmp" -I "$ubus_src" -I "$json_src" -I "$json_build" \
      -c "$ubus_src/$file" -o "$tmp/ubusd-obj/${file%.c}.o"
  done
  ar rcs "$tmp/libubusd.a" "$tmp/ubusd-obj/"*.o
  test "$(ar t "$tmp/libubusd.a" | wc -l)" -eq "${#ubusd_sources[@]}"
  nm --defined-only "$tmp/libubusd.a" | grep -Eq ' [TW] ubusd_acl_load$'
  # Link a real ubusd daemon ELF, not a stub. Never execute or install it.
  timeout 120s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE -static \
    -DUBUS_UNIX_SOCKET='"/var/run/ubus/ubus.sock"' \
    -DUBUS_MAX_MSGLEN=1048576 \
    -I "$tmp" -I "$ubus_src" -I "$json_src" -I "$json_build" \
    "$ubus_src/ubusd_main.c" "$tmp/libubusd.a" \
    "$tmp/libblobmsg_json.a" "$tmp/libubox.a" \
    "$json_build/libjson-c.a" -lm -o "$tmp/ubusd"
  readelf -h "$tmp/ubusd" | grep -q 'Machine:.*AArch64'
  if readelf -l "$tmp/ubusd" | grep -q 'INTERP'; then
    echo 'Unexpected dynamic interpreter in musl-static ubusd' >&2
    exit 1
  fi
  test -s "$tmp/ubusd"
  # Export only to the caller's ephemeral stage, never to an upload/release.
  if [[ -n "${SBAT6_MUSL_UBUSD_OUTPUT:-}" ]]; then
    [[ "$SBAT6_MUSL_UBUSD_OUTPUT" == /* &&
       ! -e "$SBAT6_MUSL_UBUSD_OUTPUT" &&
       ! -L "$SBAT6_MUSL_UBUSD_OUTPUT" ]] || {
      echo 'Unsafe ubusd staging output' >&2; exit 2;
    }
    cp -- "$tmp/ubusd" "$SBAT6_MUSL_UBUSD_OUTPUT"
    chmod 0600 "$SBAT6_MUSL_UBUSD_OUTPUT"
  fi
  sha256sum "$json_build/libjson-c.a" "$tmp/libblobmsg_json.a" "$tmp/libubusd.a" "$tmp/ubusd"
  wc -c "$tmp/ubusd"
  echo 'SBAT6_MUSL_UBUSD_STATIC_DAEMON_LINK_PASS'
fi
echo 'LIMIT: native musl ubusd link only; no execution, procd, netifd, OpenWrt target/rootfs, device or release.'
