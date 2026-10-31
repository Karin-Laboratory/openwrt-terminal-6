#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Construct a deterministic, non-installable AArch64 BusyBox PID1 initramfs.

Compile-only diagnostic ingredient. Never boot, install, upload, or release it.
The /init shell script deliberately exposes no shell/login/network service.
"""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "busybox_rootfs_elf", ROOT / "scripts/package-arm64-busybox-rootfs.py"
)
elf_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elf_check)

INIT = (b"#!/bin/sh\n"
        b"echo 'SBAT6 build-only BusyBox PID1 diagnostic; NOT OpenWrt AP' >/dev/console\n"
        b"while :; do /bin/busybox sleep 60; done\n")


def entry(name: str, mode: int, data: bytes, ino: int,
          rdevmajor: int = 0, rdevminor: int = 0) -> bytes:
    if not name or name.startswith("/") or ".." in name.split("/") or "\x00" in name:
        raise ValueError("unsafe cpio name")
    namebytes = name.encode("ascii") + b"\0"
    fields = (ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0,
              len(data), 0, 0, rdevmajor, rdevminor, len(namebytes), 0)
    record = b"070701" + b"".join(f"{value:08x}".encode("ascii") for value in fields)
    record += namebytes
    record += b"\0" * (-len(record) % 4)
    record += data
    return record + b"\0" * (-len(record) % 4)


def unpack(raw: bytes) -> dict:
    """Parse the entire newc stream, checking record boundaries and trailer."""
    offset, result = 0, {}
    while offset < len(raw):
        if raw[offset:offset + 6] != b"070701" or offset + 110 > len(raw):
            raise ValueError("invalid newc header")
        fields = [int(raw[offset + 6 + i * 8:offset + 14 + i * 8], 16)
                  for i in range(13)]
        size, namesize = fields[6], fields[11]
        offset += 110
        if namesize < 2 or offset + namesize > len(raw):
            raise ValueError("invalid newc name length")
        namebytes = raw[offset:offset + namesize]
        if not namebytes.endswith(b"\0"):
            raise ValueError("unterminated newc name")
        name = namebytes[:-1].decode("ascii")
        offset = (offset + namesize + 3) & ~3
        if offset + size > len(raw) or name in result:
            raise ValueError("truncated or duplicate newc member")
        data = raw[offset:offset + size]
        offset = (offset + size + 3) & ~3
        result[name] = (fields[1], data, fields[9], fields[10])
        if name == "TRAILER!!!":
            if offset != len(raw):
                raise ValueError("trailing bytes after newc trailer")
            return result
    raise ValueError("missing newc trailer")


def package(binary: Path, archive: Path, manifest: Path) -> dict:
    if binary.is_symlink() or not binary.is_file():
        raise ValueError("BusyBox input must be a regular file")
    if archive == manifest or archive.exists() or archive.is_symlink() or \
            manifest.exists() or manifest.is_symlink():
        raise ValueError("outputs must be distinct and must not exist")
    payload = binary.read_bytes()
    elf_check.check_static_aarch64_elf(payload)
    records = [
        ("bin", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("dev", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3),
        ("proc", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("sys", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("bin/busybox", stat.S_IFREG | 0o755, payload, 0, 0),
        ("bin/sh", stat.S_IFLNK | 0o777, b"busybox", 0, 0),
        ("init", stat.S_IFREG | 0o755, INIT, 0, 0),
    ]
    raw = b"".join(entry(name, mode, data, i, major, minor)
                   for i, (name, mode, data, major, minor) in enumerate(records, 1))
    raw += entry("TRAILER!!!", 0, b"", len(records) + 1)
    check = unpack(raw)
    if set(check) != {x[0] for x in records} | {"TRAILER!!!"}:
        raise ValueError("unexpected newc entries")
    if check["bin/busybox"][1] != payload or check["bin/sh"][1] != b"busybox" or \
            check["init"][1] != INIT or check["dev/console"][2:] != (5, 1):
        raise ValueError("newc payload round-trip failed")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    if unpack(gzip.decompress(compressed)) != check:
        raise ValueError("gzip round-trip failed")
    record = {
        "scope": "NONINSTALLABLE_STATIC_BUSYBOX_PID1_INITRAMFS",
        "architecture": "aarch64",
        "libc": "host-glibc-static-not-openwrt-musl",
        "busybox_version": "1.36.1",
        "busybox_commit": "1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4",
        "busybox_sha256": hashlib.sha256(payload).hexdigest(),
        "init_sha256": hashlib.sha256(INIT).hexdigest(),
        "initramfs_sha256": hashlib.sha256(compressed).hexdigest(),
        "initramfs_bytes": len(compressed),
        "rights_review": "pending",
        "not_proven": ["OpenWrt musl/rootfs/procd/netifd", "SBAT6 kernel ABI",
                       "hardware boot", "Ethernet/Wi-Fi AP", "redistribution rights"],
    }
    archive.write_bytes(compressed)
    manifest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record


if __name__ == "__main__":
    try:
        if len(sys.argv) != 4:
            raise ValueError("usage: package-arm64-busybox-initramfs.py BUSYBOX NEW_CPIO_GZ NEW_MANIFEST")
        result = package(*(Path(arg) for arg in sys.argv[1:]))
        print("SBAT6_STATIC_BUSYBOX_PID1_INITRAMFS_PASS", json.dumps(result, sort_keys=True))
        print("LIMIT: compile-only; no musl, AP, device boot, binary distribution or rights clearance")
    except (OSError, ValueError) as exc:
        print("SBAT6_STATIC_BUSYBOX_PID1_INITRAMFS_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
