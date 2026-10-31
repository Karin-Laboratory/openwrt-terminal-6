# SPDX-License-Identifier: MIT
"""Offline tests for the BusyBox PID1 cpio ingredient; no binary execution."""
import gzip
import importlib.util
import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package-arm64-busybox-initramfs.py"
spec = importlib.util.spec_from_file_location("busybox_initramfs", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fake_elf(interpreter=False, machine=183):
    data = bytearray(120)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 2, machine)
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<I", data, 64, 3 if interpreter else 1)
    return bytes(data)


class BusyBoxPid1CpioTests(unittest.TestCase):
    def test_archive_has_real_pid1_script_and_static_busybox(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            binary = p / "busybox"
            binary.write_bytes(fake_elf())
            first = module.package(binary, p / "one.cpio.gz", p / "one.json")
            second = module.package(binary, p / "two.cpio.gz", p / "two.json")
            self.assertEqual(first, second)
            self.assertEqual((p / "one.cpio.gz").read_bytes(),
                             (p / "two.cpio.gz").read_bytes())
            self.assertEqual(json.loads((p / "one.json").read_text()), first)
            entries = module.unpack(gzip.decompress((p / "one.cpio.gz").read_bytes()))
            self.assertEqual(set(entries), {"bin", "dev", "dev/console", "dev/null",
                                            "proc", "sys", "bin/busybox", "bin/sh",
                                            "init", "TRAILER!!!"})
            self.assertEqual(entries["bin/busybox"][1], binary.read_bytes())
            self.assertTrue(stat.S_ISLNK(entries["bin/sh"][0]))
            self.assertEqual(entries["bin/sh"][1], b"busybox")
            self.assertTrue(stat.S_ISREG(entries["init"][0]))
            self.assertTrue(entries["init"][1].startswith(b"#!/bin/sh\n"))
            self.assertIn(b"/bin/busybox sleep", entries["init"][1])
            self.assertEqual(entries["dev/console"][2:], (5, 1))
            self.assertEqual(entries["dev/null"][2:], (1, 3))
            self.assertEqual(first["rights_review"], "pending")
            self.assertEqual(first["libc"], "host-glibc-static-not-openwrt-musl")

    def test_musl_pid1_archive_has_explicit_libc_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binary = root / "busybox"
            binary.write_bytes(fake_elf())
            record = module.package(binary, root / "musl.cpio.gz", root / "musl.json",
                                    libc="musl-static")
            self.assertEqual(record["libc"], "musl-static")
            self.assertEqual(record["scope"], "NONINSTALLABLE_MUSL_STATIC_BUSYBOX_PID1_INITRAMFS")
            self.assertIn("OpenWrt toolchain/rootfs/procd/netifd", record["not_proven"])
            with self.assertRaisesRegex(ValueError, "unsupported libc"):
                module.package(binary, root / "bad.cpio.gz", root / "bad.json",
                               libc="unknown")
            entries = module.unpack(gzip.decompress((root / "musl.cpio.gz").read_bytes()))
            self.assertEqual(entries["bin/busybox"][1], binary.read_bytes())

    def test_fail_closed_wrong_elf_or_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            binary = p / "busybox"
            for data in (fake_elf(interpreter=True), fake_elf(machine=62), b"bad"):
                binary.write_bytes(data)
                with self.assertRaises(ValueError):
                    module.package(binary, p / "a.gz", p / "a.json")
            binary.write_bytes(fake_elf())
            existing = p / "existing"
            existing.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "outputs"):
                module.package(binary, existing, p / "manifest")
            self.assertEqual(existing.read_text(), "preserve")

    def test_cpio_rejects_trailing_data_and_unsafe_names(self):
        with self.assertRaisesRegex(ValueError, "unsafe"):
            module.entry("../passwd", stat.S_IFREG | 0o644, b"x", 1)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            binary = p / "busybox"
            binary.write_bytes(fake_elf())
            module.package(binary, p / "a.gz", p / "a.json")
            raw = gzip.decompress((p / "a.gz").read_bytes())
            with self.assertRaises(ValueError):
                module.unpack(raw + b"extra")

    def test_no_remote_login_or_device_actions(self):
        init = module.INIT
        for forbidden in (b"dropbear", b"telnet", b"passwd", b"udhcpc",
                          b"mtd", b"flash", b"sysupgrade", b"reboot"):
            self.assertNotIn(forbidden, init)
        workflow = (ROOT / ".github/workflows/arm64-image-build.yml").read_text()
        self.assertIn("build-arm64-musl-busybox-stage.sh", workflow)
        self.assertIn("NONINSTALLABLE_MUSL_STATIC_BUSYBOX_PID1_INITRAMFS", workflow)
        self.assertIn("SBAT6_BUSYBOX_PID1_EMBEDDED_IMAGE_PASS", workflow)
        self.assertIn('cmp "$tmp/ramfs/initramfs.cpio.gz" usr/initramfs_inc_data', workflow)


if __name__ == "__main__":
    unittest.main()
