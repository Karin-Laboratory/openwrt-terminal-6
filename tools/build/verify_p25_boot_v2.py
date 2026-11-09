#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent readback of real 32MiB AOSP boot-v2 research image bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SIZE = 33_554_432
PAGE = 2048


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify(image, receipt, kernel, dtb):
    image, receipt, kernel, dtb = map(Path, (image, receipt, kernel, dtb))
    for path in (image, receipt, kernel, dtb):
        if path.is_symlink() or not path.is_file():
            raise ValueError("regular non-symlink inputs required")
    record = json.loads(receipt.read_text())
    if record.get("format") != "aosp-boot-v2-p25-research-receipt-v1":
        raise ValueError("incorrect receipt")
    if record.get("status") != "REAL_32M_BYTES_AOSP_V2_STRUCTURE_ONLY_NOT_LK_ACCEPTED":
        raise ValueError("unverified LK status required")
    if any(record.get(k) is not False for k in
           ("lk_header_and_vendor64_accepted", "signed", "device_boot_proven", "distributable")):
        raise ValueError("misleading acceptance claim")
    if image.stat().st_size != SIZE or record.get("partition_bytes") != SIZE:
        raise ValueError("wrong p25 length")
    if record.get("header_bytes") != 1660 or record.get("page_size") != PAGE:
        raise ValueError("bad header metadata")
    if sha256(image) != record.get("p25_sha256"):
        raise ValueError("full 32MiB SHA mismatch")
    with image.open("rb") as src:
        page = src.read(PAGE)
        if page[:8] != b"ANDROID!" or any(page[1660:]):
            raise ValueError("invalid AOSP header or padding")
        ksize, kaddr, rsize, raddr, ssize, saddr, tags, pagesize, version, osver = struct.unpack_from("<10I", page, 8)
        ro_size, ro_offset, hsize, dsize, daddr = struct.unpack_from("<IQIIQ", page, 1632)
        if (pagesize, version, hsize) != (PAGE, 2, 1660) or (rsize, ssize, ro_size, ro_offset) != (0, 0, 0, 0):
            raise ValueError("not expected AOSP v2 zero-optional-section header")
        if raddr or saddr:
            raise ValueError("nonzero address for absent payload")
        def ascii_field(offset, width):
            field = page[offset:offset + width]
            if b"\x00" not in field:
                raise ValueError("unterminated boot-v2 header string")
            value, padding = field.split(b"\x00", 1)
            if any(padding):
                raise ValueError("nonzero boot-v2 string padding")
            return value.decode("ascii")
        actual_header = {"kernel_addr": kaddr, "tags_addr": tags,
                         "dtb_addr": daddr, "os_version": osver,
                         "board": ascii_field(48, 16),
                         "cmdline": ascii_field(64, 512),
                         "extra_cmdline": ascii_field(608, 1024)}
        if actual_header != record.get("header_fields"):
            raise ValueError("boot-v2 header metadata independent mismatch")
        sections = [("kernel", kernel, PAGE, ksize),
                    ("dtb", dtb, (PAGE + ksize + PAGE - 1) // PAGE * PAGE, dsize)]
        # Verify page-alignment padding independently of the receipt digest.
        gap_start = PAGE + ksize
        gap_end = sections[1][2]
        src.seek(gap_start)
        if any(src.read(gap_end - gap_start)):
            raise ValueError("nonzero kernel-to-DTB alignment padding")
        image_id = hashlib.sha1(usedforsecurity=False)
        for label, path, offset, expected in sections:
            sect = record.get(label, {})
            if (expected != path.stat().st_size or sect.get("offset") != offset or
                sect.get("bytes") != expected or sect.get("sha256") != sha256(path)):
                raise ValueError("mismatched " + label + " receipt/input")
            src.seek(offset)
            with path.open("rb") as original:
                remaining = expected
                while remaining:
                    a, b = src.read(min(1 << 20, remaining)), original.read(min(1 << 20, remaining))
                    if not a or a != b:
                        raise ValueError("independent section byte mismatch: " + label)
                    remaining -= len(a)
        with kernel.open("rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                image_id.update(b)
        image_id.update(struct.pack("<I", ksize))
        image_id.update(struct.pack("<III", 0, 0, 0))
        with dtb.open("rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                image_id.update(b)
        image_id.update(struct.pack("<I", dsize))
        if page[576:608] != image_id.digest().ljust(32, b"\x00") or record.get("android_image_id_sha1") != image_id.hexdigest():
            raise ValueError("AOSP image ID mismatch")
        end = (sections[-1][2] + dsize + PAGE - 1) // PAGE * PAGE
        if end != record.get("body_end") or SIZE - end != record.get("zero_tail_bytes"):
            raise ValueError("body boundary mismatch")
        src.seek(end)
        while chunk := src.read(1 << 20):
            if any(chunk):
                raise ValueError("nonzero unaccounted tail")
    return record["p25_sha256"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("p25", "receipt", "kernel", "dtb"):
        p.add_argument("--" + name, required=True, type=Path)
    a = p.parse_args()
    print("PUBLIC_AOSP_V2_P25_32M_INDEPENDENT_READBACK_PASS",
          verify(a.p25, a.receipt, a.kernel, a.dtb))
    print("LIMIT: LK vendor64/header semantics not proven; no device boot/signing/release")


if __name__ == "__main__":
    main()
