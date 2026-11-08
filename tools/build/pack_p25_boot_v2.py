#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build real 32MiB Android boot v2 research candidates from public inputs.

Independently implemented from published AOSP boot image header v2 fields.
No Air6 LK addresses, vendor64 DTB wrapper, signer, flash or release approval
is inferred. Synthetic header metadata yields a NONBOOTABLE research candidate.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct

PARTITION = 33_554_432
HEADER_SIZE = 1660
PAGE = 2048


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as src:
        for data in iter(lambda: src.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def validate_inputs(kernel, dtb):
    for path in (kernel, dtb):
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError("inputs must be regular nonempty non-symlink files")
    with kernel.open("rb") as src:
        if src.read(2) != b"\x1f\x8b":
            raise ValueError("kernel must be Image.gz, not uncompressed Image")
    with gzip.open(kernel, "rb") as src:
        header = src.read(64)
        if len(header) != 64 or header[56:60] != b"ARM\x64":
            raise ValueError("gzip payload is not an ARM64 Linux Image")
        while src.read(1 << 20):
            pass
    with dtb.open("rb") as src:
        d = src.read(40)
        if len(d) != 40 or d[:4] != b"\xd0\x0d\xfe\xed":
            raise ValueError("bad FDT header")
        size, off_struct, off_strings, off_resv = struct.unpack_from(">IIII", d, 4)
        if size != dtb.stat().st_size or not (40 <= off_resv < size):
            raise ValueError("bad FDT length / reserve offset")
        sizes = struct.unpack_from(">II", d, 32)
        if any(off > size or n > size - off for off, n in
               ((off_struct, sizes[1]), (off_strings, sizes[0]))):
            raise ValueError("invalid FDT block")


def build(kernel, dtb, metadata, output, receipt):
    kernel, dtb, metadata = map(Path, (kernel, dtb, metadata))
    output, receipt = Path(output), Path(receipt)
    if output == receipt or output.exists() or receipt.exists() or output.is_symlink() or receipt.is_symlink():
        raise ValueError("outputs must be new and distinct")
    validate_inputs(kernel, dtb)
    cfg = json.loads(metadata.read_text())
    if cfg.get("format") != "aosp-boot-v2-metadata-v1":
        raise ValueError("unrecognized header metadata")
    if cfg.get("metadata_provenance") not in ("synthetic-research-only", "owner-reviewed-public-metadata"):
        raise ValueError("explicit header metadata provenance required")
    if cfg.get("page_size") != PAGE:
        raise ValueError("this Air6 research pipeline requires 2048-byte pages")
    fields = {}
    for key in ("kernel_addr", "tags_addr", "dtb_addr", "os_version"):
        v = cfg.get(key)
        if type(v) is not int or not 0 <= v <= (0xffffffffffffffff if key == "dtb_addr" else 0xffffffff):
            raise ValueError("missing or invalid header field: " + key)
        fields[key] = v
    board, cmdline = cfg.get("board"), cfg.get("cmdline")
    extra_cmdline = cfg.get("extra_cmdline", "")
    if not isinstance(extra_cmdline, str) or len(extra_cmdline.encode("ascii")) >= 1024:
        raise ValueError("extra cmdline must be ASCII and shorter than 1024 bytes")
    if cfg["metadata_provenance"] == "owner-reviewed-public-metadata":
        source = cfg.get("public_observation_source")
        if not isinstance(source, str) or not source.startswith("https://"):
            raise ValueError("reviewed metadata requires a public observation source")
    # Source locator and field values remain unverified until LK/device testing.
    if not isinstance(board, str) or len(board.encode("ascii")) >= 16:
        raise ValueError("board must be ASCII and shorter than 16 bytes")
    if not isinstance(cmdline, str) or len(cmdline.encode("ascii")) >= 512:
        raise ValueError("cmdline must be ASCII and shorter than 512 bytes")
    ksize, dsize = kernel.stat().st_size, dtb.stat().st_size
    koff = PAGE
    doff = (koff + ksize + PAGE - 1) // PAGE * PAGE
    end = (doff + dsize + PAGE - 1) // PAGE * PAGE
    if end > PARTITION:
        raise ValueError("P25_CAPACITY_EXCEEDED: compressed kernel + DTB > 32MiB")
    sha1 = hashlib.sha1(usedforsecurity=False)
    for path, size in ((kernel, ksize), (None, 0), (None, 0), (None, 0), (dtb, dsize)):
        if path:
            with path.open("rb") as src:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    sha1.update(chunk)
        sha1.update(struct.pack("<I", size))
    header = bytearray(HEADER_SIZE)
    header[:8] = b"ANDROID!"
    struct.pack_into("<10I", header, 8, ksize, fields["kernel_addr"], 0, 0,
                     0, 0, fields["tags_addr"], PAGE, 2, fields["os_version"])
    header[48:64] = board.encode("ascii").ljust(16, b"\x00")
    header[64:576] = cmdline.encode("ascii").ljust(512, b"\x00")
    header[576:608] = sha1.digest().ljust(32, b"\x00")
    header[608:1632] = extra_cmdline.encode("ascii").ljust(1024, b"\x00")
    struct.pack_into("<IQIIQ", header, 1632, 0, 0, HEADER_SIZE, dsize, fields["dtb_addr"])
    created = False
    try:
        with output.open("xb") as dst:
            created = True
            dst.truncate(PARTITION)
            dst.write(header)
            for offset, path in ((koff, kernel), (doff, dtb)):
                dst.seek(offset)
                with path.open("rb") as src:
                    for chunk in iter(lambda: src.read(1 << 20), b""):
                        dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        record = {
            "format": "aosp-boot-v2-p25-research-receipt-v1",
            "status": "REAL_32M_BYTES_AOSP_V2_STRUCTURE_ONLY_NOT_LK_ACCEPTED",
            "metadata_provenance": cfg["metadata_provenance"],
            "header_fields": {"kernel_addr": fields["kernel_addr"],
                "tags_addr": fields["tags_addr"], "dtb_addr": fields["dtb_addr"],
                "os_version": fields["os_version"], "board": board,
                "cmdline": cmdline, "extra_cmdline": extra_cmdline},
            "partition_bytes": PARTITION, "header_bytes": HEADER_SIZE,
            "page_size": PAGE, "kernel": {"offset": koff, "bytes": ksize,
                "sha256": file_sha(kernel)},
            "dtb": {"offset": doff, "bytes": dsize, "sha256": file_sha(dtb)},
            "body_end": end, "zero_tail_bytes": PARTITION - end,
            "android_image_id_sha1": sha1.hexdigest(),
            "p25_sha256": file_sha(output),
            "lk_header_and_vendor64_accepted": False, "signed": False,
            "device_boot_proven": False, "distributable": False,
        }
        with receipt.open("xb") as dst:
            dst.write((json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
            dst.flush()
            os.fsync(dst.fileno())
        return record
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("kernel", "dtb", "metadata", "output", "receipt"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    record = build(a.kernel, a.dtb, a.metadata, a.output, a.receipt)
    print("PUBLIC_AOSP_V2_P25_32M_RESEARCH_IMAGE_SHA256", record["p25_sha256"])
    print("LIMIT: not Air6 LK acceptance, unsigned, unapproved for distribution")


if __name__ == "__main__":
    main()
