# SPDX-License-Identifier: MIT
"""Synthetic public AOSP 32+32 DT-table regression, no proprietary bytes."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/boot/make_p25_dtb_table.py"
spec = importlib.util.spec_from_file_location("dt_table64", SRC)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

PINNED_PUBLIC_RC16_PREFIX_SHA256 = (
    "f170c43553f75b65bb0f88714f776773f79489cad8725078ddc84bf7fb2d73d2")


def fdt_of_length(n):
    data = bytearray(n)
    data[:4] = bytes.fromhex("d00dfeed")
    struct.pack_into(">I", data, 4, n)
    return bytes(data)


class TestAospDtTable64(unittest.TestCase):
    def test_exact_published_rc16_64b_identity_from_public_spec(self):
        prefix = tool.generate(fdt_of_length(148765), 2048)
        self.assertEqual(len(prefix), 64)
        self.assertEqual(hashlib.sha256(prefix).hexdigest(),
                         PINNED_PUBLIC_RC16_PREFIX_SHA256)
        self.assertEqual(struct.unpack_from(">8I", prefix),
                         (0xd7b7ab1e, 148829, 32, 32, 1, 32, 2048, 0))
        self.assertEqual(struct.unpack_from(">8I", prefix, 32),
                         (148765, 64, 0, 0, 0, 0, 0, 0))

    def test_r39f_size_change_requires_new_header_and_entry_sizes(self):
        original = tool.generate(fdt_of_length(148765))
        changed = tool.generate(fdt_of_length(177286))
        self.assertNotEqual(original, changed)
        self.assertEqual(struct.unpack_from(">I", changed, 4)[0], 177350)
        self.assertEqual(struct.unpack_from(">I", changed, 32)[0], 177286)
        self.assertNotEqual(hashlib.sha256(changed).hexdigest(),
                            PINNED_PUBLIC_RC16_PREFIX_SHA256)

    def test_wrong_magic_length_and_page_rejected(self):
        for input_bytes in (b"", b"x" * 40,
                            fdt_of_length(40) + b"x"):
            with self.subTest(n=len(input_bytes)):
                with self.assertRaises(ValueError):
                    tool.generate(input_bytes)
        for page in (0, 512, 3000, True):
            with self.subTest(page=page):
                with self.assertRaisesRegex(ValueError, "PAGE_SIZE"):
                    tool.generate(fdt_of_length(40), page)

    def test_output_exclusive_and_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dtb = root / "input.dtb"
            out = root / "vendor64"
            dtb.write_bytes(fdt_of_length(148765))
            digest = tool.produce(dtb, out)
            self.assertEqual(digest, PINNED_PUBLIC_RC16_PREFIX_SHA256)
            self.assertEqual(out.read_bytes(), tool.generate(dtb.read_bytes()))
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                tool.produce(dtb, out)

    def test_reject_symlinked_input_and_output_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.dtb"
            real.write_bytes(fdt_of_length(40))
            alias = root / "alias.dtb"
            alias.symlink_to(real)
            with self.assertRaisesRegex(ValueError, "INPUT_PATH"):
                tool.produce(alias, root / "out")
            (root / "outdir").mkdir()
            (root / "aliasdir").symlink_to(root / "outdir")
            with self.assertRaisesRegex(ValueError, "OUTPUT_PARENT"):
                tool.produce(real, root / "aliasdir" / "out")


if __name__ == "__main__":
    unittest.main()
