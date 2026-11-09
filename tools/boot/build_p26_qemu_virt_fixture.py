#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate an ephemeral QEMU-virtio-only copy of the actual p26 boot CPIO.

The ORIGINAL Air6 /init is NEVER changed. Only this scratch CPIO replaces
the observed p26 GPT block identifier with the QEMU virtio /dev/vda identity.
Its only purpose is a no-sign, no-flash QEMU virt RAM-overlay boot test.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
from tools.boot import build_p26_p44_initramfs as origin

ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / "scripts/package-arm64-busybox-initramfs.py"
NEWC = ROOT / "scripts/build-minimal-arm64-initramfs.py"
PATCHES = (
    (b"P26=/dev/mmcblk0p26", b"P26=/dev/vda"),
    (b"'PARTNAME=rootfs_a' /sys/class/block/mmcblk0p26/uevent",
     b"'DEVNAME=vda' /sys/class/block/vda/uevent"),
)


def _module(path):
    spec = importlib.util.spec_from_file_location("air6_ephemeral_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def build(original_cpio, cpio_receipt, p26_file, p26_receipt, output, manifest):
    paths = list(map(Path, (original_cpio, cpio_receipt, p26_file, p26_receipt)))
    for p in paths:
        if not p.is_file() or p.is_symlink():
            raise ValueError("QEMU_FIXTURE_NONREGULAR_INPUT")
    output, manifest = Path(output), Path(manifest)
    if output == manifest or output.exists() or manifest.exists():
        raise ValueError("QEMU_FIXTURE_OUTPUT_EXISTS")
    original = paths[0].read_bytes()
    receipt = json.loads(paths[1].read_text())
    p26info = json.loads(paths[3].read_text())
    p26_hash = origin.sha(paths[2])
    if (paths[2].stat().st_size != origin.PARTITION_BYTES or
            p26info.get("partition_bytes") != origin.PARTITION_BYTES or
            p26info.get("p26_sha256") != p26_hash or
            receipt.get("cpio_sha256") != digest(original) or
            receipt.get("p26_sha256") != p26_hash or
            receipt.get("scope") != "EPHEMERAL_UNSIGNED_BOOTSTRAP_CPIO_NOT_AIR6_VALIDATED"):
        raise ValueError("QEMU_FIXTURE_SOURCE_READBACK")
    entries = _module(READER).unpack(original)
    if "init" not in entries or "etc/air6-p26.sha256" not in entries:
        raise ValueError("QEMU_FIXTURE_NO_INIT")
    if any(k in entries for k in ("etc/air6-owner-p44-rw-go", "etc/air6-p44.partname")):
        raise ValueError("QEMU_FIXTURE_OWNER_MATERIAL")
    if entries["etc/air6-p26.sha256"][1] != (p26_hash + "\n").encode():
        raise ValueError("QEMU_FIXTURE_P26_NOT_BOUND")
    mode, init, major, minor = entries["init"]
    if not stat.S_ISREG(mode) or init != origin.BOOT_SCRIPT.read_bytes() or not mode & 0o111:
        raise ValueError("QEMU_FIXTURE_INIT_SOURCE_MISMATCH")
    revised = init
    for old, new in PATCHES:
        if revised.count(old) != 1 or revised.count(new):
            raise ValueError("QEMU_FIXTURE_PATCH_INPUT")
        revised = revised.replace(old, new)
    if b"/dev/mmcblk0p26" in revised or b"PARTNAME=rootfs_a" in revised:
        raise ValueError("QEMU_FIXTURE_P26_PATH_UNCHANGED")
    entries["init"] = (mode, revised, major, minor)
    pack = _module(NEWC)
    buffer = bytearray()
    for ino, name in enumerate(sorted(k for k in entries if k != "TRAILER!!!"), 1):
        m, content, rmajor, rminor = entries[name]
        buffer.extend(pack.newc_entry(name, m, content, ino, rmajor, rminor))
        if len(buffer) > origin.MAX_ARCHIVE:
            raise ValueError("QEMU_FIXTURE_TOO_LARGE")
    buffer.extend(pack.newc_entry("TRAILER!!!", 0, ino=len(entries)))
    evidence = {
        "schema": "air6-qemu-virtio-only-positive-p26-v1",
        "scope": "EPHEMERAL_SYNTHETIC_VIRTIO_P26_NO_AIR6_BOOT_CLAIM",
        "source_cpio_sha256": digest(original),
        "cpio_sha256": digest(buffer),
        "p26_sha256": p26_hash,
        "init_sha256": digest(revised),
        "virtual_block": "/dev/vda",
        "owner_p44_authorization": False,
        "source_air6_init_modified": False,
        "air6_hardware_proven": False,
        "signed_or_installable": False,
        "cpio_bytes": len(buffer),
    }
    made = False
    try:
        with output.open("xb") as f:
            made = True
            f.write(buffer)
        with manifest.open("x") as f:
            f.write(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    except BaseException:
        if made:
            output.unlink(missing_ok=True)
        raise
    return evidence


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("source-cpio", "source-receipt", "p26", "p26-receipt", "output", "receipt"):
        ap.add_argument("--" + name, required=True, type=Path)
    a = ap.parse_args()
    r = build(a.source_cpio, a.source_receipt, a.p26, a.p26_receipt, a.output, a.receipt)
    print("PUBLIC_AIR6_SYNTHETIC_QEMU_VIRT_P26_CPIO_BUILT", r["cpio_sha256"])


if __name__ == "__main__":
    main()
