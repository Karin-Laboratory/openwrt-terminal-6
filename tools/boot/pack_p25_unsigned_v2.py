#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an unsigned Android-v2-shaped p25 from explicit external inputs.

The ``kernel_embedded`` ramdisk mode models the observed MTK/LK RC14 layout:
the CPIO is linked into the kernel and the boot-header ramdisk size is zero.
This is a device-specific deviation from the AOSP v2 requirement that a
ramdisk section be present. An opaque DTB-section prefix can be provided as a
separate, hash-pinned input; no OEM prefix or load values are bundled here.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

PARTITION = 32 * 1024 * 1024
DEFAULT_PAGE = 4096
HDR_V2_SIZE = 1660
MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
CONFIG_KEYS = {
    "kernel_addr", "ramdisk_addr", "second_addr", "tags_addr", "dtb_addr",
    "page_size", "os_version", "name", "cmdline", "ramdisk_mode",
    "dtb_prefix_bytes", "dtb_prefix_sha256",
}


def require(condition, name):
    if not condition:
        raise ValueError("P25_BLOCKED_" + name)


def read_regular(path):
    require(path.is_file() and not path.is_symlink(), "NONREGULAR_INPUT")
    return path.read_bytes()


def parse_addr(value, bits, label):
    require(isinstance(value, str), label + "_FORMAT")
    try:
        number = int(value, 0)
    except ValueError as exc:
        raise ValueError("P25_BLOCKED_" + label + "_FORMAT") from exc
    require(0 <= number < 2 ** bits and number % 4 == 0, label)
    return number


def align(data, page):
    return data + bytes((-len(data)) % page)


def validate_config(config):
    require(isinstance(config, dict) and set(config) == CONFIG_KEYS,
            "CONFIG_KEYS")
    require(config["ramdisk_mode"] in ("external", "kernel_embedded"),
            "RAMDISK_MODE")
    page = config["page_size"]
    require(isinstance(page, int) and not isinstance(page, bool) and
            HDR_V2_SIZE <= page <= 65536 and page & (page - 1) == 0,
            "PAGE_SIZE")
    os_version = config["os_version"]
    require(isinstance(os_version, int) and not isinstance(os_version, bool)
            and 0 <= os_version <= 0xffffffff, "OS_VERSION")
    addresses = {
        "kernel_addr": parse_addr(config["kernel_addr"], 32, "KERNEL_ADDRESS"),
        "ramdisk_addr": parse_addr(config["ramdisk_addr"], 32, "RAMDISK_ADDRESS"),
        "second_addr": parse_addr(config["second_addr"], 32, "SECOND_ADDRESS"),
        "tags_addr": parse_addr(config["tags_addr"], 32, "TAGS_ADDRESS"),
        "dtb_addr": parse_addr(config["dtb_addr"], 64, "DTB_ADDRESS"),
    }
    prefix_bytes = config["dtb_prefix_bytes"]
    prefix_sha = config["dtb_prefix_sha256"]
    require(isinstance(prefix_bytes, int) and not isinstance(prefix_bytes, bool)
            and 0 <= prefix_bytes <= 4096, "DTB_PREFIX_LENGTH")
    if prefix_bytes == 0:
        require(prefix_sha == "", "DTB_PREFIX_SHA256")
    else:
        require(isinstance(prefix_sha, str) and len(prefix_sha) == 64 and
                all(ch in "0123456789abcdef" for ch in prefix_sha),
                "DTB_PREFIX_SHA256")
    require(isinstance(config["name"], str) and
            isinstance(config["cmdline"], str), "CONFIG_STRINGS")
    return addresses, page, os_version, prefix_bytes, prefix_sha


