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
        self.vmlinux.write_bytes(elf)
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


if __name__ == "__main__":
    unittest.main()
