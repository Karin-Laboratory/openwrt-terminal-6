#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package a build-only static AArch64 BusyBox rootfs *stage* without executing it.

Not an OpenWrt rootfs: no init, procd, netifd, networking, passwords or firmware.
The archive is temporary and must never be treated as installable.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import sys
import tarfile


def check_static_aarch64_elf(blob: bytes) -> None:
    if len(blob) < 64 or blob[:6] != b"\x7fELF\x02\x01":
        raise ValueError("not little-endian ELF64")
    elf_type, machine = struct.unpack_from("<HH", blob, 16)
    offset = struct.unpack_from("<Q", blob, 32)[0]
    size, count = struct.unpack_from("<HH", blob, 54)
    if elf_type not in (2, 3) or machine != 183 or size != 56 or not count:
        raise ValueError("not an AArch64 executable with program headers")
    if offset < 64 or offset + size * count > len(blob):
        raise ValueError("invalid program header table")
    for index in range(count):
        p_type = struct.unpack_from("<I", blob, offset + index * size)[0]
        if p_type == 3:  # PT_INTERP: would need a dynamic loader not in this stage
            raise ValueError("dynamic interpreter is forbidden")
    # This is an ELF structure check, not proof of runtime or static dependencies.


def package(binary: Path, archive: Path, manifest: Path,
            libc: str = "host-glibc-static") -> dict:
    if libc not in ("host-glibc-static", "musl-static"):
        raise ValueError("unsupported libc identity")
    for output in (archive, manifest):
        if output.exists() or output.is_symlink():
            raise ValueError("output must not already exist")
    if binary.is_symlink() or not binary.is_file():
        raise ValueError("binary must be a regular file")
    payload = binary.read_bytes()
    check_static_aarch64_elf(payload)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        def add(name: str, mode: int, kind: bytes, data: bytes = b"",
                linkname: str = "") -> None:
            info = tarfile.TarInfo(name)
            info.mode = mode
            info.type = kind
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            info.linkname = linkname
            info.size = len(data) if kind == tarfile.REGTYPE else 0
            tar.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)

        for directory in ("bin", "dev", "etc", "proc", "sbin", "sys", "tmp"):
            add(directory, 0o755, tarfile.DIRTYPE)
        add("bin/busybox", 0o755, tarfile.REGTYPE, payload)
        add("bin/sh", 0o777, tarfile.SYMTYPE, linkname="busybox")
        # Deliberately no /init, inittab, preset credentials or network config.
    compressed = gzip.compress(buffer.getvalue(), compresslevel=9, mtime=0)
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode="r:") as tar:
        names = sorted(tar.getnames())
        if names != sorted(["bin", "dev", "etc", "proc", "sbin", "sys", "tmp",
                            "bin/busybox", "bin/sh"]):
            raise ValueError("unexpected rootfs-stage contents")
        if hashlib.sha256(tar.extractfile("bin/busybox").read()).digest() != hashlib.sha256(payload).digest():
            raise ValueError("BusyBox archive roundtrip mismatch")
    record = {
        "scope": ("NONINSTALLABLE_MUSL_BUSYBOX_ROOTFS_STAGE"
                  if libc == "musl-static"
                  else "NONINSTALLABLE_STATIC_BUSYBOX_ROOTFS_STAGE"),
        "libc": libc,
        "architecture": "aarch64",
        "busybox_version": "1.36.1",
        "busybox_commit": "1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4",
        "busybox_sha256": hashlib.sha256(payload).hexdigest(),
        "archive_sha256": hashlib.sha256(compressed).hexdigest(),
        "archive_bytes": len(compressed),
        "rights_review": "pending",
        "not_proven": [("OpenWrt musl toolchain/package closure"
                        if libc == "musl-static" else "musl/OpenWrt toolchain"),
                       "SBAT6 target", "init/PID1",
                       "procd/netifd/wpad", "kernel ABI", "Air6 boot/AP",
                       "source redistribution rights"],
    }
    archive.write_bytes(compressed)
    manifest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record


if __name__ == "__main__":
    try:
        if len(sys.argv) not in (4, 5):
            raise ValueError("usage: package-arm64-busybox-rootfs.py ELF NEW_TAR_GZ NEW_MANIFEST [host-glibc-static|musl-static]")
        result = package(*(Path(arg) for arg in sys.argv[1:4]),
                         libc=sys.argv[4] if len(sys.argv) == 5 else "host-glibc-static")
        print("SBAT6_STATIC_BUSYBOX_ROOTFS_STAGE_PASS", json.dumps(result, sort_keys=True))
        print("LIMIT: not OpenWrt, no PID1, no device use, no redistribution clearance")
    except (OSError, ValueError, tarfile.TarError) as exc:
        print("SBAT6_STATIC_BUSYBOX_ROOTFS_STAGE_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
