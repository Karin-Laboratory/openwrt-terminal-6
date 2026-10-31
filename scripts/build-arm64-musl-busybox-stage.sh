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
# Opt-in combined rootfs *stage*: both binaries must be built with this
# exact native musl toolchain. It is deliberately not a bootable target.
if [[ "${SBAT6_BUILD_ROOTFS_SERVICES:-0}" == 1 ]]; then
  [[ $# -eq 0 && "${SBAT6_BUILD_LIBUBOX_CORE:-0}" == 1 &&
     "${SBAT6_BUILD_UBUS_CORE:-0}" == 1 &&
     "${SBAT6_BUILD_UBUSD:-0}" == 1 &&
     "${SBAT6_BUILD_UCI:-0}" == 1 &&
     "${SBAT6_BUILD_PROCD_INIT:-0}" == 1 &&
     "${SBAT6_BUILD_PROCD_SERVICE:-0}" == 1 &&
     "${SBAT6_BUILD_NETIFD_LINUX_OBJECT:-0}" == 1 ]] || {
    echo 'Combined stage requires pinned BusyBox, procd, ubus, UCI and netifd' >&2; exit 2;
  }
  mkdir "$tmp/service-inputs"
  export SBAT6_MUSL_BUSYBOX_OUTPUT="$tmp/service-inputs/busybox"
  export SBAT6_MUSL_UBUSD_OUTPUT="$tmp/service-inputs/ubusd"
  export SBAT6_MUSL_UBUS_CLI_OUTPUT="$tmp/service-inputs/ubus"
  export SBAT6_MUSL_UCI_CLI_OUTPUT="$tmp/service-inputs/uci"
  export SBAT6_MUSL_PROCD_INIT_OUTPUT="$tmp/service-inputs/init"
  export SBAT6_MUSL_PROCD_SERVICE_OUTPUT="$tmp/service-inputs/procd"
  export SBAT6_MUSL_NETIFD_OUTPUT="$tmp/service-inputs/netifd"
fi

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
if [[ "${SBAT6_BUILD_ROOTFS_SERVICES:-0}" == 1 ]]; then
  # Deterministic noninstallable rootfs stage with pinned procd/netifd and
  # a loopback-only first-boot policy. No external interface is configured.
  policy_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config/sbat6-stage"
  python3 - "$SBAT6_MUSL_BUSYBOX_OUTPUT" "$SBAT6_MUSL_UBUSD_OUTPUT" \
    "$SBAT6_MUSL_UBUS_CLI_OUTPUT" "$SBAT6_MUSL_UCI_CLI_OUTPUT" \
    "$SBAT6_MUSL_PROCD_INIT_OUTPUT" "$SBAT6_MUSL_PROCD_SERVICE_OUTPUT" \
    "$SBAT6_MUSL_NETIFD_OUTPUT" "$tmp/sbat6-services-rootfs.tar.gz" "$tmp/sbat6-services-manifest.json" "$policy_dir" <<'PY'
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tarfile

def read_static_aarch64(filename):
    path = Path(filename)
    if path.is_symlink() or not path.is_file():
        raise ValueError("binary must be a regular file")
    data = path.read_bytes()
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("expected little-endian ELF64")
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    if elf_type not in (2, 3) or machine != 183 or phentsize != 56 or not phnum:
        raise ValueError("expected AArch64 executable with program headers")
    if phoff < 64 or phoff + phentsize * phnum > len(data):
        raise ValueError("invalid ELF program headers")
    for index in range(phnum):
        if struct.unpack_from("<I", data, phoff + index * phentsize)[0] == 3:
            raise ValueError("PT_INTERP is not permitted in musl-static stage")
    return data

busybox, ubusd, ubus_cli, uci_cli, procd_init, procd_service, netifd = [read_static_aarch64(arg) for arg in sys.argv[1:8]]
archive_path, manifest_path = map(Path, sys.argv[8:10])
policy_root = Path(sys.argv[10])
policy_names = ("etc/preinit", "etc/inittab", "etc/rc.d/S10netifd", "etc/config/network", "etc/passwd", "etc/group")
policy_data = {}
for name in policy_names:
    path = policy_root / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("missing or unsafe SBAT6 boot policy: " + name)
    policy_data[name] = path.read_bytes()
if any(p.exists() or p.is_symlink() for p in (archive_path, manifest_path)):
    raise ValueError("output already exists")
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
    def add(name, kind, mode, data=b"", linkname=""):
        info = tarfile.TarInfo(name)
        info.type, info.mode = kind, mode
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ""
        info.linkname = linkname
        info.size = len(data) if kind == tarfile.REGTYPE else 0
        tar.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
    for directory in ("bin", "sbin", "etc", "etc/rc.d", "etc/config", "dev", "proc", "sys", "tmp", "var", "var/run"):
        add(directory, tarfile.DIRTYPE, 0o755)
    add("bin/busybox", tarfile.REGTYPE, 0o755, busybox)
    add("bin/ubus", tarfile.REGTYPE, 0o755, ubus_cli)
    add("sbin/uci", tarfile.REGTYPE, 0o755, uci_cli)
    add("sbin/init", tarfile.REGTYPE, 0o755, procd_init)
    add("sbin/procd", tarfile.REGTYPE, 0o755, procd_service)
    add("sbin/netifd", tarfile.REGTYPE, 0o755, netifd)
    for name, payload in policy_data.items():
        add(name, tarfile.REGTYPE, 0o755 if name in ("etc/preinit", "etc/rc.d/S10netifd") else 0o644, payload)
    add("bin/sh", tarfile.SYMTYPE, 0o777, linkname="busybox")
    add("sbin/ubusd", tarfile.REGTYPE, 0o755, ubusd)
