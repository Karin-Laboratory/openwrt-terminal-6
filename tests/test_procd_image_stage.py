# SPDX-License-Identifier: MIT
"""Offline tests for real procd-stage to kernel initramfs construction."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "procd_stage", ROOT / "scripts/package-arm64-procd-stage-initramfs.py"
)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fake_aarch64_elf():
    data = bytearray(120)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 2, 183)
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<I", data, 64, 1)  # PT_LOAD, never PT_INTERP
    return bytes(data)


class ProcdImageStageTests(unittest.TestCase):
    def make_source(self, root: Path):
        data = fake_aarch64_elf()
        policies = {name: (ROOT / "config/sbat6-stage" / name).read_bytes()
                    for name in stage.POLICY}
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as tar:
            for name in stage.DIRS:
                info = tarfile.TarInfo(name)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            for name in stage.BINARIES:
                info = tarfile.TarInfo(name)
                info.mode = 0o755
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            for name, payload in policies.items():
                info = tarfile.TarInfo(name)
                info.mode = 0o755 if name in stage.POLICY_EXEC else 0o644
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            info = tarfile.TarInfo("bin/sh")
            info.type = tarfile.SYMTYPE
            info.linkname = "busybox"
            tar.addfile(info)
        payload = gzip.compress(buf.getvalue(), mtime=0)
        rootfs = root / "source.tar.gz"
        rootfs.write_bytes(payload)
        manifest = root / "source.json"
        manifest.write_text(json.dumps({
            "scope": stage.SOURCE_SCOPE, "architecture": "aarch64",
            "libc": "native-musl-static-1.2.5", "rights_review": "pending",
            "archive_sha256": hashlib.sha256(payload).hexdigest(),
            "archive_bytes": len(payload),
            "files_sha256": {
                **{name: hashlib.sha256(data).hexdigest() for name in stage.BINARIES},
                **{name: hashlib.sha256(payload).hexdigest()
                   for name, payload in policies.items()},
            },
        }))
        return rootfs, manifest

    def test_real_six_elf_stage_becomes_pid1_cpio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rootfs, source = self.make_source(root)
            out, manifest = root / "initramfs.cpio.gz", root / "out.json"
            result = stage.package(rootfs, source, out, manifest)
            parsed = stage.cpio.unpack(gzip.decompress(out.read_bytes()))
            self.assertEqual(parsed["init"][1], b"sbin/init")
            self.assertEqual(parsed["dev/console"][2:], (5, 1))
            self.assertEqual(set(stage.BINARIES).issubset(parsed), True)
            for name in stage.POLICY:
                self.assertEqual(parsed[name][1],
                                 (ROOT / "config/sbat6-stage" / name).read_bytes())
            self.assertEqual(result["scope"],
                             "NONINSTALLABLE_AIR6_PROCD_STAGE_EMBEDDED_INITRAMFS")
            self.assertEqual(result["initramfs_sha256"],
                             hashlib.sha256(out.read_bytes()).hexdigest())

    def test_rejects_modified_rootfs_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rootfs, source = self.make_source(root)
            rootfs.write_bytes(rootfs.read_bytes() + b"bad")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                stage.package(rootfs, source, root / "out", root / "manifest")

    def test_rejects_policy_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rootfs, source = self.make_source(root)
            manifest = json.loads(source.read_text())
            manifest["files_sha256"]["etc/preinit"] = "0" * 64
            source.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "boot policy identity mismatch"):
                stage.package(rootfs, source, root / "out", root / "manifest")

    def test_no_existing_output_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rootfs, source = self.make_source(root)
            out = root / "out"
            out.write_text("do not overwrite")
            with self.assertRaisesRegex(ValueError, "absent"):
                stage.package(rootfs, source, out, root / "manifest")


if __name__ == "__main__":
    unittest.main()
