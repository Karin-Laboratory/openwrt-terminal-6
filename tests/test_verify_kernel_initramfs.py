# SPDX-License-Identifier: MIT
import gzip
import hashlib
import importlib.util
import lzma
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/boot/verify_kernel_initramfs.py"
spec = importlib.util.spec_from_file_location("verify_initramfs", PATH)
verify_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_module)


def fake_elf64_aarch64_initramfs(section):
    names = b"\0.shstrtab\0.init.ramfs\0"
    shoff = 64
    shnum = 3
    names_off = shoff + shnum * 64
    data_off = names_off + len(names)
    data_off += (-data_off) % 8
    blob = bytearray(data_off + len(section))
    blob[:4] = b"\x7fELF"
    blob[4:6] = b"\x02\x01"
    struct.pack_into("<HHIQQQIHHHHHH", blob, 16,
                     1, 183, 1, 0, 0, shoff, 0, 64, 0, 0,
                     64, shnum, 1)
    # Null section.
    struct.pack_into("<IIQQQQIIQQ", blob, shoff, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    # .shstrtab
    struct.pack_into("<IIQQQQIIQQ", blob, shoff + 64,
                     1, 3, 0, 0, names_off, len(names), 0, 0, 1, 0)
    # .init.ramfs
    struct.pack_into("<IIQQQQIIQQ", blob, shoff + 128,
                     11, 1, 2, 0, data_off, len(section), 0, 0, 1, 0)
    blob[names_off:names_off + len(names)] = names
    blob[data_off:data_off + len(section)] = section
    return bytes(blob)


def fake_vmlinux_with_linked_initramfs(payload):
    # Model Linux's final linker output: input .init.ramfs is folded into
    # .init.data and referenced by linker symbols. __initramfs_size is an
    # eight-byte object inside that output section.
    names = b"\0.shstrtab\0.strtab\0.symtab\0.init.data\0"
    shoff = 64
    shnum = 5
    names_off = shoff + shnum * 64
    strtab = b"\0__initramfs_start\0__initramfs_size\0"
    str_off = names_off + len(names)
    sym_off = str_off + len(strtab)
    sym_size = 3 * 24
    data_off = sym_off + sym_size
    data_off += (-data_off) % 8
    initramfs_start = 0x1000
    size_addr = initramfs_start + len(payload)
    init_data = payload + struct.pack("<Q", len(payload))
    blob = bytearray(data_off + len(init_data))
    blob[:4] = b"\x7fELF"
    blob[4:6] = b"\x02\x01"
    struct.pack_into("<HHIQQQIHHHHHH", blob, 16,
                     1, 183, 1, 0, 0, shoff, 0, 64, 0, 0,
                     64, shnum, 1)
    headers = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 3, 0, 0, names_off, len(names), 0, 0, 1, 0),
        (11, 3, 0, 0, str_off, len(strtab), 0, 0, 1, 0),
        (19, 2, 0, 0, sym_off, sym_size, 2, 1, 8, 24),
        (27, 1, 2, initramfs_start, data_off, len(init_data), 0, 0, 8, 0),
    ]
    for i, header in enumerate(headers):
        struct.pack_into("<IIQQQQIIQQ", blob, shoff + i * 64, *header)
    # Null symbol, linker start symbol, and assembler size symbol. The actual
    # vmlinux can keep this as STT_NOTYPE with st_size=0 while its address
    # points to the eight-byte .quad payload.
    struct.pack_into("<IBBHQQ", blob, sym_off + 24, 1, 0x10, 0, 4,
                     initramfs_start, 0)
    struct.pack_into("<IBBHQQ", blob, sym_off + 48, 19, 0x10, 0, 4,
                     size_addr, 0)
    blob[names_off:names_off + len(names)] = names
    blob[str_off:str_off + len(strtab)] = strtab
    blob[data_off:data_off + len(init_data)] = init_data
    return bytes(blob)


class BuiltinInitramfsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.object = root / "initramfs_data.o"
        self.vmlinux = root / "vmlinux"
        self.image = root / "Image"
        self.kernel_gz = root / "Image.gz"
        self.cpio = root / "first-stage.cpio"
        self.cpio_bytes = b"070701synthetic-cpio-payload\0TRAILER!!!\0"
        self.cpio.write_bytes(self.cpio_bytes)
        self.compressed = lzma.compress(self.cpio_bytes, format=lzma.FORMAT_XZ)
        elf = fake_elf64_aarch64_initramfs(self.compressed)
        self.object.write_bytes(elf)
        self.vmlinux.write_bytes(fake_vmlinux_with_linked_initramfs(self.compressed))
        image = bytearray(512)
        image[56:60] = b"ARM\x64"
        image.extend(self.compressed)
        self.image.write_bytes(image)
        self.kernel_gz.write_bytes(gzip.compress(bytes(image), mtime=0))

    def test_exact_cpio_is_xz_linked_and_embedded_in_image(self):
        result = verify_module.verify(self.object, self.vmlinux, self.image,
                                      self.kernel_gz, self.cpio, "xz")
        self.assertEqual(result["status"],
                         "ARM64_KERNEL_INITRAMFS_OBJECT_AND_IMAGE_VERIFIED")
        self.assertEqual(result["cpio_sha256"], hashlib.sha256(self.cpio_bytes).hexdigest())

    def test_rejects_cpio_not_matching_kernel_object(self):
        self.cpio.write_bytes(self.cpio_bytes + b"changed")
        with self.assertRaisesRegex(ValueError, "CPIO_CONTENT_MISMATCH"):
            verify_module.verify(self.object, self.vmlinux, self.image,
                                 self.kernel_gz, self.cpio, "xz")

    def test_rejects_object_missing_from_raw_image(self):
        image = bytearray(512)
        image[56:60] = b"ARM\x64"
        self.image.write_bytes(image)
        self.kernel_gz.write_bytes(gzip.compress(bytes(image), mtime=0))
        with self.assertRaisesRegex(ValueError, "INITRAMFS_NOT_UNIQUE_IN_IMAGE"):
            verify_module.verify(self.object, self.vmlinux, self.image,
                                 self.kernel_gz, self.cpio, "xz")

    def test_rejects_non_aarch64_elf(self):
        elf = bytearray(self.object.read_bytes())
        struct.pack_into("<H", elf, 18, 62)
        self.object.write_bytes(elf)
        with self.assertRaisesRegex(ValueError, "ELF_NOT_AARCH64"):
            verify_module.verify(self.object, self.vmlinux, self.image,
                                 self.kernel_gz, self.cpio, "xz")

    def test_rejects_mismatched_linked_initramfs_size(self):
        malformed = bytearray(fake_vmlinux_with_linked_initramfs(self.compressed))
        sections = verify_module.elf_sections(malformed)
        init_data = next(s for s in sections if s["name"] == ".init.data")
        struct.pack_into("<Q", malformed,
                         init_data["offset"] + init_data["size"] - 8,
                         len(self.compressed) + 1)
        self.vmlinux.write_bytes(malformed)
        with self.assertRaisesRegex(ValueError, "OBJECT_NOT_LINKED"):
            verify_module.verify(self.object, self.vmlinux, self.image,
                                 self.kernel_gz, self.cpio, "xz")

    def test_rejects_missing_linker_symbol(self):
        malformed = bytearray(fake_vmlinux_with_linked_initramfs(self.compressed))
        malformed = malformed.replace(b"__initramfs_start", b"__initramfs_xxxxx")
        self.vmlinux.write_bytes(malformed)
        with self.assertRaisesRegex(ValueError, "ELF_SYMBOL_COUNT___INITRAMFS_START"):
            verify_module.verify(self.object, self.vmlinux, self.image,
                                 self.kernel_gz, self.cpio, "xz")


if __name__ == "__main__":
    unittest.main()
