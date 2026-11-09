#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only Air6 p25/DTB acceptance preflight using PUBLIC structural facts.

Never imports an OEM header, signer or private blob. Distinguishes Android v2
structure from physical LK acceptance; unknown metadata always stays BLOCKED.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

PAGE = 2048
HEADER = 1660
PARTITION = 33_554_432
FIELDS = ("kernel_addr", "tags_addr", "dtb_addr", "os_version",
          "board", "cmdline", "extra_cmdline")
TOK_BEGIN, TOK_END_NODE, TOK_PROP, TOK_NOP, TOK_END = 1, 2, 3, 4, 9


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _word(buf, pos):
    if pos < 0 or pos + 4 > len(buf):
        raise ValueError("FDT_TRUNCATED_WORD")
    return struct.unpack_from(">I", buf, pos)[0]


def check_fdt(blob, lk_adds=()):
    """Validate sections, tree delimiters, unique phandles and LK node conflicts."""
    if len(blob) < 56 or _word(blob, 0) != 0xd00dfeed:
        raise ValueError("FDT_MAGIC")
    total, off_struct, off_str, off_reserve, version, last = struct.unpack_from(">6I", blob, 4)
    strings_len, struct_len = struct.unpack_from(">II", blob, 32)
    if (total != len(blob) or version < 16 or last > version or
        off_reserve < 40 or off_reserve >= off_struct or
        off_struct % 4 or off_reserve % 8 or
        off_struct + struct_len > total or off_str + strings_len > total or
        off_str < off_struct + struct_len):
        raise ValueError("FDT_OFFSETS")
    # Real memreserve table must end before the structure block.
    reserve_end = None
    for pos in range(off_reserve, off_struct, 16):
        if pos + 16 > off_struct:
            break
        base, size = struct.unpack_from(">QQ", blob, pos)
        if base == size == 0:
            reserve_end = pos + 16
            break
    if reserve_end is None:
        raise ValueError("FDT_MEMRESERVE_TERMINATOR")
    names = blob[off_str:off_str + strings_len]
    pos, stop = off_struct, off_struct + struct_len
    stack, paths, phandles = [], set(), {}
    # phandle and linux,phandle may legitimately alias on ONE node.
    node_handles = {}
    ended = False
    while pos < stop:
        token = _word(blob, pos)
        pos += 4
        if token == TOK_BEGIN:
            end = blob.find(b"\x00", pos, stop)
            if end < 0:
                raise ValueError("FDT_NODE_NAME")
            name = blob[pos:end].decode("ascii")
            if "/" in name or (not stack and name != ""):
                raise ValueError("FDT_NODE_PATH")
            path = (stack[-1].rstrip("/") + "/" + name) if stack else "/"
            if path in paths:
                raise ValueError("FDT_DUPLICATE_NODE")
            paths.add(path)
            stack.append(path)
            pos = (end + 4) & ~3
        elif token == TOK_END_NODE:
            if not stack:
                raise ValueError("FDT_NODE_UNDERFLOW")
            stack.pop()
        elif token == TOK_PROP:
            if not stack or pos + 8 > stop:
                raise ValueError("FDT_PROPERTY")
            size, off = struct.unpack_from(">II", blob, pos)
            pos += 8
            endname = names.find(b"\x00", off)
            if off >= len(names) or endname < 0 or pos + size > stop:
                raise ValueError("FDT_PROPERTY_BOUNDS")
            name = names[off:endname]
            if name in (b"phandle", b"linux,phandle"):
                if size != 4:
                    raise ValueError("FDT_BAD_PHANDLE")
                value = _word(blob, pos)
                if value in (0, 0xffffffff):
                    raise ValueError("FDT_PHANDLE_COLLISION")
                node = stack[-1]
                props = node_handles.setdefault(node, {})
                if name in props:
                    raise ValueError("FDT_DUPLICATE_PHANDLE_PROPERTY")
                if props and next(iter(props.values())) != value:
                    raise ValueError("FDT_PHANDLE_ALIAS_MISMATCH")
                if value in phandles and phandles[value] != node:
                    raise ValueError("FDT_PHANDLE_COLLISION")
                phandles[value] = node
                props[name] = value
            pos = (pos + size + 3) & ~3
        elif token == TOK_NOP:
            continue
        elif token == TOK_END:
            if stack or pos != stop:
                raise ValueError("FDT_EARLY_END")
            ended = True
        else:
            raise ValueError("FDT_UNKNOWN_TOKEN")
        if ended:
            break
    if not ended or not paths or "/" not in paths:
        raise ValueError("FDT_MISSING_END")
    if any(p in paths for p in lk_adds):
        raise ValueError("FDT_LK_INJECTION_COLLISION")
    return {"fdt_bytes": total, "nodes": len(paths), "phandles": len(phandles),
            "memreserve_end": reserve_end}


