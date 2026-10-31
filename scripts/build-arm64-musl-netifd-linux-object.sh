#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compile the actual netifd Linux/netlink backend against pinned OpenWrt
# libnl-tiny, libubox, libubus and UCI with the SAME native ARM64 musl ABI.
# Build-only object milestone: no daemon executable, execution or deployment.
set -euo pipefail
umask 077
if (( EUID == 0 )); then echo 'Refusing root build' >&2; exit 2; fi
[[ "$(uname -m)" == aarch64 && $# -eq 2 && "$1" == /* &&
   "$2" == /* && -x "$1" && -d "$2/libubox" &&
   -f "$2/ubus/libubus.h" && -f "$2/uci/uci.h" &&
   -s "$2/libubox.a" ]] || {
  echo 'usage: build-arm64-musl-netifd-linux-object.sh /absolute/musl-gcc /absolute/verified-dependency-build-root' >&2
  exit 2
}
for tool in git timeout ar nm readelf sha256sum; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
cc="$1"
deps="$2"
# The parent ephemeral build root owns cleanup and source provenance.
nl="$deps/libnl-tiny"
git init --quiet "$nl"
git -C "$nl" remote add origin https://github.com/openwrt/libnl-tiny.git
nl_rev=40493a655d8caa2ccf5206dde1e733abe2920432
timeout 180s git -C "$nl" -c protocol.version=2 fetch --quiet --depth 1 origin "$nl_rev"
test "$(git -C "$nl" rev-parse FETCH_HEAD)" = "$nl_rev"
git -C "$nl" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$nl" rev-parse HEAD)" = "$nl_rev"
# All 14 sources from upstream CMakeLists.txt; not a fake API stub.
nl_sources=(attr.c cache.c cache_mngt.c error.c genl.c genl_ctrl.c
  genl_family.c genl_mngt.c handlers.c msg.c nl.c object.c socket.c unl.c)
mkdir "$deps/nl-obj"
for file in "${nl_sources[@]}"; do
  test -f "$nl/$file"
  timeout 90s "$cc" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration -I "$nl/include" \
    -c "$nl/$file" -o "$deps/nl-obj/${file%.c}.o"
done
ar rcs "$deps/libnl-tiny.a" "$deps/nl-obj/"*.o
test "$(ar t "$deps/libnl-tiny.a" | wc -l)" -eq "${#nl_sources[@]}"
nm --defined-only "$deps/libnl-tiny.a" | grep -Eq ' [TW] nl_socket_alloc$'
cat > "$deps/nl-link-smoke.c" <<'EOF'
#include <netlink/socket.h>
int main(void) {
  struct nl_sock *sock = nl_socket_alloc();
  if (sock) nl_socket_free(sock);
  return 0;
}
EOF
timeout 90s "$cc" -static -I "$nl/include" \
  "$deps/nl-link-smoke.c" "$deps/libnl-tiny.a" -o "$deps/nl-link-smoke"
readelf -h "$deps/nl-link-smoke" | grep -q 'Machine:.*AArch64'
if readelf -l "$deps/nl-link-smoke" | grep -q INTERP; then
  echo 'Unexpected dynamic interpreter in libnl-tiny link' >&2; exit 1
fi
echo 'SBAT6_MUSL_LIBNL_TINY_REAL_OBJECTS_STATIC_LINK_PASS'

# Compile netifd's actual Linux backend, not a placeholder or DUMMY_MODE.
# This is the first netifd C object; the full daemon still requires ucode,
# libudebug and the remaining netifd sources before it can be linked.
netifd="$deps/netifd"
git init --quiet "$netifd"
git -C "$netifd" remote add origin https://github.com/openwrt/netifd.git
netifd_rev=a1e39a458f9601100ee6bf91b0d6800688cf6a5b
timeout 180s git -C "$netifd" -c protocol.version=2 fetch --quiet --depth 1 origin "$netifd_rev"
test "$(git -C "$netifd" rev-parse FETCH_HEAD)" = "$netifd_rev"
git -C "$netifd" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$netifd" rev-parse HEAD)" = "$netifd_rev"
# Upstream generates this header from the active compiler's Linux UAPI.
sh "$netifd/make_ethtool_modes_h.sh" "$cc" > "$deps/ethtool-modes.h"
test -s "$deps/ethtool-modes.h"
timeout 180s "$cc" -Os -std=gnu99 -D_GNU_SOURCE \
  -Werror=implicit-function-declaration \
  -I "$deps" -I "$deps/libubox" -I "$deps/ubus" -I "$deps/uci" \
  -I "$nl/include" -I "$netifd" \
  -c "$netifd/system-linux.c" -o "$deps/netifd-system-linux.o"
test -s "$deps/netifd-system-linux.o"
nm --defined-only "$deps/netifd-system-linux.o" | grep -Eq ' [TW] system_init$'
sha256sum "$deps/libnl-tiny.a" "$deps/netifd-system-linux.o"
echo 'SBAT6_MUSL_NETIFD_REAL_LINUX_BACKEND_OBJECT_PASS'
echo 'LIMIT: no full netifd executable, ucode closure, service execution, AP, hardware or rights approval.'
