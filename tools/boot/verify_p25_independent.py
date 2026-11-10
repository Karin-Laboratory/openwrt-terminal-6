#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently inspect full unsigned Android boot-v2 p25 bytes and input identity."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SIZE = 33_554_432
PAGE = 4096


def checked(condition, failure):
    if not condition:
        raise ValueError("P25_VERIFY_FAIL_" + failure)


def aligned(n):
    return (n + PAGE - 1) // PAGE * PAGE


def verify(image, kernel, ramdisk, dtb):
    for path in (image, kernel, ramdisk, dtb):
        checked(path.is_file() and not path.is_symlink(), "NONREGULAR_INPUT")
    data = image.read_bytes()
    checked(len(data) == SIZE, "PARTITION_SIZE")
    checked(data[:8] == b"ANDROID!", "MAGIC")
    ksize, kaddr, rsize, raddr, ssize, saddr, tags, page, version, os_version = (
        struct.unpack_from("<10I", data, 8))
    checked(page == PAGE and version == 2, "HEADER_VERSION_OR_PAGE")
    checked(ssize == 0 and saddr == 0, "UNEXPECTED_SECOND_STAGE")
    checked(struct.unpack_from("<IQI", data, 1632) == (0, 0, 1660),
            "UNEXPECTED_RECOVERY_SECTION")
    dtbsize, dtbaddr = struct.unpack_from("<IQ", data, 1648)
    checked(all((kaddr, raddr, tags, dtbaddr)), "MISSING_LOAD_ADDRESS")
    checked(ksize > 0 and rsize > 0 and dtbsize > 0, "EMPTY_SECTION")
    sections = (kernel.read_bytes(), ramdisk.read_bytes(), dtb.read_bytes())
    checked((ksize, rsize, dtbsize) == tuple(len(s) for s in sections),
            "SECTION_SIZE")
    offset = PAGE
    for section, label in zip(sections, ("KERNEL", "RAMDISK", "DTB")):
        checked(data[offset:offset + len(section)] == section, label + "_MISMATCH")
        gap_end = offset + aligned(len(section))
        checked(not any(data[offset + len(section):gap_end]),
                label + "_ALIGNMENT_PADDING")
        offset = gap_end
    checked(not any(data[offset:]), "NONZERO_PARTITION_PADDING")
    digest = hashlib.sha1()
    for section in (*sections[:2], b"", b"", sections[2]):
        digest.update(section)
        digest.update(struct.pack("<I", len(section)))
    checked(data[576:608] == digest.digest() + bytes(12), "BOOT_ID")
    checked(data[1660:PAGE] == bytes(PAGE - 1660), "HEADER_PADDING")
    return {"p25_sha256": hashlib.sha256(data).hexdigest(),
            "partition_bytes": SIZE,
            "kernel_sha256": hashlib.sha256(sections[0]).hexdigest(),
            "ramdisk_sha256": hashlib.sha256(sections[1]).hexdigest(),
            "dtb_sha256": hashlib.sha256(sections[2]).hexdigest(),
            "scope": "UNSIGNED_V2_BYTE_LAYOUT_ONLY",
            "not_proven": ["Air6 boot", "signing", "OEM extension acceptance"]}


def main():
    parser = argparse.ArgumentParser()
    for flag in ("p25", "kernel", "ramdisk", "dtb"):
        parser.add_argument("--" + flag, required=True, type=Path)
    a = parser.parse_args()
    print("P25_INDEPENDENT_READBACK_PASS", json.dumps(
        verify(a.p25, a.kernel, a.ramdisk, a.dtb), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
