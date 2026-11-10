#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the exact first-stage CPIO is linked into an ARM64 kernel image."""
import argparse
import gzip
import hashlib
import lzma
from pathlib import Path
import struct

ELF64_SHDR = struct.Struct("<IIQQQQIIQQ")
ELF64_SYM = struct.Struct("<IBBHQQ")
SHF_ALLOC = 0x2
SHT_NOBITS = 8
SHT_SYMTAB = 2


def require(ok, code):
    if not ok:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_" + code)


def elf_sections(data):
    require(len(data) >= 64 and data[:4] == b"\x7fELF", "ELF_MAGIC")
    require(data[4] == 2 and data[5] == 1, "ELF64_LITTLE_ENDIAN")
    require(struct.unpack_from("<H", data, 18)[0] == 183, "ELF_NOT_AARCH64")
    shoff = struct.unpack_from("<Q", data, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 58)
    require(shentsize >= ELF64_SHDR.size and shnum > 1 and
            shstrndx < shnum, "ELF_SECTION_TABLE")
    require(shoff + shentsize * shnum <= len(data), "ELF_SECTION_BOUNDS")
    headers = [ELF64_SHDR.unpack_from(data, shoff + i * shentsize)
               for i in range(shnum)]
    shstr = headers[shstrndx]
    names_off, names_size = shstr[4], shstr[5]
    require(names_off + names_size <= len(data), "ELF_NAMES_BOUNDS")
    names = data[names_off:names_off + names_size]
    result = []
    for index, header in enumerate(headers):
        nameoff, stype, flags, addr, offset, size, link, info, align, entsize = header
        require(nameoff < len(names), "ELF_SECTION_NAME")
        end = names.find(b"\0", nameoff)
        require(end >= 0, "ELF_SECTION_NAME_TERMINATOR")
        require(stype == SHT_NOBITS or offset + size <= len(data),
                "ELF_SECTION_BOUNDS")
        result.append({"index": index, "name": names[nameoff:end].decode("ascii"),
                       "type": stype, "flags": flags, "addr": addr,
                       "offset": offset, "size": size, "link": link,
                       "entsize": entsize})
    return result


def section(data, wanted):
    matches = [data[item["offset"]:item["offset"] + item["size"]]
               for item in elf_sections(data) if item["name"] == wanted]
    require(len(matches) == 1, "ELF_TARGET_SECTION_COUNT")
    return matches[0]


def symbol_table(data, sections, wanted):
    matches = []
    for symtab in sections:
        if symtab["type"] != SHT_SYMTAB:
            continue
        require(symtab["link"] < len(sections), "ELF_SYMBOL_STRTAB")
        strings_section = sections[symtab["link"]]
        strings = data[strings_section["offset"]:
                       strings_section["offset"] + strings_section["size"]]
        entsize = symtab["entsize"] or ELF64_SYM.size
        require(entsize >= ELF64_SYM.size and symtab["size"] % entsize == 0,
                "ELF_SYMBOL_TABLE_BOUNDS")
        start = symtab["offset"]
        for offset in range(start, start + symtab["size"], entsize):
            nameoff, info, other, shndx, value, size = ELF64_SYM.unpack_from(data, offset)
            if nameoff >= len(strings):
                continue
            end = strings.find(b"\0", nameoff)
            require(end >= 0, "ELF_SYMBOL_NAME")
            if strings[nameoff:end].decode("ascii", "replace") == wanted and shndx != 0:
                matches.append({"value": value, "size": size, "shndx": shndx})
    require(len(matches) == 1, "ELF_SYMBOL_COUNT_" + wanted.upper())
    return matches[0]


