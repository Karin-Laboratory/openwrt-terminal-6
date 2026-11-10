# SPDX-License-Identifier: MIT
"""Public AOSP-v2 boot research packer regression tests, not hardware proof."""
import gzip
import hashlib
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
            # A matching receipt digest cannot excuse nonzero page padding.
            gap = 2048 + k.stat().st_size
            self.assertLess(gap, r["dtb"]["offset"])
            with out.open("r+b") as f:
                f.seek(gap)
                f.write(b"X")
            tampered = json.loads(receipt.read_text())
            tampered["p25_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "alignment padding"):
                reader.verify(out, receipt, k, dt)
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


    def test_external_synthetic_vendor64_prefix_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = bytearray(64)
            image[56:60] = b"ARM\x64"
            kernel = root / "Image.gz"
            with kernel.open("wb") as dst:
                with gzip.GzipFile(filename="", mode="wb",
                                   fileobj=dst, mtime=0) as stream:
                    stream.write(image)
            fdt = bytearray(64)
            struct.pack_into(">10I", fdt, 0, 0xd00dfeed, 64, 56, 48, 40, 17, 16, 0, 8, 8)
            prefix = bytes(range(64))  # synthetic; NO OEM bytes.
            dtb = root / "synthetic-prefix-board.dtb"
            dtb.write_bytes(prefix + fdt)
            meta = root / "meta.json"
            data = {
                "format": "aosp-boot-v2-metadata-v1",
                "metadata_provenance": "synthetic-research-only",
                "page_size": 2048,
                "kernel_addr": 0, "tags_addr": 0, "dtb_addr": 0, "os_version": 0,
                "board": "research", "cmdline": "",
                "dtb_layout": "opaque-64-prefix-plus-fdt",
                "vendor64_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
            }
            meta.write_text(json.dumps(data))
            out, receipt = root / "boot.img", root / "receipt.json"
            result = maker.build(kernel, dtb, meta, out, receipt)
            self.assertEqual(result["dtb_layout"], "opaque-64-prefix-plus-fdt")
            self.assertEqual(reader.verify(out, receipt, kernel, dtb),
                             result["p25_sha256"])
            bad = dict(result)
            bad["vendor64_prefix_sha256"] = "0" * 64
            receipt.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "vendor64 prefix SHA"):
                reader.verify(out, receipt, kernel, dtb)
            data["vendor64_prefix_sha256"] = "0" * 64
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "vendor64 prefix SHA"):
                maker.build(kernel, dtb, meta, root / "invalid.img", root / "invalid.json")
            self.assertFalse((root / "invalid.img").exists())
            data["vendor64_prefix_sha256"] = hashlib.sha256(prefix).hexdigest()
            data["dtb_layout"] = "bare-fdt"
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unexpected vendor64 SHA"):
                maker.build(kernel, dtb, meta, root / "invalid2.img", root / "invalid2.json")


    def test_reject_trailing_and_concatenated_gzip_members_before_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arm64 = bytearray(64)
            arm64[56:60] = b"ARM\x64"
            kernel = root / "Image.gz"
            # Each member has its own valid gzip CRC/ISIZE. Some decompression
            # libraries accept this concatenation, but the device LK inflater
            # must not be assumed to support it.
            one = gzip.compress(arm64, mtime=0)
            dtb = root / "board.dtb"
            fdt = bytearray(64)
            struct.pack_into(">10I", fdt, 0, 0xd00dfeed, 64, 56, 48,
                             40, 17, 16, 0, 8, 8)
            dtb.write_bytes(fdt)
            meta = root / "meta.json"
            meta.write_text(json.dumps({
                "format": "aosp-boot-v2-metadata-v1",
                "metadata_provenance": "synthetic-research-only",
                "page_size": 2048, "kernel_addr": 0,
                "tags_addr": 0, "dtb_addr": 0, "os_version": 0,
                "board": "research", "cmdline": ""
            }))
            for label, content, pattern in (
                ("trailing", one + b"extra", "trailing bytes"),
                ("multi-member", one + gzip.compress(b"x", mtime=0), "trailing bytes"),
                ("truncated", one[:-4], "truncated gzip"),
                ("bad-crc", one[:-8] + b"\x00" * 8, "invalid gzip"),
            ):
                with self.subTest(case=label):
                    kernel.write_bytes(content)
                    output, receipt = root / (label + ".img"), root / (label + ".json")
                    with self.assertRaisesRegex(ValueError, pattern):
                        maker.build(kernel, dtb, meta, output, receipt)
                    self.assertFalse(output.exists())
                    self.assertFalse(receipt.exists())
            kernel.write_bytes(one)
            output, receipt = root / "valid.img", root / "valid.json"
            result = maker.build(kernel, dtb, meta, output, receipt)
            self.assertEqual(reader.verify(output, receipt, kernel, dtb),
                             result["p25_sha256"])


if __name__ == "__main__":
    unittest.main()
