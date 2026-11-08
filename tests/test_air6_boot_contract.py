# SPDX-License-Identifier: MIT
"""Public synthetic fixtures; never OEM headers or device identifiers."""
import hashlib
import struct
import unittest
from tools.boot import air6_boot_contract as gate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fdt(nodes=("/chosen",), phandle=None):
    strings = b"phandle\x00"
    body = bytearray()
    body += struct.pack(">I", 1) + b"\x00\x00\x00\x00"
    for path in nodes:
        name = path.lstrip("/").encode()
        body += struct.pack(">I", 1) + (name + b"\x00").ljust((len(name)+4)//4*4, b"\x00")
        if phandle is not None:
            body += struct.pack(">III", 3, 4, 0) + struct.pack(">I", phandle)
        body += struct.pack(">I", 2)
    body += struct.pack(">II", 2, 9)
    reserve = b"\x00" * 16
    start = 40 + len(reserve)
    off_strings = start + len(body)
    header = struct.pack(">10I", 0xd00dfeed, off_strings + len(strings),
                         start, off_strings, 40, 17, 16, 0, len(strings), len(body))
    return header + reserve + body + strings


def specimen(section):
    image = bytearray(gate.PARTITION)
    image[:8] = b"ANDROID!"
    struct.pack_into("<10I", image, 8, 64, 0, 0, 0, 0, 0, 0, 2048, 2, 0)
    image[48:64] = b"research\x00".ljust(16, b"\x00")
    struct.pack_into("<IQIIQ", image, 1632, 0, 0, 1660, len(section), 0)
    start = 4096
    image[start:start + len(section)] = section
    return image


def metadata(image, section, injected=(), prefix_sha=None):
    return dict(format="public-air6-p25-contract-v1",
                metadata_provenance="synthetic-research-only",
                expected_header={"kernel_addr": 0, "tags_addr": 0,
                                 "dtb_addr": 0, "os_version": 0,
                                 "board": "research", "cmdline": "", "extra_cmdline": ""},
                expected_header_page_sha256=sha(image[:2048]),
                expected_dtb_sha256=sha(section),
                lk_injected_nodes=list(injected), vendor64_prefix_sha256=prefix_sha)


class P25ContractTests(unittest.TestCase):
    def test_bare_fdt_aosp_v2_structure_does_not_claim_lk(self):
        section = fdt()
        image = specimen(section)
        result = gate.check(image, metadata(image, section), section,
                            {"source": "synthetic-fixture"})
        self.assertFalse(result["sign_ready"])
        self.assertFalse(result["device_boot_proven"])
        self.assertGreaterEqual(result["nodes"], 2)

    def test_lk_collision_rejected(self):
        section = fdt()
        image = specimen(section)
        with self.assertRaisesRegex(ValueError, "FDT_LK_INJECTION_COLLISION"):
            gate.check(image, metadata(image, section, ("/chosen",)), section,
                       {"source": "synthetic-fixture"})

    def test_vendor64_requires_pinned_prefix_and_independent_fdt(self):
        bare = fdt()
        section = b"V" * 64 + bare
        image = specimen(section)
        self.assertEqual(gate.check(image, metadata(image, section, prefix_sha=sha(section[:64])),
                                    section, {"source": "synthetic-fixture"})["fdt_bytes"], len(bare))
        with self.assertRaisesRegex(ValueError, "P25_VENDOR64_IDENTITY"):
            gate.check(image, metadata(image, section, prefix_sha="0" * 64),
                       section, {"source": "synthetic-fixture"})

    def test_reject_modified_header_even_if_image_looks_valid(self):
        section = fdt()
        image = specimen(section)
        cfg = metadata(image, section)
        struct.pack_into("<I", image, 12, 0x40000000)
        with self.assertRaisesRegex(ValueError, "P25_HEADER_MISMATCH"):
            gate.check(image, cfg, section, {"source": "synthetic-fixture"})

    def test_reject_duplicate_phandle_and_bad_reservation_table(self):
        self.assertRaisesRegex(ValueError, "FDT_PHANDLE_COLLISION",
                               gate.check_fdt, fdt(("/a", "/b"), phandle=1))
        raw = bytearray(fdt())
        raw[40:56] = b"\xff" * 16
        self.assertRaisesRegex(ValueError, "FDT_MEMRESERVE_TERMINATOR",
                               gate.check_fdt, raw)

    def test_reject_unproven_external_observation(self):
        section = fdt()
        image = specimen(section)
        with self.assertRaisesRegex(ValueError, "P25_SOURCE_LOCATOR_REQUIRED"):
            gate.check(image, metadata(image, section), section,
                       {"source": "independently-observed-public"})


if __name__ == "__main__":
    unittest.main()
