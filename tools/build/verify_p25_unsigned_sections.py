#!/usr/bin/env python3
"""Independent unsigned p25 byte/section readback (not a boot-v2 parser).

Manifest is produced independently of the image writer, from a reviewed
boot-v2 layout. No signing, firmware extraction or device access.
"""
import argparse
import hashlib
import json
from pathlib import Path

SIZE = 32 * 1024 * 1024
CHUNK = 1024 * 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while data := stream.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def verify(image, manifest):
    image = Path(image)
    if image.stat().st_size != SIZE:
        raise ValueError("P25_SIZE_MISMATCH")
    if sha256_file(image) != manifest["image_sha256"]:
        raise ValueError("P25_FULL_SHA_MISMATCH")
    sections = sorted(manifest["sections"], key=lambda s: s["offset"])
    if not sections:
        raise ValueError("P25_NO_SECTIONS")
    end = 0
    with image.open("rb") as stream:
        for section in sections:
            offset, length = section["offset"], section["length"]
            if not isinstance(offset, int) or not isinstance(length, int):
                raise ValueError("P25_INVALID_RANGE")
            if offset < end or length <= 0 or offset + length > SIZE:
                raise ValueError("P25_SECTION_RANGE")
            stream.seek(end)
            remaining = offset - end
            while remaining:
                block = stream.read(min(CHUNK, remaining))
                if len(block) == 0 or any(block):
                    raise ValueError("P25_NONZERO_GAP")
                remaining -= len(block)
            stream.seek(offset)
            digest = hashlib.sha256()
            remaining = length
            while remaining:
                block = stream.read(min(CHUNK, remaining))
                if len(block) == 0:
                    raise ValueError("P25_TRUNCATED_SECTION")
                digest.update(block)
                remaining -= len(block)
            if digest.hexdigest() != section["sha256"]:
                raise ValueError("P25_SECTION_SHA_MISMATCH")
            end = offset + length
        stream.seek(end)
        while block := stream.read(CHUNK):
            if any(block):
                raise ValueError("P25_NONZERO_PADDING")
    return {"size": SIZE, "sha256": manifest["image_sha256"],
            "sections_verified": len(sections), "zero_gaps_padding": True,
            "boot_v2_semantics": "NOT_VERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("manifest", help="JSON with image_sha256 and sections")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    print(json.dumps(verify(args.image, manifest), sort_keys=True))


if __name__ == "__main__":
    main()
