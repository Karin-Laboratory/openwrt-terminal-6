#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build unsigned Android boot-header-v2 p25 from independently supplied public inputs.

Uses the public Android boot image v2 data layout. No signing, flashing, device IO,
OEM payloads or private address constants. All target load addresses are explicit.
"""
import argparse
import gzip
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
import struct

PARTITION = 32 * 1024 * 1024
PAGE = 4096
HDR_V2_SIZE = 1660
MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
MAX_KERNEL_UNCOMPRESSED = 64 * 1024 * 1024


def require(condition, name):
    if not condition:
        raise ValueError("P25_BLOCKED_" + name)


def read_regular(path):
    require(path.is_file() and not path.is_symlink(), "NONREGULAR_INPUT")
    return path.read_bytes()


def align(data):
    return data + bytes((-len(data)) % PAGE)


def parse_addr(value):
    number = int(value, 0)
    require(0 < number < 2 ** 32 and number % 4 == 0, "LOAD_ADDRESS")
    return number


def build(kernel_path, ramdisk_path, dtb_path, cfg_path, output):
    require(not output.exists() and not output.is_symlink(), "OUTPUT_EXISTS")
    require(not output.parent.is_symlink(), "OUTPUT_PARENT_SYMLINK")
    receipt_path = output.with_name(output.name + ".json")
    require(not receipt_path.exists() and not receipt_path.is_symlink(), "RECEIPT_EXISTS")
    kernel = read_regular(kernel_path)
    ramdisk = read_regular(ramdisk_path)
    dtb = read_regular(dtb_path)
    config = json.loads(read_regular(cfg_path))
    require(set(config) == {"kernel_addr", "ramdisk_addr", "tags_addr", "dtb_addr",
                            "name", "cmdline"}, "CONFIG_KEYS")
    require(0 < len(kernel) < PARTITION and kernel[:2] == b"\x1f\x8b",
            "KERNEL_GZIP_REQUIRED")
    try:
        with gzip.GzipFile(fileobj=BytesIO(kernel)) as stream:
            uncompressed = stream.read(MAX_KERNEL_UNCOMPRESSED + 1)
        require(len(uncompressed) <= MAX_KERNEL_UNCOMPRESSED, "KERNEL_UNCOMPRESSED_TOO_LARGE")
    except (OSError, EOFError) as exc:
        raise ValueError("P25_BLOCKED_KERNEL_GZIP_INVALID") from exc
    require(bool(uncompressed), "EMPTY_KERNEL")
    require(bool(ramdisk), "EMPTY_RAMDISK")
    require(len(dtb) >= 40 and dtb[:4] == FDT_MAGIC, "DTB_MAGIC")
    total_dtb = struct.unpack_from(">I", dtb, 4)[0]
    require(total_dtb == len(dtb), "DTB_TOTALSIZE")
    kernel_addr = parse_addr(config["kernel_addr"])
    ramdisk_addr = parse_addr(config["ramdisk_addr"])
    tags_addr = parse_addr(config["tags_addr"])
    dtb_addr = int(config["dtb_addr"], 0)
    require(0 < dtb_addr < 2 ** 64 and dtb_addr % 4 == 0, "DTB_ADDRESS")
    name = config["name"].encode("ascii")
    cmdline = config["cmdline"].encode("ascii")
    require(len(name) <= 15 and len(cmdline) <= 1535 and b"\x00" not in name + cmdline,
            "NAME_OR_CMDLINE")
    # v2 layout includes a standard SHA-1 boot ID; never a signature.
    digest = hashlib.sha1()
    for data in (kernel, ramdisk, b"", b"", dtb):
        digest.update(data)
        digest.update(struct.pack("<I", len(data)))
    boot_id = digest.digest() + bytes(12)
    header = bytearray(HDR_V2_SIZE)
    header[:8] = MAGIC
    struct.pack_into("<10I", header, 8, len(kernel), kernel_addr,
                     len(ramdisk), ramdisk_addr, 0, 0, tags_addr, PAGE, 2, 0)
    header[48:64] = name.ljust(16, b"\x00")
    header[64:576] = cmdline[:512].ljust(512, b"\x00")
    header[576:608] = boot_id
    header[608:1632] = cmdline[512:].ljust(1024, b"\x00")
    struct.pack_into("<IQI", header, 1632, 0, 0, HDR_V2_SIZE)
    struct.pack_into("<IQ", header, 1648, len(dtb), dtb_addr)
    payload = align(header) + align(kernel) + align(ramdisk) + align(dtb)
    require(len(payload) <= PARTITION, "PARTITION_OVERFLOW")
    data = payload + bytes(PARTITION - len(payload))
    # O_EXCL makes output creation atomic against concurrent producers.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(output, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            written = handle.write(data)
            require(written == len(data), "IMAGE_SHORT_WRITE")
    except BaseException:
        # A short/failed image write must never leave a plausible P25 file.
        output.unlink(missing_ok=True)
        raise
    receipt = {
        "scope": "UNSIGNED_P25_PRE_SIGNING_ONLY", "header_version": 2,
        "partition_bytes": PARTITION, "page_bytes": PAGE,
        "p25_sha256": hashlib.sha256(data).hexdigest(),
        "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
        "ramdisk_sha256": hashlib.sha256(ramdisk).hexdigest(),
        "dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "boot_id_sha1": digest.hexdigest(),
        "not_proven": ["Air6 LK compatibility", "Air6 cold boot", "proprietary boot extensions",
                       "kernel runtime", "rights clearance", "signed firmware"]
    }
    receipt_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        receipt_flags |= os.O_NOFOLLOW
    receipt_created = False
    try:
        receipt_fd = os.open(receipt_path, receipt_flags, 0o600)
        receipt_created = True
        with os.fdopen(receipt_fd, "w", encoding="utf-8") as receipt_handle:
            receipt_handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    except BaseException:
        # Only remove files exclusively created by this invocation. A failed
        # write may otherwise leave a truncated JSON receipt behind.
        if receipt_created:
            receipt_path.unlink(missing_ok=True)
        output.unlink()
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for name in ("kernel", "ramdisk", "dtb", "config", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    record = build(args.kernel, args.ramdisk, args.dtb, args.config, args.output)
    print("P25_UNSIGNED_V2_MANUFACTURE_PASS", record["p25_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
