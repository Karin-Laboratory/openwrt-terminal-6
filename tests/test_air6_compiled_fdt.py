# SPDX-License-Identifier: MIT
"""Synthetic FDT regression tests; real DTBs are validated in hosted CI."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fdt_gate", ROOT / "scripts/check-air6-compiled-fdt.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def word(n):
    return struct.pack(">I", n)


def node(name, props=(), children=()):
    data = word(1) + name.encode() + b"\0"
    data += b"\0" * (-len(data) % 4)
    for pname, value in props:
        assert pname == "compatible"
        data += word(3) + word(len(value)) + word(0) + value
        data += b"\0" * (-len(data) % 4)
    return data + b"".join(children) + word(2)


def fixture(duplicate=False):
    switch = node("switch@0", [("compatible", b"mediatek,mt7531\0")])
    if duplicate:
        switch += switch
    body = node("", [("compatible", b"softbank,air-terminal-6\0")], [switch]) + word(9)
    strings = b"compatible\0"
    off_struct = 56
    off_strings = off_struct + len(body)
    total = off_strings + len(strings)
    header = struct.pack(">10I", gate.MAGIC, total, off_struct, off_strings,
                         40, 17, 16, 0, len(strings), len(body))
    return header + b"\0" * 16 + body + strings


class CompiledFdtTests(unittest.TestCase):
    def test_valid_structure(self):
        nodes, properties = gate.parse_fdt(fixture())
        self.assertEqual((nodes, properties), (2, 2))

    def test_duplicate_node_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate node"):
            gate.parse_fdt(fixture(duplicate=True))

    def test_repeated_root_rejected(self):
        blob = fixture()
        root = node("", [("compatible", b"softbank,air-terminal-6\0")])
        body = blob[56:-11]
        new_body = body[:-4] + root + word(9)
        strings = b"compatible\0"
        total = 56 + len(new_body) + len(strings)
        header = struct.pack(">10I", gate.MAGIC, total, 56, 56 + len(new_body),
                             40, 17, 16, 0, len(strings), len(new_body))
        with self.assertRaisesRegex(ValueError, "repeated root"):
            gate.parse_fdt(header + b"\0" * 16 + new_body + strings)

    def test_trailing_structure_token_rejected(self):
        blob = fixture()
        body = blob[56:-11] + word(4)
        strings = b"compatible\0"
        total = 56 + len(body) + len(strings)
        header = struct.pack(">10I", gate.MAGIC, total, 56, 56 + len(body),
                             40, 17, 16, 0, len(strings), len(body))
        with self.assertRaises(ValueError):
            gate.parse_fdt(header + b"\0" * 16 + body + strings)

    def test_overlapping_blocks_rejected(self):
        blob = bytearray(fixture())
        struct.pack_into(">I", blob, 12, 56)  # strings begin inside structure
        with self.assertRaisesRegex(ValueError, "overlapping FDT blocks"):
            gate.parse_fdt(bytes(blob))

    def test_unterminated_reservation_map_rejected(self):
        blob = bytearray(fixture())
        blob[40:56] = word(1) + word(0) + word(0) + word(1)
        with self.assertRaisesRegex(ValueError, "unterminated FDT reservation map"):
            gate.parse_fdt(bytes(blob))

    def test_misaligned_reservation_map_rejected(self):
        blob = bytearray(fixture())
        struct.pack_into(">I", blob, 16, 44)
        with self.assertRaisesRegex(ValueError, "invalid FDT reservation map"):
            gate.parse_fdt(bytes(blob))

    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):
            gate.parse_fdt(fixture()[:-1])

    def test_missing_switch_rejected(self):
        blob = fixture().replace(b"mediatek,mt7531", b"mediatek,mt9999")
        with self.assertRaisesRegex(ValueError, "MT7531"):
            gate.parse_fdt(blob)


if __name__ == "__main__":
    unittest.main()