compressed = gzip.compress(buffer.getvalue(), compresslevel=9, mtime=0)
with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode="r:") as tar:
    expected = {"bin", "sbin", "etc", "etc/rc.d", "etc/config", "dev", "proc", "sys", "tmp",
                "var", "var/run", "bin/busybox", "bin/ubus", "bin/sh", "sbin/ubusd", "sbin/uci", "sbin/init", "sbin/procd", "sbin/netifd"} | set(policy_names)
    if set(tar.getnames()) != expected:
        raise ValueError("unexpected rootfs stage member")
    if tar.getmember("bin/sh").linkname != "busybox":
        raise ValueError("unexpected shell link")
    for name, original in (("bin/busybox", busybox), ("bin/ubus", ubus_cli),
                           ("sbin/ubusd", ubusd), ("sbin/uci", uci_cli),
                           ("sbin/init", procd_init), ("sbin/procd", procd_service),
                           ("sbin/netifd", netifd)):
        if tar.extractfile(name).read() != original:
            raise ValueError("rootfs archive byte mismatch")
    for name, original in policy_data.items():
        if tar.extractfile(name).read() != original:
            raise ValueError("rootfs boot policy byte mismatch")
manifest = {
    "scope": "NONINSTALLABLE_SBAT6_MUSL_BUSYBOX_UBUSD_UBUS_UCI_PROCD_NETIFD_ROOTFS_STAGE",
    "architecture": "aarch64",
    "libc": "native-musl-static-1.2.5",
    "busybox_version": "1.36.1",
    "ubus_commit": "db20eff5535fe3126c05dc0edc029caf0e82fe10",
    "libubox_commit": "da2d205a5cf3e877c45a2eec488218cbaf452e7d",
    "json_c_commit": "41a55cfcedb54d9c1874f2f0eb07b504091d7e37",
    "uci_commit": "66127cd76c5d0bd46d5a90302cc6110f53a4e2f8",
    "procd_commit": "5aef7c33b01455157c1373a14e2a3fa47d024c6c",
    "netifd_commit": "a1e39a458f9601100ee6bf91b0d6800688cf6a5b",
    "ucode_commit": "dfc64d41fd720163ac21d9feb9cb224d1a80fd75",
    "libnl_tiny_commit": "40493a655d8caa2ccf5206dde1e733abe2920432",
    "udebug_commit": "6726e98ad69402e79b6d0b305012ace857ca0786",
    "files_sha256": {
        "bin/busybox": hashlib.sha256(busybox).hexdigest(),
        "bin/ubus": hashlib.sha256(ubus_cli).hexdigest(),
        "sbin/ubusd": hashlib.sha256(ubusd).hexdigest(),
        "sbin/uci": hashlib.sha256(uci_cli).hexdigest(),
        "sbin/init": hashlib.sha256(procd_init).hexdigest(),
        "sbin/procd": hashlib.sha256(procd_service).hexdigest(),
        "sbin/netifd": hashlib.sha256(netifd).hexdigest(),
        **{name: hashlib.sha256(data).hexdigest() for name, data in policy_data.items()}
    },
    "archive_sha256": hashlib.sha256(compressed).hexdigest(),
    "archive_bytes": len(compressed),
    "rights_review": "pending",
    "not_proven": ["PID1/procd service runtime", "netifd runtime/bridge", "SSH", "wpad",
                   "SBAT6 OpenWrt target", "hardware AP", "distribution rights"]
}
archive_path.write_bytes(compressed)
manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
print("SBAT6_MUSL_PROCD_SERVICE_ROOTFS_STAGE_PASS",
      "bytes=", len(compressed), "sha256=", manifest["archive_sha256"])
PY
  test -s "$tmp/sbat6-services-rootfs.tar.gz"
  test -s "$tmp/sbat6-services-manifest.json"
  sha256sum "$tmp/sbat6-services-rootfs.tar.gz"
  # Opt-in handoff to the SAME hosted Image job. The destination must be
  # new, absolute and temporary; never upload or install the rootfs stage.
  if [[ -n "${SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT:-}" ||
        -n "${SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT:-}" ]]; then
    [[ -n "${SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT:-}" &&
       -n "${SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT:-}" &&
       "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT" == /* &&
       "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT" == /* &&
       "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT" != "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT" &&
       ! -e "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT" &&
       ! -L "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT" &&
       ! -e "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT" &&
       ! -L "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT" ]] || {
      echo 'Unsafe rootfs stage handoff' >&2; exit 2;
    }
    cp -- "$tmp/sbat6-services-rootfs.tar.gz" "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT"
    cp -- "$tmp/sbat6-services-manifest.json" "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT"
    chmod 0600 "$SBAT6_MUSL_SERVICES_ROOTFS_OUTPUT" "$SBAT6_MUSL_SERVICES_MANIFEST_OUTPUT"
  fi
fi
echo 'LIMIT: procd preinit/inittab/netifd service policy staged, but no runtime execution, external network/AP, SSH or release.'
