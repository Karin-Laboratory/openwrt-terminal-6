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

    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):
            gate.parse_fdt(fixture()[:-1])

    def test_missing_switch_rejected(self):
        blob = fixture().replace(b"mediatek,mt7531", b"mediatek,mt9999")
        with self.assertRaisesRegex(ValueError, "MT7531"):
            gate.parse_fdt(blob)


if __name__ == "__main__":
    unittest.main()
