#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the exact first-stage CPIO is linked into an ARM64 kernel image."""
import argparse
import gzip
import hashlib
import lzma
from pathlib import Path
import struct

ELF64_SHDR = struct.Struct("<IIQQQQIIQQ")


def require(ok, code):
    if not ok:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_" + code)


def section(data, wanted):
    require(len(data) >= 64 and data[:4] == b"\x7fELF", "ELF_MAGIC")
    require(data[4] == 2 and data[5] == 1, "ELF64_LITTLE_ENDIAN")
    require(struct.unpack_from("<H", data, 18)[0] == 183, "ELF_NOT_AARCH64")
    shoff = struct.unpack_from("<Q", data, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 58)
    require(shentsize >= ELF64_SHDR.size and shnum > 1 and
            shstrndx < shnum, "ELF_SECTION_TABLE")
    require(shoff + shentsize * shnum <= len(data), "ELF_SECTION_BOUNDS")
    headers = [ELF64_SHDR.unpack_from(data, shoff + i * shentsize)
               for i in range(shnum)]
    shstr = headers[shstrndx]
    names_off, names_size = shstr[4], shstr[5]
    require(names_off + names_size <= len(data), "ELF_NAMES_BOUNDS")
    names = data[names_off:names_off + names_size]
    matches = []
    for header in headers:
        nameoff, stype, flags, addr, offset, size, link, info, align, entsize = header
        require(nameoff < len(names), "ELF_SECTION_NAME")
        end = names.find(b"\0", nameoff)
        require(end >= 0, "ELF_SECTION_NAME_TERMINATOR")
        if names[nameoff:end] == wanted.encode("ascii"):
            require(stype != 8 and offset + size <= len(data),
                    "ELF_TARGET_SECTION_BOUNDS")
            matches.append(data[offset:offset + size])
    require(len(matches) == 1, "ELF_TARGET_SECTION_COUNT")
    return matches[0]


def verify(obj, vmlinux, image, kernel_gz, cpio, compression="xz"):
    paths = (obj, vmlinux, image, kernel_gz, cpio)
    require(all(p.is_file() and not p.is_symlink() for p in paths), "INPUT")
    object_data = section(obj.read_bytes(), ".init.ramfs")
    linked_data = section(vmlinux.read_bytes(), ".init.ramfs")
    require(object_data and object_data == linked_data, "OBJECT_NOT_LINKED")
    if compression == "xz":
        try:
            decoded = lzma.decompress(object_data)
        except lzma.LZMAError as exc:
            raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_XZ_DECODE") from exc
    elif compression == "none":
        decoded = object_data
    else:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_UNSUPPORTED_COMPRESSION")
    cpio_data = cpio.read_bytes()
    require(decoded == cpio_data, "CPIO_CONTENT_MISMATCH")
    raw_image = image.read_bytes()
    require(len(raw_image) >= 64 and raw_image[56:60] == b"ARM\x64",
            "IMAGE_NOT_ARM64")
    require(raw_image.count(object_data) == 1, "INITRAMFS_NOT_UNIQUE_IN_IMAGE")
    try:
        decompressed_kernel = gzip.decompress(kernel_gz.read_bytes())
    except (OSError, EOFError) as exc:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_KERNEL_GZIP") from exc
    require(decompressed_kernel == raw_image, "KERNEL_GZIP_IMAGE_MISMATCH")
    return {
        "status": "ARM64_KERNEL_INITRAMFS_OBJECT_AND_IMAGE_VERIFIED",
        "cpio_bytes": len(cpio_data),
        "cpio_sha256": hashlib.sha256(cpio_data).hexdigest(),
        "compressed_initramfs_bytes": len(object_data),
        "compressed_initramfs_sha256": hashlib.sha256(object_data).hexdigest(),
        "kernel_image_sha256": hashlib.sha256(raw_image).hexdigest(),
        "kernel_gzip_sha256": hashlib.sha256(kernel_gz.read_bytes()).hexdigest(),
        "compression": compression,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("object", "vmlinux", "image", "kernel-gz", "cpio"):
        ap.add_argument("--" + name, required=True, type=Path)
    ap.add_argument("--compression", choices=("xz", "none"), default="xz")
    a = ap.parse_args()
    result = verify(a.object, a.vmlinux, a.image, a.kernel_gz, a.cpio,
                    a.compression)
    print("PUBLIC_P25_KERNEL_BUILTIN_INITRAMFS_VERIFY_PASS", result)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, struct.error) as exc:
        raise SystemExit(str(exc))
