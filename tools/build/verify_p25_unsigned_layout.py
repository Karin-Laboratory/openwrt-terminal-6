#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent byte-level unsigned p25 layout readback, not boot-v2 validation."""
import argparse
import hashlib
import json
from pathlib import Path

SIZE = 33_554_432

def verify(image, receipt):
    spec = json.loads(Path(receipt).read_text())
    if spec.get("format") != "unsigned-p25-layout-v1" or spec.get("partition_bytes") != SIZE:
        raise ValueError("unrecognized unsigned p25 receipt")
    if spec.get("boot_v2_verified") is not False or spec.get("status") != "LAYOUT_CANDIDATE_ONLY_NOT_BOOTABLE":
        raise ValueError("receipt must explicitly deny boot-v2 verification")
    image = Path(image)
    if image.is_symlink() or not image.is_file() or image.stat().st_size != SIZE:
        raise ValueError("p25 image must be a regular 32MiB file")
    segments = spec.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("missing segment evidence")
    spans = []
    for segment in segments:
        start, length, digest = segment["offset"], segment["length"], segment["sha256"]
        if (type(start) is not int or type(length) is not int or start < 0 or
                length <= 0 or start + length > SIZE or
                not isinstance(digest, str) or len(digest) != 64 or
                any(ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError("invalid segment evidence")
        spans.append((start, start + length, digest))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError("overlapping segments")
    full = hashlib.sha256()
    with image.open("rb") as stream:
        offset = 0
        for start, end, expected in spans:
            while offset < start:
                chunk = stream.read(min(1 << 20, start - offset))
                if not chunk or any(chunk):
                    raise ValueError("nonzero unaccounted bytes")
                full.update(chunk)
                offset += len(chunk)
            digest = hashlib.sha256()
            while offset < end:
                chunk = stream.read(min(1 << 20, end - offset))
                if not chunk:
                    raise ValueError("truncated segment")
                full.update(chunk)
                digest.update(chunk)
                offset += len(chunk)
            if digest.hexdigest() != expected:
                raise ValueError("segment hash mismatch")
        while chunk := stream.read(1 << 20):
            if any(chunk):
                raise ValueError("nonzero trailing padding")
            full.update(chunk)
    if full.hexdigest() != spec.get("p25_sha256"):
        raise ValueError("full image hash mismatch")
    return full.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p25", type=Path, required=True)
    parser.add_argument("--layout-receipt", type=Path, required=True)
    args = parser.parse_args()
    print("P25_LAYOUT_BYTE_READBACK_PASS", verify(args.p25, args.layout_receipt))
    print("LIMIT: LK boot-v2 semantics, rights, signature and hardware boot unverified")

if __name__ == "__main__":
    main()
