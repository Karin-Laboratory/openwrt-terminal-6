#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconstruct one-entry 64-byte AOSP DT table from an independently built FDT.

This is an independently authored standards-based serializer, NOT an OEM
prefix extraction or an LK-acceptance claim. The observed public RC16 P25
prefix was exactly 32B header + 32B entry, with zero id/rev/custom.
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct

DT_TABLE_MAGIC = 0xd7b7ab1e
FDT_MAGIC = bytes.fromhex("d00dfeed")
MAX_FDT_BYTES = 2_000_000


def require(ok, reason):
    if not ok:
        raise ValueError("P25_DTB_TABLE_BLOCKED_" + reason)


def generate(fdt: bytes, page_size: int = 2048) -> bytes:
    require(type(fdt) is bytes and 40 <= len(fdt) <= MAX_FDT_BYTES,
            "FDT_SIZE")
    require(fdt[:4] == FDT_MAGIC, "FDT_MAGIC")
    require(struct.unpack_from(">I", fdt, 4)[0] == len(fdt),
            "FDT_TOTALSIZE")
    require(type(page_size) is int and page_size in (2048, 4096, 8192),
            "PAGE_SIZE")
    section_bytes = 64 + len(fdt)
    header = struct.pack(">8I", DT_TABLE_MAGIC, section_bytes,
                         32, 32, 1, 32, page_size, 0)
    entry = struct.pack(">8I", len(fdt), 64, 0, 0, 0, 0, 0, 0)
    result = header + entry
    require(len(result) == 64, "TABLE_LENGTH")
    return result


def produce(dtb: Path, output: Path, page_size: int = 2048) -> str:
    require(dtb.is_file() and not dtb.is_symlink() and
            not any(p.is_symlink() for p in dtb.parents), "INPUT_PATH")
    require(output.parent.is_dir() and not output.parent.is_symlink()
            and not any(p.is_symlink() for p in output.parents),
            "OUTPUT_PARENT")
    require(not output.exists() and not output.is_symlink(),
            "OUTPUT_EXISTS")
    prefix = generate(dtb.read_bytes(), page_size)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(output, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            n = stream.write(prefix)
            require(n == len(prefix), "SHORT_WRITE")
            stream.flush()
            os.fsync(stream.fileno())
        require(output.read_bytes() == prefix, "READBACK")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return hashlib.sha256(prefix).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dtb", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--page-size", type=int, default=2048)
    a = p.parse_args()
    digest = produce(a.dtb, a.output, a.page_size)
    print("PUBLIC_AOSP_DT_TABLE64_GENERATED_SHA256", digest)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, struct.error) as exc:
        raise SystemExit(str(exc))
