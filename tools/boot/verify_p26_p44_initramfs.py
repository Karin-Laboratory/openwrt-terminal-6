#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent full-byte cpio/rootfs readback of P26/P44 /init research stage."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
from tools.boot import build_p26_p44_initramfs as producer

CPIO_READER = Path(__file__).resolve().parents[2] / "scripts/package-arm64-busybox-initramfs.py"


def verify(rootfs, p26_file, p26_receipt, cpio_file, receipt_file):
    rootfs, p26_file, p26_receipt, cpio_file, receipt_file = map(
        Path, (rootfs, p26_file, p26_receipt, cpio_file, receipt_file))
    for p in (p26_file, p26_receipt, cpio_file, receipt_file):
        if p.is_symlink() or not p.is_file():
            raise ValueError("BOOTSTAGE_NONREGULAR_INPUT")
    if rootfs.is_symlink() or not rootfs.is_dir():
        raise ValueError("BOOTSTAGE_ROOTFS")
    record = json.loads(receipt_file.read_text())
    source = json.loads(p26_receipt.read_text())
    if (record.get("schema") != "public-air6-p26-p44-bootstrap-v1" or
            record.get("scope") != "EPHEMERAL_UNSIGNED_BOOTSTRAP_CPIO_NOT_AIR6_VALIDATED" or
            source.get("partition_bytes") != producer.PARTITION_BYTES or
            p26_file.stat().st_size != producer.PARTITION_BYTES):
        raise ValueError("BOOTSTAGE_RECEIPT_OR_SIZE")
    p26_sha = producer.sha(p26_file)
    if source.get("p26_sha256") != p26_sha or record.get("p26_sha256") != p26_sha:
        raise ValueError("BOOTSTAGE_P26_SHA_MISMATCH")
    raw = cpio_file.read_bytes()
    if len(raw) != record.get("cpio_bytes") or hashlib.sha256(raw).hexdigest() != record.get("cpio_sha256"):
        raise ValueError("BOOTSTAGE_CPIO_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location("air6_cpio_reader", CPIO_READER)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    parsed = reader.unpack(raw)
    required = ("init", "etc/air6-p26.sha256", "bin/busybox", "sbin/procd",
                "sbin/init", "etc/preinit", "dev/console")
    if any(n not in parsed for n in required) or record.get("entries") != len(parsed) - 1:
        raise ValueError("BOOTSTAGE_CPIO_ENTRIES")
    if any(name in parsed for name in ("etc/air6-owner-p44-rw-go", "etc/air6-p44.partname")):
        raise ValueError("BOOTSTAGE_PRIVATE_CONSENT_INCLUDED")
    mode = record.get("boot_mode")
    if mode not in ("ram-experimental", "p44-required"):
        raise ValueError("BOOTSTAGE_BOOT_MODE_INVALID")
    if (record.get("p44_required") is not (mode == "p44-required") or
            record.get("p44_identity_gate") != "EXT4_RO_NOLOAD_MARKER_FS_STATE_UPPER_WORK" or
            record.get("p44_owner_secret_embedded") is not False):
        raise ValueError("BOOTSTAGE_P44_MODE_ATTESTATION")
    if record.get("management_autostart") is not False:
        raise ValueError("BOOTSTAGE_UNAPPROVED_MANAGEMENT_AUTOSTART")
    if mode == "p44-required":
        rel = producer.MANAGEMENT_REL
        audited = producer.MANAGEMENT_SOURCE.read_bytes()
        payload = parsed.get(rel)
        if (record.get("management_entry") != rel or
                record.get("management_sha256") != hashlib.sha256(audited).hexdigest() or
                payload is None or payload[1] != audited or
                not stat.S_ISREG(payload[0]) or
                stat.S_IMODE(payload[0]) != 0o755):
            raise ValueError("BOOTSTAGE_P26_MANAGEMENT_ENTRY_MISMATCH")
    elif record.get("management_entry") is not None or record.get("management_sha256") is not None:
        raise ValueError("BOOTSTAGE_RAM_MANAGEMENT_ATTESTATION")
    init = producer.BOOT_SCRIPT.read_bytes()
    marker = b"BOOT_MODE='ram-experimental'"
    if init.count(marker) != 1:
        raise ValueError("BOOTSTAGE_BOOT_MODE_TEMPLATE")
    if mode == "p44-required":
        init = init.replace(marker, b"BOOT_MODE='p44-required'")
    if (parsed["init"][1] != init or record.get("init_sha256") != hashlib.sha256(init).hexdigest() or
            not stat.S_ISREG(parsed["init"][0]) or
            not (parsed["init"][0] & 0o111)):
        raise ValueError("BOOTSTAGE_INIT_MISMATCH")
    if (parsed["etc/air6-p26.sha256"][1] != (p26_sha + "\n").encode() or
            parsed["etc/air6-p26.sha256"][0] & 0o777 != 0o600):
        raise ValueError("BOOTSTAGE_EXPECTED_SHA_INVALID")
    if (not stat.S_ISCHR(parsed["dev/console"][0]) or
            parsed["dev/console"][2:] != (5, 1)):
        raise ValueError("BOOTSTAGE_CONSOLE")
    # Independent inspection of *all* staged files and links, not producer manifest alone.
    disk_paths = set()
    for p in rootfs.rglob("*"):
        rel = p.relative_to(rootfs).as_posix()
        disk_paths.add(rel)
        if rel not in parsed:
            raise ValueError("BOOTSTAGE_MISSING_FILE_" + rel)
        mode, payload, _, _ = parsed[rel]
        info = p.lstat()
        if stat.S_IFMT(mode) != stat.S_IFMT(info.st_mode):
            raise ValueError("BOOTSTAGE_TYPE_MISMATCH_" + rel)
        if stat.S_ISREG(info.st_mode):
            if payload != p.read_bytes():
                raise ValueError("BOOTSTAGE_FILE_MISMATCH_" + rel)
        elif stat.S_ISLNK(info.st_mode):
            if payload != __import__("os").fsencode(__import__("os").readlink(p)):
                raise ValueError("BOOTSTAGE_SYMLINK_MISMATCH_" + rel)
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError("BOOTSTAGE_UNSUPPORTED_FILE_" + rel)
    allowed_extra = {"init", "etc/air6-p26.sha256", "dev", "proc", "sys", "mnt",
                     "etc", "dev/console", "dev/null"}
    if set(parsed) - {"TRAILER!!!"} - disk_paths - allowed_extra:
        raise ValueError("BOOTSTAGE_UNEXPECTED_ENTRY")
    if any(record.get(field) is not False for field in
           ("owner_rw_approval_embedded", "p44_partname_embedded",
            "activated_in_kernel", "device_boot_proven")):
        raise ValueError("BOOTSTAGE_MISLEADING_ACCEPTANCE")
    return {"status": "P26_P44_CPIO_INDEPENDENT_FULL_READBACK_PASS",
            "p26_sha256": p26_sha,
            "cpio_sha256": hashlib.sha256(raw).hexdigest(),
            "device_boot_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("rootfs", "p26-file", "p26-receipt", "cpio", "receipt"):
        ap.add_argument("--" + name, required=True, type=Path)
    a = ap.parse_args()
    print(json.dumps(verify(a.rootfs, a.p26_file, a.p26_receipt,
                            a.cpio, a.receipt), sort_keys=True))


if __name__ == "__main__":
    main()