def build(kernel_path, ramdisk_path, dtb_path, cfg_path, output,
          dtb_prefix_path=None):
    require(not output.exists() and not output.is_symlink(), "OUTPUT_EXISTS")
    require(not output.parent.is_symlink(), "OUTPUT_PARENT_SYMLINK")
    kernel = read_regular(kernel_path)
    ramdisk = read_regular(ramdisk_path)
    dtb = read_regular(dtb_path)
    config = json.loads(read_regular(cfg_path))
    addresses, page, os_version, prefix_bytes, prefix_sha = validate_config(config)

    require(len(kernel) < PARTITION and kernel.startswith(b"\x1f\x8b"),
            "KERNEL_GZIP_REQUIRED")
    try:
        uncompressed = gzip.decompress(kernel)
    except (OSError, EOFError) as exc:
        raise ValueError("P25_BLOCKED_KERNEL_GZIP_INVALID") from exc
    require(len(uncompressed) >= 64 and uncompressed[56:60] == b"ARM\x64",
            "KERNEL_NOT_ARM64_IMAGE")
    if config["ramdisk_mode"] == "kernel_embedded":
        require(len(ramdisk) == 0, "EXTERNAL_RAMDISK_MUST_BE_EMPTY")
    else:
        require(bool(ramdisk), "EXTERNAL_RAMDISK_EMPTY")

    require(len(dtb) >= 40 and dtb[:4] == FDT_MAGIC, "DTB_MAGIC")
    total_dtb = struct.unpack_from(">I", dtb, 4)[0]
    require(total_dtb == len(dtb), "DTB_TOTALSIZE")
    if prefix_bytes:
        require(dtb_prefix_path is not None, "DTB_SECTION_PREFIX_MISSING")
        prefix = read_regular(dtb_prefix_path)
        require(len(prefix) == prefix_bytes, "DTB_SECTION_PREFIX_SIZE")
        require(hashlib.sha256(prefix).hexdigest() == prefix_sha,
                "DTB_SECTION_PREFIX_SHA256")
    else:
        require(dtb_prefix_path is None, "UNEXPECTED_DTB_SECTION_PREFIX")
        prefix = b""
    dtb_section = prefix + dtb

    name = config["name"].encode("ascii")
    cmdline = config["cmdline"].encode("ascii")
    require(len(name) <= 15 and len(cmdline) <= 1535 and
            b"\x00" not in name + cmdline, "NAME_OR_CMDLINE")
    if config["ramdisk_mode"] == "kernel_embedded":
        # RC14's measured header uses a built-in initramfs and zero external
        # ramdisk size. This profile is not AOSP VTS-conformant boot-v2.
        require(prefix_bytes > 0, "MTK_PROFILE_REQUIRES_EXPLICIT_DTB_PREFIX")

    digest = hashlib.sha1()
    for data in (kernel, ramdisk, b"", b"", dtb_section):
        digest.update(data)
        digest.update(struct.pack("<I", len(data)))
    boot_id = digest.digest() + bytes(12)

    header = bytearray(HDR_V2_SIZE)
    header[:8] = MAGIC
    struct.pack_into("<10I", header, 8,
                     len(kernel), addresses["kernel_addr"],
                     len(ramdisk), addresses["ramdisk_addr"],
                     0, addresses["second_addr"], addresses["tags_addr"],
                     page, 2, os_version)
    header[48:64] = name.ljust(16, b"\x00")
    header[64:576] = cmdline[:512].ljust(512, b"\x00")
    header[576:608] = boot_id
    header[608:1632] = cmdline[512:].ljust(1024, b"\x00")
    struct.pack_into("<IQI", header, 1632, 0, 0, HDR_V2_SIZE)
    struct.pack_into("<IQ", header, 1648, len(dtb_section), addresses["dtb_addr"])

    sections = (kernel, ramdisk, b"", b"", dtb_section)
    payload = bytearray(align(bytes(header), page))
    for section in sections:
        payload.extend(align(section, page))
    require(len(payload) <= PARTITION, "PARTITION_OVERFLOW")
    data = bytes(payload) + bytes(PARTITION - len(payload))
    output.write_bytes(data)
    receipt = {
        "scope": "UNSIGNED_P25_PRE_SIGNING_ONLY",
        "profile": "MTK_LK_BOOT_V2" if config["ramdisk_mode"] == "kernel_embedded"
                   else "ANDROID_BOOT_V2",
        "ramdisk_mode": config["ramdisk_mode"],
        "header_version": 2,
        "partition_bytes": PARTITION,
        "page_bytes": page,
        "p25_sha256": hashlib.sha256(data).hexdigest(),
        "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
        "ramdisk_sha256": hashlib.sha256(ramdisk).hexdigest(),
        "dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "dtb_section_prefix_bytes": len(prefix),
        "dtb_section_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        "dtb_section_sha256": hashlib.sha256(dtb_section).hexdigest(),
        "boot_id_sha1": digest.hexdigest(),
        "not_proven": ["Air6 LK compatibility", "Air6 cold boot",
                        "proprietary signing acceptance", "kernel runtime",
                        "rights clearance", "signed firmware"],
    }
    output.with_name(output.name + ".json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for name in ("kernel", "ramdisk", "dtb", "config", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--dtb-prefix", type=Path)
    args = parser.parse_args()
    record = build(args.kernel, args.ramdisk, args.dtb, args.config,
                   args.output, args.dtb_prefix)
    print("P25_UNSIGNED_V2_MANUFACTURE_PASS", record["p25_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
