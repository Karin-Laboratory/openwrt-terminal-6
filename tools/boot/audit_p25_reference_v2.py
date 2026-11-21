#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit a pinned, owner-held boot-v2 P25 without exporting OEM bytes.

This reconstructs only Android-v2 header/layout observations from an explicitly
supplied local reference. A matching prefix is *not* a redistribution license,
not a reverse-engineered LK contract, and not a public manufacture approval.
No signing, device access, extraction, or binary publication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct

PARTITION_BYTES = 33_554_432
HEADER_BYTES = 1660
FDT_MAGIC = bytes.fromhex("d00dfeed")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def require(ok, reason):
    if not ok:
        raise ValueError("P25_REFERENCE_BLOCKED_" + reason)


def regular(path):
    return (path.is_file() and not path.is_symlink()
            and not any(parent.is_symlink() for parent in path.parents))


def aligned(n, page):
    return (n + page - 1) // page * page


def nul_ascii(data, label):
    require(b"\x00" in data, label + "_NOT_TERMINATED")
    a, padding = data.split(b"\x00", 1)
    require(not any(padding), label + "_TRAILING_BYTES")
    try:
        return a.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("P25_REFERENCE_BLOCKED_" + label + "_NONASCII") from exc


def inspect(reference, expected_sha, prefix=None):
    require(SHA.fullmatch(expected_sha) is not None, "EXPECTED_SHA")
    require(regular(reference) and reference.stat().st_size == PARTITION_BYTES,
            "REFERENCE_PATH_OR_SIZE")
    data = reference.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_sha,
            "REFERENCE_SHA_MISMATCH")
    require(data[:8] == b"ANDROID!", "ANDROID_MAGIC")
    fields = struct.unpack_from("<10I", data, 8)
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, tags_addr, page, version, os_version = fields
    require(version == 2 and page in (2048, 4096, 8192), "HEADER_VERSION_OR_PAGE")
    require(struct.unpack_from("<I", data, 1644)[0] == HEADER_BYTES,
            "HEADER_SIZE")
    recovery_size, recovery_offset = struct.unpack_from("<IQ", data, 1632)
    dtb_size, dtb_addr = struct.unpack_from("<IQ", data, 1648)
    require(kernel_size > 0 and dtb_size > 64, "REQUIRED_SECTION_EMPTY")
    require(second_size == 0 and recovery_size == 0 and recovery_offset == 0,
            "UNSUPPORTED_SECTIONS")
    require(ramdisk_size == 0, "EXTERNAL_RAMDISK_UNEXPECTED")
    name = nul_ascii(data[48:64], "BOARD_NAME")
    cmdline = nul_ascii(data[64:576], "CMDLINE") + nul_ascii(
        data[608:1632], "EXTRA_CMDLINE")
    sizes = (kernel_size, ramdisk_size, second_size, recovery_size, dtb_size)
    offsets = []
    cursor = page
    for size in sizes:
        require(size <= PARTITION_BYTES and cursor + size <= PARTITION_BYTES,
                "SECTION_BOUNDS")
        offsets.append(cursor)
        end = cursor + size
        next_cursor = cursor + aligned(size, page)
        require(next_cursor <= PARTITION_BYTES and
                not any(data[end:next_cursor]), "SECTION_PADDING")
        cursor = next_cursor
    require(not any(data[HEADER_BYTES:page]), "HEADER_PADDING")
    section = data[offsets[4]:offsets[4] + dtb_size]
    require(section[64:68] == FDT_MAGIC, "VENDOR64_FDT_OFFSET")
    total = struct.unpack_from(">I", section, 68)[0]
    require(total >= 40 and total == len(section) - 64,
            "BARE_DTB_TOTALSIZE")
    if prefix is not None:
        require(regular(prefix) and prefix.stat().st_size == 64,
                "PREFIX_PATH_OR_SIZE")
        require(prefix.read_bytes() == section[:64],
                "PREFIX_NOT_FROM_REFERENCE")
    # The boot ID is the SHA1 of five sections each followed by its uint32 size.
    h = hashlib.sha1()
    for start, length in zip(offsets, sizes):
        h.update(data[start:start + length])
        h.update(struct.pack("<I", length))
    require(data[576:608] == h.digest() + bytes(12), "BOOT_ID")
    return {
        "schema": 1,
        "status": "PRIVATE_REFERENCE_LAYOUT_VERIFIED_NOT_LICENSED",
        "reference_p25_sha256": expected_sha,
        "reference_size": len(data),
        "android_header": {
            "version": version, "header_bytes": HEADER_BYTES, "page_size": page,
            "kernel_addr": hex(kernel_addr), "ramdisk_addr": hex(ramdisk_addr),
            "second_addr": hex(second_addr), "tags_addr": hex(tags_addr),
            "dtb_addr": hex(dtb_addr), "os_version": os_version,
            "name": name, "cmdline": cmdline, "kernel_size": kernel_size,
            "ramdisk_size": ramdisk_size, "dtb_size": dtb_size,
        },
        "reference_prefix": {
            "bytes": 64,
            "sha256": hashlib.sha256(section[:64]).hexdigest(),
            "independently_supplied_candidate_matches": prefix is not None,
            "origin": "OWNER-PRIVATE-RC11-P25-TEMPLATE-REUSE",
            "rights": "UNVERIFIED",
            "lk_semantics": "UNVERIFIED",
        },
        "bare_dtb_sha256": hashlib.sha256(section[64:]).hexdigest(),
        "kernel_gzip_sha256": hashlib.sha256(
            data[offsets[0]:offsets[0] + kernel_size]).hexdigest(),
        "boot_id_sha1": h.hexdigest(),
        "binary_or_prefix_bytes_exported": False,
        "device_writes": False, "signed_new_image": False,
        "public_manufacture_configuration_approved": False,
        "not_proven": [
            "reference rights/redistribution", "prefix semantic meaning",
            "load-address applicability to a new Image",
            "public-board DTB compatibility", "Air6 LK acceptance",
            "target hardware cold boot",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--candidate-prefix", type=Path)
    ap.add_argument("--private-receipt", required=True, type=Path)
    args = ap.parse_args()
    out = args.private_receipt
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not any(p.is_symlink() for p in out.parents),
            "RECEIPT_OUTPUT_NOT_FRESH_PRIVATE")
    result = inspect(args.reference, args.expected_sha256,
                     args.candidate_prefix)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(out, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("P25_REFERENCE_LAYOUT_VERIFIED_PRIVATE_ONLY; ",
          "BOOT_CONFIG_AND_PREFIX_RIGHTS_BLOCKED")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise SystemExit(str(exc))
