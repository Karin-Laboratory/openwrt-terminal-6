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
#include <linux/types.h>
#include <netlink/socket.h>
int main(void) {
  struct nl_sock *sock = nl_socket_alloc();
  if (sock) nl_socket_free(sock);
  return 0;
}
EOF
timeout 90s "$cc" -static -D_GNU_SOURCE -I "$nl/include" \
  "$deps/nl-link-smoke.c" "$deps/libnl-tiny.a" -o "$deps/nl-link-smoke"
readelf -h "$deps/nl-link-smoke" | grep -q 'Machine:.*AArch64'
if readelf -l "$deps/nl-link-smoke" | grep -q INTERP; then
  echo 'Unexpected dynamic interpreter in libnl-tiny link' >&2; exit 1
fi
echo 'SBAT6_MUSL_LIBNL_TINY_REAL_OBJECTS_STATIC_LINK_PASS'

# netifd uses the separate libudebug API, not libubox's ring-buffer
# udebug.h. Build both upstream libudebug C objects and prefer its header.
ud="$deps/udebug"
git init --quiet "$ud"
git -C "$ud" remote add origin https://github.com/openwrt/udebug.git
ud_rev=6726e98ad69402e79b6d0b305012ace857ca0786
timeout 180s git -C "$ud" -c protocol.version=2 fetch --quiet --depth 1 origin "$ud_rev"
test "$(git -C "$ud" rev-parse FETCH_HEAD)" = "$ud_rev"
git -C "$ud" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$ud" rev-parse HEAD)" = "$ud_rev"
mkdir "$deps/ud-obj"
for file in lib.c lib-pcap.c; do
  test -f "$ud/$file"
  timeout 90s "$cc" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration \
    -I "$deps" -I "$deps/ubus" -I "$ud" \
    -c "$ud/$file" -o "$deps/ud-obj/${file%.c}.o"
done
ar rcs "$deps/libudebug.a" "$deps/ud-obj/"*.o
test "$(ar t "$deps/libudebug.a" | wc -l)" -eq 2
nm --defined-only "$deps/libudebug.a" | grep -Eq ' [TW] udebug_netlink_msg$'
echo 'SBAT6_MUSL_LIBUDEBUG_REAL_OBJECTS_PASS'

# Compile netifd's actual Linux backend, not a placeholder or DUMMY_MODE.
# This is the first netifd C object; the full daemon still requires ucode
# and the remaining netifd sources before it can be linked.
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
  -I "$ud" -I "$deps" -I "$deps/libubox" -I "$deps/ubus" -I "$deps/uci" \
  -I "$nl/include" -I "$netifd" \
  -c "$netifd/system-linux.c" -o "$deps/netifd-system-linux.o"
test -s "$deps/netifd-system-linux.o"
nm --defined-only "$deps/netifd-system-linux.o" | grep -Eq ' [TW] system_init$'
# Compile real upstream netifd bridge/VLAN and static protocol objects with
# the exact same native AArch64 musl ABI as system-linux.c. These are part of
# the upstream netifd CMake SOURCES, not an emulated or DUMMY_MODE backend.
# This does not link the daemon or authorize execution/installation.
core_sources=(bridge.c vlan.c vlandev.c proto-static.c)
mkdir "$deps/netifd-core-obj"
for file in "${core_sources[@]}"; do
  test -f "$netifd/$file"
  # libubox/assert.h shadows the C standard header under -I; keep
  # system headers ahead of the libubox fallback include directory.
  timeout 180s "$cc" -Os -std=gnu99 -D_GNU_SOURCE \
    -Werror=implicit-function-declaration \
    -I "$ud" -I "$deps" -idirafter "$deps/libubox" -I "$deps/ubus" -I "$deps/uci" \
    -I "$nl/include" -I "$netifd" \
    -c "$netifd/$file" -o "$deps/netifd-core-obj/${file%.c}.o"
done
test "$(find "$deps/netifd-core-obj" -maxdepth 1 -name '*.o' | wc -l)" -eq "${#core_sources[@]}"
for file in "${core_sources[@]}"; do
  test -s "$deps/netifd-core-obj/${file%.c}.o"
done
nm --defined-only "$deps/netifd-core-obj/bridge.o" | grep -Fq ' bridge_config_init'
nm --defined-only "$deps/netifd-core-obj/vlan.o" | grep -Fq ' vlan_config_init'
nm --defined-only "$deps/netifd-core-obj/vlandev.o" | grep -Fq ' vlandev_config_init'
echo 'SBAT6_MUSL_NETIFD_BRIDGE_VLAN_STATIC_PROTO_OBJECTS_PASS'
sha256sum "$deps/libnl-tiny.a" "$deps/libudebug.a" "$deps/netifd-system-linux.o" "$deps/netifd-core-obj/"*.o
echo 'SBAT6_MUSL_NETIFD_REAL_LINUX_BACKEND_OBJECT_PASS'
echo 'LIMIT: no full netifd executable, ucode closure, service execution, AP, hardware or rights approval.'
