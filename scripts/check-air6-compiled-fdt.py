#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate compiled Air6 FDT structure, not mere substring presence.

Source-only, noninstallable build gate. This is not a binding check or boot proof.
"""
import argparse
from pathlib import Path
import struct

MAGIC = 0xD00DFEED
BEGIN, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def parse_fdt(blob):
    if len(blob) < 40:
        raise ValueError("truncated FDT header")
    magic, total, off_struct, off_strings, off_rsv, version, last, boot, strings_len, struct_len = struct.unpack_from(">10I", blob)
    if magic != MAGIC or total != len(blob) or version < 17 or last > version:
        raise ValueError("invalid FDT header")
    if off_rsv < 40 or off_struct % 4 or off_strings % 4:
        raise ValueError("invalid FDT offsets")
    if off_struct + struct_len > total or off_strings + strings_len > total:
        raise ValueError("FDT block out of bounds")
    # Reject overlapping blocks and an unterminated memory reservation map.\n    blocks = [(off_struct, off_struct + struct_len),\n              (off_strings, off_strings + strings_len)]\n    if any(start < 40 or end < start for start, end in blocks):\n        raise ValueError("invalid FDT block extent")\n    if max(blocks[0][0], blocks[1][0]) < min(blocks[0][1], blocks[1][1]):\n        raise ValueError("overlapping FDT blocks")\n    reserve_end = min(off_struct, off_strings)\n    if off_rsv % 8 or off_rsv + 16 > reserve_end:\n        raise ValueError("invalid FDT reservation map")\n    reserve_pos = off_rsv\n    while reserve_pos + 16 <= reserve_end:\n        address, size = struct.unpack_from(">QQ", blob, reserve_pos)\n        reserve_pos += 16\n        if address == 0 and size == 0:\n            break\n    else:\n        raise ValueError("unterminated FDT reservation map")\n    strings = blob[off_strings:off_strings + strings_len]
    pos, stop = off_struct, off_struct + struct_len
    stack, nodes, properties = [], set(), {}
    root_seen = False
    ended = False
    while pos + 4 <= stop:
        token = struct.unpack_from(">I", blob, pos)[0]
        pos += 4
        if token == BEGIN:
            end = blob.find(b"\0", pos, stop)
            if end < 0:
                raise ValueError("unterminated node")
            name = blob[pos:end].decode("ascii")
            if "/" in name:
                raise ValueError("invalid node name")
            pos = (end + 4) & ~3
            if not stack:
                if name != "" or root_seen:
                    raise ValueError("invalid or repeated root")
                root_seen = True
            path = (stack[-1] if stack else "") + "/" + name
            if path in nodes:
                raise ValueError("duplicate node " + path)
            nodes.add(path)
            stack.append(path.rstrip("/"))
        elif token == END_NODE:
            if not stack:
                raise ValueError("unbalanced FDT")
            stack.pop()
        elif token == PROP:
            if not stack or pos + 8 > stop:
                raise ValueError("invalid property")
            length, nameoff = struct.unpack_from(">II", blob, pos)
            pos += 8
            if nameoff >= len(strings):
                raise ValueError("invalid property name offset")
            name_end = strings.find(b"\0", nameoff)
            if name_end < 0 or pos + length > stop:
                raise ValueError("invalid property length/name")
            name = strings[nameoff:name_end].decode("ascii")
            key = (stack[-1] or "/", name)
            if key in properties:
                raise ValueError("duplicate property " + str(key))
            properties[key] = blob[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == NOP:
            continue
        elif token == END:
            if stack:
                raise ValueError("unclosed FDT nodes")
            ended = True
            break
        else:
            raise ValueError("unknown FDT token " + str(token))
    if not ended or pos != stop or ("/", "compatible") not in properties:
        raise ValueError("missing FDT end/root compatible")
    compatibles = properties[("/", "compatible")].split(b"\0")
    if b"softbank,air-terminal-6" not in compatibles:
        raise ValueError("not Air Terminal 6")
    if not any(b"mediatek,mt7531" in value.split(b"\0")
               for (path, name), value in properties.items() if name == "compatible"):
        raise ValueError("MT7531 switch missing")
    return len(nodes), len(properties)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dtb", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.dtb:
        nodes, props = parse_fdt(path.read_bytes())
        print(f"AIR6_COMPILED_FDT_STRUCTURE_PASS {path} nodes={nodes} properties={props}")


if __name__ == "__main__":
    main()
