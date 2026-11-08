#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect real ARM64 Image and flattened DTB inputs before p25 layout assembly.

This validates public container structures, NOT the proprietary boot-v2 envelope,
LK acceptance, a device-specific DTB identity, or bootability.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ARM64_MAGIC = 0x644d5241
FDT_MAGIC = 0xd00dfeed

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def inspect(image, dtb):
    image, dtb = Path(image), Path(dtb)
    for path in (image, dtb):
        if path.is_symlink() or not path.is_file():
            raise ValueError("regular non-symlink input required")
    with image.open("rb") as stream:
        header = stream.read(64)
    if len(header) < 64 or struct.unpack_from("<I", header, 56)[0] != ARM64_MAGIC:
        raise ValueError("ARM64 Image header magic mismatch")
    text_offset, image_size = struct.unpack_from("<QQ", header, 8)
    flags = struct.unpack_from("<Q", header, 24)[0]
    if image_size and image_size > image.stat().st_size:
        raise ValueError("ARM64 Image declared size exceeds file")
    with dtb.open("rb") as stream:
        header = stream.read(40)
    if len(header) < 40:
        raise ValueError("truncated FDT header")
    magic, total, off_struct, off_strings, off_rsv, version, last_comp, bootcpu, strings_size, struct_size = struct.unpack(">10I", header)
    if magic != FDT_MAGIC or total != dtb.stat().st_size or total < 40:
        raise ValueError("FDT magic or totalsize mismatch")
    if version < 16 or last_comp > version:
        raise ValueError("unsupported FDT version")
    if off_rsv < 40 or off_rsv >= total:
        raise ValueError("invalid FDT reserve map offset")
    if any(offset < 40 or offset > total or size > total - offset
           for offset, size in ((off_struct, struct_size), (off_strings, strings_size))):
        raise ValueError("FDT block out of bounds")
    return {
        "format": "p25-public-payload-input-inspection-v1",
        "status": "PAYLOAD_HEADERS_ONLY_BOOT_V2_UNVERIFIED",
        "image": {"bytes": image.stat().st_size, "sha256": digest(image),
                  "text_offset": text_offset, "declared_image_size": image_size,
                  "flags": flags},
        "dtb": {"bytes": total, "sha256": digest(dtb),
                "fdt_version": version, "boot_cpuid_phys": bootcpu},
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--dtb", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.image, args.dtb), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
