#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently read back the original CPIO and isolated virtio-only CPIO."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from tools.boot import build_p26_p44_initramfs as origin

ROOT = Path(__file__).resolve().parents[2]
CPIO_READER = ROOT / "scripts/package-arm64-busybox-initramfs.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(original_cpio, fixture_cpio, receipt_path, p26, p26_receipt):
    a, b, c, d, e = map(Path, (original_cpio, fixture_cpio, receipt_path, p26, p26_receipt))
    if any(not p.is_file() or p.is_symlink() for p in (a, b, c, d, e)):
        raise ValueError("VIRTIO_READBACK_FILES")
    original, synthetic = a.read_bytes(), b.read_bytes()
    record, p26record = json.loads(c.read_text()), json.loads(e.read_text())
    digest = origin.sha(d)
    if (d.stat().st_size != origin.PARTITION_BYTES or
            p26record.get("partition_bytes") != origin.PARTITION_BYTES or
            p26record.get("p26_sha256") != digest or
            record.get("p26_sha256") != digest):
        raise ValueError("VIRTIO_READBACK_P26")
    if (record.get("schema") != "air6-qemu-virtio-only-positive-p26-v1" or
            record.get("scope") != "EPHEMERAL_SYNTHETIC_VIRTIO_P26_NO_AIR6_BOOT_CLAIM" or
            record.get("virtual_block") != "/dev/vda" or
            record.get("source_cpio_sha256") != sha(original) or
            record.get("cpio_sha256") != sha(synthetic) or
            record.get("cpio_bytes") != len(synthetic) or
            any(record.get(k) is not False for k in
                ("owner_p44_authorization", "source_air6_init_modified",
                 "air6_hardware_proven", "signed_or_installable"))):
        raise ValueError("VIRTIO_READBACK_RECEIPT")
    spec = importlib.util.spec_from_file_location("air6_qemu_independent_cpio_parser", CPIO_READER)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    before, after = parser.unpack(original), parser.unpack(synthetic)
    if set(before) != set(after) or "init" not in before:
        raise ValueError("VIRTIO_READBACK_MEMBERS")
    for key, contents in before.items():
        if key != "init" and contents != after[key]:
            raise ValueError("VIRTIO_READBACK_NONINIT_CHANGE_" + key)
    source = origin.BOOT_SCRIPT.read_bytes()
    if before["init"][1] != source:
        raise ValueError("VIRTIO_READBACK_ORIGINAL_INIT")
    expected = source.replace(b"P26=/dev/mmcblk0p26", b"P26=/dev/vda")
    expected = expected.replace(
        b"'PARTNAME=rootfs_a' /sys/class/block/mmcblk0p26/uevent",
        b"'DEVNAME=vda' /sys/class/block/vda/uevent")
    if (after["init"][0] != before["init"][0] or
            after["init"][1] != expected or sha(expected) != record.get("init_sha256") or
            b"/dev/mmcblk0p26" in expected or
            any(k in after for k in ("etc/air6-p44.partname", "etc/air6-owner-p44-rw-go")) or
            after["etc/air6-p26.sha256"][1] != (digest + "\n").encode()):
        raise ValueError("VIRTIO_READBACK_UNAUTHORIZED_INIT")
    return {"status": "QEMU_VIRTIO_SYNTHETIC_P26_CPIO_INDEPENDENT_READBACK_PASS",
            "cpio_sha256": sha(synthetic), "p26_sha256": digest,
            "hardware_boot_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("source-cpio", "fixture", "receipt", "p26", "p26-receipt"):
        ap.add_argument("--" + name, required=True, type=Path)
    a = ap.parse_args()
    print(json.dumps(verify(a.source_cpio, a.fixture, a.receipt, a.p26, a.p26_receipt),
                     sort_keys=True))


if __name__ == "__main__":
    main()
