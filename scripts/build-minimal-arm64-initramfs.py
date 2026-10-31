#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a temporary, unsigned AArch64 PID1 initramfs; never install/upload it."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/air6-diagnostic-init.c"


def newc_entry(name: str, mode: int, payload: bytes = b"", ino: int = 1,
               rdevmajor: int = 0, rdevminor: int = 0) -> bytes:
    if not name or name.startswith("/") or ".." in name.split("/") or "\x00" in name:
        raise ValueError("unsafe cpio name")
    name_bytes = name.encode("ascii") + b"\x00"
    fields = (ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0,
              len(payload), 0, 0, rdevmajor, rdevminor, len(name_bytes), 0)
    header = b"070701" + b"".join(f"{field:08x}".encode("ascii") for field in fields)
    record = header + name_bytes
    record += b"\x00" * (-len(record) % 4)
    record += payload
    record += b"\x00" * (-len(record) % 4)
    return record


def make_archive(init_elf: bytes) -> bytes:
    entries = [
        ("dev", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3),
        ("proc", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("sys", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("init", stat.S_IFREG | 0o755, init_elf, 0, 0),
    ]
    raw = b"".join(newc_entry(name, mode, data, i, major, minor)
                   for i, (name, mode, data, major, minor) in enumerate(entries, 1))
    raw += newc_entry("TRAILER!!!", 0, ino=len(entries) + 1)
    return raw


def validate_elf(data: bytes) -> None:
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("not ELF64 little-endian")
    kind, machine = struct.unpack_from("<HH", data, 16)
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    if kind != 2 or machine != 183 or not phnum or phentsize != 56:
        raise ValueError("not a static AArch64 ET_EXEC")
    if phoff + phnum * phentsize > len(data):
        raise ValueError("invalid ELF program headers")
    for i in range(phnum):
        p_type = struct.unpack_from("<I", data, phoff + i * phentsize)[0]
        if p_type == 3:  # PT_INTERP requires an absent dynamic linker
            raise ValueError("dynamic loader forbidden in standalone initramfs")


def build(output: Path) -> dict:
    if os.geteuid() == 0:
        raise ValueError("refuse privileged build")
    if output.exists() or output.is_symlink():
        raise ValueError("output directory must not already exist")
    if not shutil.which("clang") or not shutil.which("ld.lld"):
        raise ValueError("preinstalled clang and ld.lld are required")
    output.mkdir(mode=0o700, parents=False)
    elf_path = output / "init.elf"
    cmd = ["clang", "--target=aarch64-linux-gnu", "-fuse-ld=lld", "-nostdlib",
           "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fno-pic",
           "-static", "-O2", "-Wl,-e,_start", "-Wl,--build-id=none",
           "-o", str(elf_path), str(SOURCE)]
    subprocess.run(cmd, check=True, timeout=90)
    elf = elf_path.read_bytes()
    validate_elf(elf)
    raw = make_archive(elf)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    if gzip.decompress(compressed) != raw:
        raise ValueError("archive compression round-trip failed")
    archive_path = output / "initramfs.cpio.gz"
    archive_path.write_bytes(compressed)
    manifest = {
        "scope": "UNSIGNED_NONINSTALLABLE_DIAGNOSTIC_ONLY",
        "architecture": "aarch64",
        "compiler": subprocess.check_output(["clang", "--version"], text=True).splitlines()[0],
        "linker": subprocess.check_output(["ld.lld", "--version"], text=True).strip(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "init_elf_sha256": hashlib.sha256(elf).hexdigest(),
        "initramfs_sha256": hashlib.sha256(compressed).hexdigest(),
        "initramfs_bytes": len(compressed),
        "not_proven": ["kernel Image", "Air6 DTB", "OpenWrt rootfs", "AP runtime",
                       "device boot", "redistribution rights"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    elf_path.unlink()  # Do not retain standalone executable outside the archive.
    return manifest


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: build-minimal-arm64-initramfs.py NEW_OUTPUT_DIRECTORY")
        result = build(Path(sys.argv[1]))
        print("ARM64_PID1_INITRAMFS_BUILD_PASS", json.dumps(result, sort_keys=True))
        print("LIMIT: ephemeral unsigned diagnostic archive, no Image/DTB/AP/flash/rights claim")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("ARM64_PID1_INITRAMFS_BUILD_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
