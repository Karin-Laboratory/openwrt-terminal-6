#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a separate real-package initramfs with optional P26/P44 boot path.

This does NOT replace the current known QEMU procd PID1 initramfs; the output
is an ephemeral offline candidate. In particular, the file needed to approve
a P44 RW mount is deliberately NEVER manufactured here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
BOOT_SCRIPT = ROOT / "scripts/air6-p26-p44-init.sh"
NEWC_SCRIPT = ROOT / "scripts/build-minimal-arm64-initramfs.py"
PARTITION_BYTES = 134_217_728
MAX_ARCHIVE = 256 * 1024 * 1024


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError("AIR6_STAGE_" + code)


def package(rootfs, p26_file, p26_receipt, cpio_path, receipt_path):
    rootfs, p26_file, p26_receipt, cpio_path, receipt_path = map(
        Path, (rootfs, p26_file, p26_receipt, cpio_path, receipt_path))
    require(rootfs.is_dir() and not rootfs.is_symlink(), "ROOTFS")
    require(p26_file.is_file() and not p26_file.is_symlink(), "P26")
    require(p26_receipt.is_file() and not p26_receipt.is_symlink(), "P26_RECEIPT")
    require(cpio_path != receipt_path, "OUTPUT_ALIAS")
    require(not cpio_path.exists() and not cpio_path.is_symlink() and
            not receipt_path.exists() and not receipt_path.is_symlink(),
            "OUTPUT_ALREADY_EXISTS")
    require(cpio_path.parent.is_dir() and receipt_path.parent.is_dir() and
            not cpio_path.parent.is_symlink() and not receipt_path.parent.is_symlink(),
            "OUTPUT_PARENT")
    record = json.loads(p26_receipt.read_text())
    require(record.get("partition_bytes") == PARTITION_BYTES and
            p26_file.stat().st_size == PARTITION_BYTES and
            record.get("p26_sha256") == sha(p26_file), "P26_INDEPENDENT_SHA")
    for name in ("bin/busybox", "sbin/procd", "sbin/init", "etc/preinit"):
        src = rootfs / name
        require(src.exists() and (src.is_file() or src.is_symlink()),
                "ROOTFS_DEPENDENCY_" + name)
    require(not (rootfs / "init").exists() and not (rootfs / "init").is_symlink(),
            "ROOTFS_ALREADY_HAS_INIT")
    for name in ("etc/air6-p26.sha256", "etc/air6-owner-p44-rw-go",
                 "etc/air6-p44.partname"):
        require(not (rootfs / name).exists() and not (rootfs / name).is_symlink(),
                "ROOTFS_PROTECTED_" + name)
    for name in ("etc/rc.d/S50dropbear", "etc/rc.d/S49dropbear"):
        require(not (rootfs / name).exists() and not (rootfs / name).is_symlink(),
                "DROPBEAR_AUTO_START")
    source = BOOT_SCRIPT.read_bytes()
    require(source.startswith(b"#!/bin/sh\n") and b"\x00" not in source and
            len(source) < 32_768, "BOOT_SCRIPT")
    spec = importlib.util.spec_from_file_location("public_air6_newc", NEWC_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    entries = {}
    for path in sorted(rootfs.rglob("*")):
        name = path.relative_to(rootfs).as_posix()
        st = path.lstat()
        require(name and not name.startswith("/") and ".." not in name.split("/"),
                "ENTRY_PATH")
        if stat.S_ISDIR(st.st_mode):
            payload = b""
        elif stat.S_ISLNK(st.st_mode):
            payload = os.fsencode(os.readlink(path))
        elif stat.S_ISREG(st.st_mode):
            require(st.st_size <= 128 * 1024 * 1024, "ENTRY_OVERSIZE")
            payload = path.read_bytes()
        else:
            raise ValueError("AIR6_STAGE_SPECIAL_FILE_" + name)
        entries[name] = (st.st_mode, payload, 0, 0)
    for name in ("dev", "proc", "sys", "mnt", "etc"):
        entries.setdefault(name, (stat.S_IFDIR | 0o755, b"", 0, 0))
    for name, major, minor, mode in (("dev/console", 5, 1, 0o600),
                                     ("dev/null", 1, 3, 0o666)):
        entries.setdefault(name, (stat.S_IFCHR | mode, b"", major, minor))
    entries["init"] = (stat.S_IFREG | 0o755, source, 0, 0)
    entries["etc/air6-p26.sha256"] = (
        stat.S_IFREG | 0o600, (record["p26_sha256"] + "\n").encode("ascii"), 0, 0)
    out = bytearray()
    for ino, name in enumerate(sorted(entries), 1):
        mode, data, major, minor = entries[name]
        out.extend(mod.newc_entry(name, mode, data, ino, major, minor))
        require(len(out) <= MAX_ARCHIVE, "ARCHIVE_OVERSIZE")
    out.extend(mod.newc_entry("TRAILER!!!", 0, ino=len(entries) + 1))
    require(len(out) <= MAX_ARCHIVE, "ARCHIVE_OVERSIZE")
    digest = hashlib.sha256(out).hexdigest()
    receipt = {
        "schema": "public-air6-p26-p44-bootstrap-v1",
        "scope": "EPHEMERAL_UNSIGNED_BOOTSTRAP_CPIO_NOT_AIR6_VALIDATED",
        "p26_bytes": PARTITION_BYTES,
        "p26_sha256": record["p26_sha256"],
        "cpio_bytes": len(out), "cpio_sha256": digest,
        "init_sha256": hashlib.sha256(source).hexdigest(),
        "entries": len(entries),
        "owner_rw_approval_embedded": False,
        "p44_partname_embedded": False,
        "activated_in_kernel": False,
        "device_boot_proven": False,
    }
    created = False
    try:
        with cpio_path.open("xb") as dst:
            created = True
            dst.write(out)
            dst.flush()
            os.fsync(dst.fileno())
        with receipt_path.open("x") as dst:
            dst.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except BaseException:
        if created:
            cpio_path.unlink(missing_ok=True)
        raise
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("rootfs", "p26-file", "p26-receipt", "output", "receipt"):
        ap.add_argument("--" + name, type=Path, required=True)
    a = ap.parse_args()
    record = package(a.rootfs, a.p26_file, a.p26_receipt, a.output, a.receipt)
    print("PUBLIC_AIR6_P26_P44_BOOTSTRAP_CPIO_BUILT", record["cpio_sha256"])
    print("LIMIT: explicit private P44 consent and real Air6 boot still not verified")


if __name__ == "__main__":
    main()
