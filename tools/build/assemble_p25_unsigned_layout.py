#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble a 32MiB unsigned p25 *layout candidate* from pinned public inputs.

This is NOT a boot-v2 encoder. The caller must supply independently established
offsets and payload bytes; no LK header, signature or bootability is inferred.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

SIZE = 33_554_432

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()

def assemble(manifest, output, receipt):
    spec = json.loads(Path(manifest).read_text())
    if spec.get("format") != "unsigned-p25-layout-input-v1":
        raise ValueError("unsupported layout input")
    segments = spec.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments required")
    output, receipt = Path(output), Path(receipt)
    if output.exists() or receipt.exists() or output == receipt:
        raise ValueError("outputs must be new and distinct")
    spans = []
    for item in segments:
        offset, length = item.get("offset"), item.get("length")
        if type(offset) is not int or type(length) is not int or length <= 0 or offset < 0 or offset + length > SIZE:
            raise ValueError("invalid segment bounds")
        source = Path(item["path"])
        if source.is_symlink() or not source.is_file() or source.stat().st_size != length:
            raise ValueError("source size/type mismatch")
        expected = item.get("sha256")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("invalid source SHA")
        if sha256(source) != expected:
            raise ValueError("source SHA mismatch")
        spans.append((offset, offset + length, source, expected))
    spans.sort(key=lambda s: s[0])
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError("overlapping segments")
    if any(source.resolve() in (output.resolve(), receipt.resolve()) for _, _, source, _ in spans):
        raise ValueError("source/output alias")
    try:
        with output.open("xb") as dest:
            dest.truncate(SIZE)
            for start, end, source, _ in spans:
                dest.seek(start)
                with source.open("rb") as stream:
                    remaining = end - start
                    while remaining:
                        block = stream.read(min(1 << 20, remaining))
                        if not block:
                            raise ValueError("source changed during assembly")
                        dest.write(block)
                        remaining -= len(block)
            dest.flush()
            os.fsync(dest.fileno())
        record = {
            "format": "unsigned-p25-layout-v1",
            "partition_bytes": SIZE,
            "p25_sha256": sha256(output),
            "segments": [{"offset": start, "length": end-start, "sha256": digest}
                         for start, end, _, digest in spans],
            "boot_v2_verified": False,
            "status": "LAYOUT_CANDIDATE_ONLY_NOT_BOOTABLE",
        }
        receipt.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return record
    except BaseException:
        output.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    result = assemble(args.manifest, args.output, args.receipt)
    print("P25_LAYOUT_CANDIDATE_SHA256", result["p25_sha256"])
    print("BLOCKED: boot-v2 header/offset semantics and LK acceptance unverified")

if __name__ == "__main__":
    main()
