# SPDX-License-Identifier: MIT
"""Public AOSP-v2 boot research packer regression tests, not hardware proof."""
import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest
from tools.build import pack_p25_boot_v2 as maker
from tools.build import verify_p25_boot_v2 as reader


class BootV2SpecTests(unittest.TestCase):
    def test_real_32m_aosp_header_and_independent_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = bytearray(64)
            image[56:60] = b"ARM\x64"
            k = root / "Image.gz"
            with k.open("wb") as dst:
                with gzip.GzipFile(fileobj=dst, mode="wb", mtime=0) as gz:
                    gz.write(image)
            dt = root / "board.dtb"
            data = bytearray(64)
            struct.pack_into(">10I", data, 0, 0xd00dfeed, 64, 56, 48, 40, 17, 16, 0, 8, 8)
            dt.write_bytes(data)
            meta = root / "meta.json"
            meta.write_text(json.dumps({
                "format": "aosp-boot-v2-metadata-v1",
                "metadata_provenance": "synthetic-research-only", "page_size": 2048,
                "kernel_addr": 0, "tags_addr": 0, "dtb_addr": 0, "os_version": 0,
                "board": "research", "cmdline": ""}))
            out, receipt = root / "boot.img", root / "receipt.json"
            r = maker.build(k, dt, meta, out, receipt)
            self.assertEqual(out.stat().st_size, 33554432)
            self.assertEqual(reader.verify(out, receipt, k, dt), r["p25_sha256"])
            self.assertFalse(r["lk_header_and_vendor64_accepted"])
            with out.open("r+b") as f:
                f.seek(8192)
                f.write(b"NO")
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                reader.verify(out, receipt, k, dt)

    def test_reject_uncompressed_image_or_invented_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            k, d, m = [root / n for n in ("kernel", "dtb", "meta")]
            k.write_bytes(b"a" * 64)
            d.write_bytes(b"a" * 64)
            m.write_text("{}")
            with self.assertRaises(ValueError):
                maker.build(k, d, m, root / "o", root / "r")
            self.assertFalse((root / "o").exists())


if __name__ == "__main__":
    unittest.main()
