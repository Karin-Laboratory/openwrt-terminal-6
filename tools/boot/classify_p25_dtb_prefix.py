#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private, read-only identification of the 64 bytes before an Air6 P25 FDT.

Tests complete AOSP DT table 32+32 or U-Boot legacy uImage header semantics.
Neither header shape nor magic proves the specific device LK uses the format.
No OEM bytes, device IDs, prefix hex or binary artifacts are emitted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

P25_SIZE = 33_554_432
PREFIX_BYTES = 64
FDT_MAGIC = bytes.fromhex("d00dfeed")
DT_TABLE_MAGIC = 0xd7b7ab1e
UIMAGE_MAGIC = 0x27051956


def require(ok, reason):
    if not ok:
        raise ValueError("P25_DTB_PREFIX_BLOCKED_" + reason)


def regular(path):
    return (path.is_file() and not path.is_symlink()
            and not any(p.is_symlink() for p in path.parents))


def align(value, page):
    return ((value + page - 1) // page) * page


def dt_table_check(prefix, section, fdt_length, page):
    """Strict single-entry table only, so 64 bytes unambiguously cover it."""
    fields = struct.unpack_from("<8I", prefix)
    magic, total, header, entry_size, count, entry_off, table_page, version = fields
    if magic != DT_TABLE_MAGIC:
        return False
    if not (total == len(section) and header == 32 and entry_size == 32
            and count == 1 and entry_off == 32 and
            table_page == page and version in (0, 1)):
        return False
    dt_size, dt_off, _id, _rev, *_custom = struct.unpack_from("<8I", prefix, 32)
    return (dt_size == fdt_length and dt_off == 64
            and dt_off + dt_size == total)


def uimage_check(prefix, section):
    """Header and payload CRC both required; CRC is not authentication."""
    if struct.unpack_from(">I", prefix)[0] != UIMAGE_MAGIC:
        return (False, False, False)
    saved_crc = struct.unpack_from(">I", prefix, 4)[0]
    h = bytearray(prefix)
    h[4:8] = bytes(4)
    header_crc = zlib.crc32(h) & 0xffffffff == saved_crc
    size = struct.unpack_from(">I", prefix, 12)[0]
    payload_crc = (zlib.crc32(section[64:]) & 0xffffffff ==
                   struct.unpack_from(">I", prefix, 24)[0])
    size_ok = size == len(section) - 64
    return (header_crc, payload_crc, size_ok)


def inspect(reference, expected_sha):
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha or "") is not None,
            "REFERENCE_SHA_SYNTAX")
    require(regular(reference) and reference.stat().st_size == P25_SIZE,
            "REFERENCE_PATH_OR_SIZE")
    blob = reference.read_bytes()
    require(hashlib.sha256(blob).hexdigest() == expected_sha,
            "REFERENCE_SHA_MISMATCH")
    require(blob[:8] == b"ANDROID!", "BOOT_MAGIC")
    page, version = struct.unpack_from("<II", blob, 36)
    require(version == 2 and page in (2048, 4096, 8192), "BOOT_V2_HEADER")
    require(struct.unpack_from("<I", blob, 1644)[0] == 1660, "BOOT_HEADER_SIZE")
    kernel, ramdisk, second = (struct.unpack_from("<I", blob, offset)[0]
                               for offset in (8, 16, 24))
    recovery = struct.unpack_from("<I", blob, 1632)[0]
    dtb_size = struct.unpack_from("<I", blob, 1648)[0]
    at = page
    for size in (kernel, ramdisk, second, recovery):
        require(size <= P25_SIZE and at + align(size, page) <= P25_SIZE,
                "SECTION_BOUNDS")
        at += align(size, page)
    require(dtb_size >= PREFIX_BYTES + 40 and at + dtb_size <= P25_SIZE,
            "DTB_SECTION_BOUNDS")
    section = blob[at:at + dtb_size]
    prefix, fdt = section[:64], section[64:]
    require(fdt[:4] == FDT_MAGIC, "FDT_AFTER_PREFIX_MAGIC")
    fdt_bytes = struct.unpack_from(">I", fdt, 4)[0]
    require(40 <= fdt_bytes == len(fdt), "FDT_TOTALSIZE")
    dt_magic = struct.unpack_from("<I", prefix)[0] == DT_TABLE_MAGIC
    u_magic = struct.unpack_from(">I", prefix)[0] == UIMAGE_MAGIC
    table_ok = dt_table_check(prefix, section, len(fdt), page)
    u_header_crc, u_data_crc, u_size = uimage_check(prefix, section)
    u_ok = u_magic and u_header_crc and u_data_crc and u_size
    if table_ok:
        kind = "AOSP_SINGLE_ENTRY_DT_TABLE_STRUCTURALLY_VALID"
    elif u_ok:
        kind = "UBOOT_LEGACY_UIMAGE_STRUCTURALLY_VALID"
    else:
        kind = "UNCLASSIFIED_PREFIX_NO_FORMAT_PROVEN"
    if not table_ok and dt_magic:
        finding = "DT_TABLE_MAGIC_PRESENT_BUT_FIELDS_OR_BOUNDS_INVALID"
    elif not u_ok and u_magic:
        finding = "UIMAGE_MAGIC_PRESENT_BUT_CRC_OR_SIZE_INVALID"
    else:
        finding = "NO_KNOWN_HEADER_MATCH"
    return {
        "schema": 1,
        "status": "STRUCTURE_ONLY_NO_LK_OR_RIGHTS_APPROVAL",
        "reference_p25_sha256": expected_sha,
        "dtb_section_bytes": dtb_size,
        "fdt_bytes": fdt_bytes,
        "fdt_offset_in_dtb_section": PREFIX_BYTES,
        "observed_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        "prefix_format": kind,
        "diagnostic": finding,
        "android_dt_table": {
            "magic_matches": dt_magic,
            "single_entry_32_plus_32_valid": table_ok,
        },
        "uboot_legacy_image": {
            "magic_matches": u_magic,
            "header_crc_matches": u_header_crc,
            "payload_crc_matches": u_data_crc,
            "payload_size_matches": u_size,
        },
        "references": [
            "https://source.android.com/docs/core/architecture/dto/partitions",
            "https://android.googlesource.com/platform/external/u-boot/+/e25919d3a133b78691b7287db3f461db74be0562/include/image.h",
        ],
        "prefix_or_identifier_bytes_exported": False,
        "format_proves_lk_consumption": False,
        "independent_header_generation_approved": False,
        "redistribution_approved": False,
        "signature_or_device_actions": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--private-report", type=Path, required=True)
    args = parser.parse_args()
    out = args.private_report
    require(out.is_absolute() and out.parent.is_dir() and not
            out.exists() and not out.is_symlink() and not any(
                parent.is_symlink() for parent in out.parents),
            "PRIVATE_REPORT_MUST_BE_NEW")
    result = inspect(args.reference, args.expected_sha256)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(out, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("P25_PRIVATE_PREFIX_CLASSIFICATION_" +
          result["prefix_format"] + "_NOT_LK_OR_RIGHTS_APPROVED")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, struct.error) as exc:
        raise SystemExit(str(exc))
