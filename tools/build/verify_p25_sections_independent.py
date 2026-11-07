#!/usr/bin/env python3
"""Independent, read-only p25 section/full-image verifier.

The manifest is emitted by a *separate* boot-v2 assembler. This tool does not
assert boot-v2 validity: the header parser and signature boundary remain
independent acceptance gates. No signing, device access or binary publication.
"""
import argparse
import hashlib
import json
from pathlib import Path

P25_SIZE = 32 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(image_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("format") != "air6-p25-unsigned-sections-v1":
        raise ValueError("unknown manifest format")
    if manifest.get("image_size") != P25_SIZE:
        raise ValueError("wrong declared image size")
    image = Path(image_path)
    if image.is_symlink() or not image.is_file() or image.stat().st_size != P25_SIZE:
        raise ValueError("p25 must be exactly 32 MiB")
    sections = manifest.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("no sections")
    ranges = []
    with image.open("rb") as stream:
        full = hashlib.sha256()
        while chunk := stream.read(1024 * 1024):
            full.update(chunk)
        if full.hexdigest() != manifest.get("sha256"):
            raise ValueError("full image SHA mismatch")
        for section in sections:
            name, start, length = section["name"], section["offset"], section["length"]
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(length, int) or isinstance(length, bool):
                raise ValueError("noninteger section range")
            if start < 0 or length <= 0 or start + length > P25_SIZE:
                raise ValueError("invalid section range")
            ranges.append((start, start + length, name))
            stream.seek(start)
            if digest(stream.read(length)) != section["sha256"]:
                raise ValueError("section SHA mismatch: " + name)
        ranges.sort()
        if ranges[0][0] != 0:
            raise ValueError("unaccounted prefix")
        for previous, current in zip(ranges, ranges[1:]):
            if previous[1] > current[0]:
                raise ValueError("overlapping sections")
            if previous[1] < current[0]:
                stream.seek(previous[1])
                remaining = current[0] - previous[1]
                while remaining:
                    block = stream.read(min(1024 * 1024, remaining))
                    if not block or any(block):
                        raise ValueError("nonzero unaccounted gap")
                    remaining -= len(block)
        if manifest.get("zero_padding_from") is None:
            # Every byte outside declared sections must be zero, including the tail.
            tail_start = ranges[-1][1]
            stream.seek(tail_start)
            while block := stream.read(1024 * 1024):
                if any(block):
                    raise ValueError("nonzero unaccounted trailing bytes")
        if manifest.get("zero_padding_from") is not None:
            pad = manifest["zero_padding_from"]
            if not isinstance(pad, int) or isinstance(pad, bool) or not (0 <= pad <= P25_SIZE):
                raise ValueError("invalid padding offset")
            if any(end > pad for _, end, _ in ranges):
                raise ValueError("section overlaps padding")
            if ranges[-1][1] != pad:
                raise ValueError("unaccounted gap before padding")
            stream.seek(pad)
            while block := stream.read(1024 * 1024):
                if any(block):
                    raise ValueError("nonzero padding")
    return {"bytes": P25_SIZE, "sha256": full.hexdigest(), "sections": len(sections),
            "section_hashes": "PASS", "padding": "PASS" if manifest.get("zero_padding_from") is not None else "NOT_CHECKED",
            "boot_v2_header": "NOT_CHECKED", "signature": "NOT_CHECKED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("manifest")
    args = parser.parse_args()
    print(json.dumps(verify(args.image, args.manifest), sort_keys=True))
