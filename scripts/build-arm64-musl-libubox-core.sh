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

# Same core source list as upstream libubox CMakeLists.txt, without optional
# JSON-C/Lua frontends. Build all 18 objects, not a placeholder or host libc.
sources=(avl.c avl-cmp.c blob.c blobmsg.c uloop.c usock.c ustream.c
  ustream-fd.c vlist.c utils.c safe_list.c runqueue.c md5.c kvlist.c
  ulog.c base64.c udebug.c udebug-remote.c)
mkdir "$tmp/obj"
for file in "${sources[@]}"; do
  test -f "$src/$file"
  timeout 90s "$compiler" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$tmp" -I "$src" \
    -c "$src/$file" -o "$tmp/obj/${file%.c}.o"
done
ar rcs "$tmp/libubox.a" "$tmp/obj/"*.o
test "$(ar t "$tmp/libubox.a" | wc -l)" -eq "${#sources[@]}"
nm --defined-only "$tmp/libubox.a" | grep -Eq ' [TW] uloop_init$'
nm --defined-only "$tmp/libubox.a" | grep -Eq ' [TW] blobmsg_add_string$'

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
timeout 90s "$compiler" -static -I "$tmp" -I "$src" \
  "$tmp/link-smoke.c" "$tmp/libubox.a" -o "$tmp/link-smoke"
readelf -h "$tmp/link-smoke" | grep -q 'Machine:.*AArch64'
if readelf -l "$tmp/link-smoke" | grep -q 'INTERP'; then
  echo 'Unexpected dynamic interpreter in musl-static smoke' >&2
  exit 1
fi
sha256sum "$tmp/libubox.a" "$tmp/link-smoke"
echo 'SBAT6_MUSL_LIBUBOX_CORE_OBJECTS_AND_STATIC_LINK_PASS'
echo 'LIMIT: libubox core only; no JSON-C, ubus, procd, netifd, OpenWrt target/rootfs, device or release.'