def linked_initramfs(data):
    """Extract .init.ramfs input bytes from the final linker output section.

    Linux keeps the input .init.ramfs section inside the output .init.data
    section. The linker symbol __initramfs_start marks its first byte and the
    64-bit __initramfs_size object records its exact length.
    """
    sections = elf_sections(data)
    start = symbol_table(data, sections, "__initramfs_start")
    size_symbol = symbol_table(data, sections, "__initramfs_size")
    require(start["size"] == 0, "ELF_INITRAMFS_START_SYMBOL_SIZE")
    # GNU ld may retain the assembly symbol as STT_NOTYPE with st_size=0,
    # even though the symbol points at the eight-byte .quad payload. Validate
    # the payload by its containing allocated section and read exactly 8 bytes
    # at the symbol value instead of relying on st_size metadata.
    require(size_symbol["size"] in (0, 8), "ELF_INITRAMFS_SIZE_SYMBOL_SIZE")
    containing_start = [s for s in sections if s["flags"] & SHF_ALLOC and
                        s["type"] != SHT_NOBITS and s["addr"] <= start["value"] <
                        s["addr"] + s["size"]]
    require(len(containing_start) == 1, "ELF_INITRAMFS_START_MAPPING")
    section_start = containing_start[0]
    require(section_start["name"] == ".init.data" and
            start["shndx"] == section_start["index"],
            "ELF_INITRAMFS_OUTPUT_SECTION")
    start_offset = section_start["offset"] + start["value"] - section_start["addr"]
    size_offset = size_symbol["value"]
    size_owner = [s for s in sections if s["flags"] & SHF_ALLOC and
                  s["type"] != SHT_NOBITS and s["addr"] <= size_offset and
                  size_offset + 8 <= s["addr"] + s["size"]]
    require(len(size_owner) == 1 and size_owner[0]["index"] == section_start["index"] and
            size_symbol["shndx"] == section_start["index"],
            "ELF_INITRAMFS_SIZE_MAPPING")
    length = struct.unpack_from("<Q", data,
                                size_owner[0]["offset"] + size_offset - size_owner[0]["addr"])[0]
    require(length > 0 and start_offset + length <=
            section_start["offset"] + section_start["size"],
            "ELF_INITRAMFS_LINKED_BOUNDS")
    return data[start_offset:start_offset + length]


def verify(obj, vmlinux, image, kernel_gz, cpio, compression="xz"):
    paths = (obj, vmlinux, image, kernel_gz, cpio)
    require(all(p.is_file() and not p.is_symlink() for p in paths), "INPUT")
    object_data = section(obj.read_bytes(), ".init.ramfs")
    linked_data = linked_initramfs(vmlinux.read_bytes())
    require(object_data and object_data == linked_data, "OBJECT_NOT_LINKED")
    if compression == "xz":
        try:
            decoded = lzma.decompress(object_data)
        except lzma.LZMAError as exc:
            raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_XZ_DECODE") from exc
    elif compression == "none":
        decoded = object_data
    else:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_UNSUPPORTED_COMPRESSION")
    cpio_data = cpio.read_bytes()
    require(decoded == cpio_data, "CPIO_CONTENT_MISMATCH")
    raw_image = image.read_bytes()
    require(len(raw_image) >= 64 and raw_image[56:60] == b"ARM\x64",
            "IMAGE_NOT_ARM64")
    require(raw_image.count(object_data) == 1, "INITRAMFS_NOT_UNIQUE_IN_IMAGE")
    try:
        decompressed_kernel = gzip.decompress(kernel_gz.read_bytes())
    except (OSError, EOFError) as exc:
        raise ValueError("INITRAMFS_LINK_VERIFY_FAIL_KERNEL_GZIP") from exc
    require(decompressed_kernel == raw_image, "KERNEL_GZIP_IMAGE_MISMATCH")
    return {
        "status": "ARM64_KERNEL_INITRAMFS_OBJECT_AND_IMAGE_VERIFIED",
        "cpio_bytes": len(cpio_data),
        "cpio_sha256": hashlib.sha256(cpio_data).hexdigest(),
        "compressed_initramfs_bytes": len(object_data),
        "compressed_initramfs_sha256": hashlib.sha256(object_data).hexdigest(),
        "kernel_image_sha256": hashlib.sha256(raw_image).hexdigest(),
        "kernel_gzip_sha256": hashlib.sha256(kernel_gz.read_bytes()).hexdigest(),
        "compression": compression,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("object", "vmlinux", "image", "kernel-gz", "cpio"):
        ap.add_argument("--" + name, required=True, type=Path)
    ap.add_argument("--compression", choices=("xz", "none"), default="xz")
    a = ap.parse_args()
    result = verify(a.object, a.vmlinux, a.image, a.kernel_gz, a.cpio,
                    a.compression)
    print("PUBLIC_P25_KERNEL_BUILTIN_INITRAMFS_VERIFY_PASS", result)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, struct.error) as exc:
        raise SystemExit(str(exc))
