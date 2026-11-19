#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently inspect complete unsigned P25 bytes and source identity."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

SIZE = 33_554_432
HDR_V2_SIZE = 1660
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
CONFIG_KEYS = {
    "kernel_addr", "ramdisk_addr", "second_addr", "tags_addr", "dtb_addr",
    "page_size", "os_version", "name", "cmdline", "ramdisk_mode",
    "dtb_prefix_bytes", "dtb_prefix_sha256",
}


def checked(condition, failure):
    if not condition:
        raise ValueError("P25_VERIFY_FAIL_" + failure)


def aligned(n, page):
    return (n + page - 1) // page * page


def parse_addr(value, bits):
    checked(isinstance(value, str), "CONFIG_ADDRESS_FORMAT")
    try:
        number = int(value, 0)
    except ValueError as exc:
        raise ValueError("P25_VERIFY_FAIL_CONFIG_ADDRESS_FORMAT") from exc
    checked(0 <= number < 2 ** bits and number % 4 == 0,
            "CONFIG_ADDRESS_RANGE")
    return number


def verify(image, kernel, ramdisk, dtb, config, dtb_prefix=None):
    paths = [image, kernel, ramdisk, dtb, config]
    if dtb_prefix is not None:
        paths.append(dtb_prefix)
    for path in paths:
        checked(path.is_file() and not path.is_symlink(), "NONREGULAR_INPUT")
    data = image.read_bytes()
    kernel_bytes = kernel.read_bytes()
    ramdisk_bytes = ramdisk.read_bytes()
    dtb_bytes = dtb.read_bytes()
    checked(len(data) == SIZE, "PARTITION_SIZE")
    checked(data[:8] == b"ANDROID!", "MAGIC")
    cfg = json.loads(config.read_text())
    checked(isinstance(cfg, dict) and set(cfg) == CONFIG_KEYS,
            "CONFIG_SCHEMA")
    checked(cfg["ramdisk_mode"] in ("external", "kernel_embedded"),
            "RAMDISK_MODE")
    page = cfg["page_size"]
    checked(isinstance(page, int) and not isinstance(page, bool)
            and HDR_V2_SIZE <= page <= 65536 and page & (page - 1) == 0,
            "CONFIG_PAGE_SIZE")
    os_version_cfg = cfg["os_version"]
    checked(isinstance(os_version_cfg, int) and not isinstance(os_version_cfg, bool)
            and 0 <= os_version_cfg <= 0xffffffff, "CONFIG_OS_VERSION")
    fields = struct.unpack_from("<10I", data, 8)
    ksize, kaddr, rsize, raddr, ssize, saddr, tags, actual_page, version, os_version = fields
    checked(actual_page == page and version == 2, "HEADER_VERSION_OR_PAGE")
    checked(os_version == os_version_cfg, "CONFIG_OS_VERSION_MISMATCH")
    checked(ssize == 0, "UNEXPECTED_SECOND_STAGE")
    checked(struct.unpack_from("<IQI", data, 1632) == (0, 0, HDR_V2_SIZE),
            "UNEXPECTED_RECOVERY_SECTION")
    dtbsize, dtbaddr = struct.unpack_from("<IQ", data, 1648)
    addresses = tuple(parse_addr(cfg[key], 32) for key in
                      ("kernel_addr", "ramdisk_addr", "second_addr", "tags_addr"))
    addresses += (parse_addr(cfg["dtb_addr"], 64),)
    checked((kaddr, raddr, saddr, tags, dtbaddr) == addresses,
            "CONFIG_LOAD_ADDRESSES")
    checked(len(cfg["name"].encode("ascii")) <= 15 and
            len(cfg["cmdline"].encode("ascii")) <= 1535,
            "CONFIG_STRINGS")
    name, cmdline = cfg["name"].encode("ascii"), cfg["cmdline"].encode("ascii")
    checked(b"\x00" not in name + cmdline, "CONFIG_STRINGS")
    checked(data[48:64] == name.ljust(16, b"\x00"), "CONFIG_NAME")
    checked(data[64:576] == cmdline[:512].ljust(512, b"\x00"),
            "CONFIG_CMDLINE_PRIMARY")
    checked(data[608:1632] == cmdline[512:].ljust(1024, b"\x00"),
            "CONFIG_CMDLINE_EXTRA")

    checked(ksize > 0 and dtbsize > 0, "EMPTY_REQUIRED_SECTION")
    checked((ksize, rsize) == (len(kernel_bytes), len(ramdisk_bytes)),
            "SECTION_SIZE")
    if cfg["ramdisk_mode"] == "kernel_embedded":
        checked(rsize == 0 and not ramdisk_bytes,
                "EXTERNAL_RAMDISK_MUST_BE_EMPTY")
    else:
        checked(rsize > 0, "EXTERNAL_RAMDISK_EMPTY")
    checked(kernel_bytes.startswith(b"\x1f\x8b"), "KERNEL_GZIP")
    try:
        raw_kernel = gzip.decompress(kernel_bytes)
    except (OSError, EOFError) as exc:
        raise ValueError("P25_VERIFY_FAIL_KERNEL_GZIP_INVALID") from exc
    checked(len(raw_kernel) >= 64 and raw_kernel[56:60] == b"ARM\x64",
            "KERNEL_NOT_ARM64_IMAGE")
    checked(len(dtb_bytes) >= 40 and dtb_bytes[:4] == FDT_MAGIC,
            "DTB_MAGIC")
    checked(struct.unpack_from(">I", dtb_bytes, 4)[0] == len(dtb_bytes),
            "DTB_TOTALSIZE")

    prefix_size = cfg["dtb_prefix_bytes"]
    prefix_sha = cfg["dtb_prefix_sha256"]
    checked(isinstance(prefix_size, int) and not isinstance(prefix_size, bool)
            and 0 <= prefix_size <= 4096, "CONFIG_DTB_PREFIX_SIZE")
    if prefix_size:
        checked(dtb_prefix is not None, "DTB_SECTION_PREFIX_MISSING")
        prefix_bytes = dtb_prefix.read_bytes()
        checked(len(prefix_bytes) == prefix_size, "DTB_SECTION_PREFIX_SIZE")
        checked(isinstance(prefix_sha, str) and len(prefix_sha) == 64 and
                hashlib.sha256(prefix_bytes).hexdigest() == prefix_sha,
                "DTB_SECTION_PREFIX_SHA256")
    else:
        checked(prefix_sha == "" and dtb_prefix is None,
                "UNEXPECTED_DTB_SECTION_PREFIX")
        prefix_bytes = b""
    if cfg["ramdisk_mode"] == "kernel_embedded":
        checked(prefix_size > 0, "MTK_PROFILE_REQUIRES_EXPLICIT_DTB_PREFIX")
    dtb_section = prefix_bytes + dtb_bytes
    checked(dtbsize == len(dtb_section), "DTB_SECTION_SIZE")

    sections = (kernel_bytes, ramdisk_bytes, b"", b"", dtb_section)
    offset = page
    for section, label in zip(sections, ("KERNEL", "RAMDISK", "SECOND",
                                         "RECOVERY", "DTB")):
        end = offset + len(section)
        checked(data[offset:end] == section, label + "_MISMATCH")
        gap_end = offset + aligned(len(section), page)
        checked(not any(data[end:gap_end]), label + "_ALIGNMENT_PADDING")
        offset = gap_end
    checked(not any(data[offset:]), "NONZERO_PARTITION_PADDING")
    digest = hashlib.sha1()
    for section in sections:
        digest.update(section)
        digest.update(struct.pack("<I", len(section)))
    checked(data[576:608] == digest.digest() + bytes(12), "BOOT_ID")
    checked(data[HDR_V2_SIZE:page] == bytes(page - HDR_V2_SIZE),
            "HEADER_PADDING")
    return {
        "p25_sha256": hashlib.sha256(data).hexdigest(),
        "partition_bytes": SIZE,
        "page_bytes": page,
        "header_version": 2,
        "ramdisk_mode": cfg["ramdisk_mode"],
        "kernel_sha256": hashlib.sha256(kernel_bytes).hexdigest(),
        "ramdisk_sha256": hashlib.sha256(ramdisk_bytes).hexdigest(),
        "dtb_sha256": hashlib.sha256(dtb_bytes).hexdigest(),
        "dtb_section_prefix_bytes": len(prefix_bytes),
        "dtb_section_prefix_sha256": hashlib.sha256(prefix_bytes).hexdigest(),
        "scope": "UNSIGNED_V2_BYTE_LAYOUT_ONLY",
        "not_proven": ["Air6 boot", "signing", "LK vendor-prefix semantics"],
    }


def main():
    parser = argparse.ArgumentParser()
    for flag in ("p25", "kernel", "ramdisk", "dtb", "config"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--dtb-prefix", type=Path)
    a = parser.parse_args()
    print("P25_INDEPENDENT_READBACK_PASS", json.dumps(
        verify(a.p25, a.kernel, a.ramdisk, a.dtb, a.config, a.dtb_prefix),
        sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise SystemExit(str(exc))