def check(image, metadata, section, provenance):
    """Check exact public header fields and optional vendor64+bare-DTB boundaries."""
    if len(image) != PARTITION or image[:8] != b"ANDROID!":
        raise ValueError("P25_SIZE_OR_MAGIC")
    if len(image[:PAGE]) != PAGE or any(image[HEADER:PAGE]):
        raise ValueError("P25_HEADER_PADDING")
    numbers = struct.unpack_from("<10I", image, 8)
    kernel_size, kernel_addr, ram_size, ram_addr, second_size, second_addr, tags, page, version, osver = numbers
    recovery_size, recovery_offset, hsize, dtb_size, dtb_addr = struct.unpack_from("<IQIIQ", image, 1632)
    if (page, version, hsize) != (PAGE, 2, HEADER) or (ram_size, second_size, recovery_size, recovery_offset) != (0, 0, 0, 0):
        raise ValueError("P25_LAYOUT")
    if ram_addr or second_addr or kernel_size == 0 or dtb_size == 0:
        raise ValueError("P25_SECTION_FIELDS")
    def cstring(start, length):
        buf = image[start:start + length]
        if b"\x00" not in buf:
            raise ValueError("P25_STRING_TERMINATOR")
        return buf.split(b"\x00", 1)[0].decode("ascii")
    observed = dict(kernel_addr=kernel_addr, tags_addr=tags, dtb_addr=dtb_addr,
                    os_version=osver, board=cstring(48, 16),
                    cmdline=cstring(64, 512), extra_cmdline=cstring(608, 1024))
    if set(metadata) != {"format", "metadata_provenance", "expected_header", "expected_header_page_sha256",
                         "expected_dtb_sha256", "lk_injected_nodes", "vendor64_prefix_sha256"}:
        raise ValueError("P25_PROVENANCE_SCHEMA")
    if metadata["format"] != "public-air6-p25-contract-v1":
        raise ValueError("P25_METADATA_FORMAT")
    if metadata["metadata_provenance"] not in ("synthetic-research-only", "owner-reviewed-public-metadata"):
        raise ValueError("P25_METADATA_PROVENANCE")
    if set(metadata["expected_header"]) != set(FIELDS) or metadata["expected_header"] != observed:
        raise ValueError("P25_HEADER_MISMATCH")
    expected = metadata["expected_header_page_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or sha(image[:PAGE]) != expected:
        raise ValueError("P25_HEADER_SHA")
    dtb_at = ((PAGE + kernel_size + PAGE - 1) // PAGE) * PAGE
    if dtb_at + dtb_size > PARTITION:
        raise ValueError("P25_OVERFLOW")
    if any(image[PAGE + kernel_size:dtb_at]):
        raise ValueError("P25_KERNEL_DTB_PADDING")
    if section is None:
        raise ValueError("P25_DTB_INPUT_REQUIRED")
    raw = section
    prefix_sha = metadata["vendor64_prefix_sha256"]
    if prefix_sha is None:
        if raw[:4] != b"\xd0\x0d\xfe\xed":
            raise ValueError("P25_VENDOR64_UNREVIEWED")
        fdt = raw
    else:
        if not re.fullmatch(r"[0-9a-f]{64}", prefix_sha) or len(raw) <= 64 or sha(raw[:64]) != prefix_sha:
            raise ValueError("P25_VENDOR64_IDENTITY")
        fdt = raw[64:]
    if not re.fullmatch(r"[0-9a-f]{64}", metadata["expected_dtb_sha256"]) or sha(raw) != metadata["expected_dtb_sha256"]:
        raise ValueError("P25_DTB_SHA")
    if len(raw) != dtb_size or image[dtb_at:dtb_at + dtb_size] != raw:
        raise ValueError("P25_DTB_BYTES")
    result = check_fdt(fdt, metadata["lk_injected_nodes"])
    if not isinstance(provenance, dict) or provenance.get("source") not in (
        "independently-observed-public", "synthetic-fixture"):
        raise ValueError("P25_OBSERVATION_REQUIRED")
    if provenance.get("source") == "independently-observed-public":
        if not isinstance(provenance.get("source_locator"), str) or not provenance["source_locator"]:
            raise ValueError("P25_SOURCE_LOCATOR_REQUIRED")
    # No header-only / synthetic success may mean that LK is proven.
    result.update(status="STRUCTURAL_ONLY_LK_UNVERIFIED",
                  sign_ready=False, lk_runtime_accepted=False,
                  device_boot_proven=False)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--p25", type=Path, required=True)
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--dtb-section", type=Path, required=True)
    ap.add_argument("--provenance", type=Path, required=True)
    args = ap.parse_args()
    r = check(args.p25.read_bytes(), json.loads(args.metadata.read_text()),
              args.dtb_section.read_bytes(), json.loads(args.provenance.read_text()))
    print(json.dumps(r, sort_keys=True))


if __name__ == "__main__":
    main()
