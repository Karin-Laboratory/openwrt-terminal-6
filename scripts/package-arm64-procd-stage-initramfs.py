#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Embed the real pinned musl procd rootfs *stage* as an unsigned kernel initramfs.

Build-only research input. No preinit/service config, hardware boot, install,
signing, network configuration, or public firmware distribution is authorized.
"""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sbat6_cpio", ROOT / "scripts/package-arm64-busybox-initramfs.py"
)
cpio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpio)

BINARIES = ("bin/busybox", "bin/ubus", "sbin/ubusd",
            "sbin/uci", "sbin/init", "sbin/procd")
DIRS = ("bin", "sbin", "etc", "dev", "proc", "sys", "tmp", "var", "var/run")
EXPECTED = set(BINARIES) | set(DIRS) | {"bin/sh"}
SOURCE_SCOPE = "NONINSTALLABLE_SBAT6_MUSL_BUSYBOX_UBUSD_UBUS_UCI_PROCD_INIT_SERVICE_ROOTFS_STAGE"


def package(rootfs: Path, source_manifest: Path, output: Path, manifest_out: Path) -> dict:
    for path in (rootfs, source_manifest):
        if path.is_symlink() or not path.is_file():
            raise ValueError("source must be a regular file")
    if output == manifest_out or any(p.exists() or p.is_symlink() for p in (output, manifest_out)):
        raise ValueError("outputs must be distinct and absent")
    blob = rootfs.read_bytes()
    source = json.loads(source_manifest.read_text())
    if (source.get("scope") != SOURCE_SCOPE or source.get("architecture") != "aarch64"
            or source.get("libc") != "native-musl-static-1.2.5"
            or source.get("rights_review") != "pending"
            or source.get("archive_sha256") != hashlib.sha256(blob).hexdigest()
            or source.get("archive_bytes") != len(blob)):
        raise ValueError("rootfs stage provenance/identity mismatch")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) != len(EXPECTED) or {m.name for m in members} != EXPECTED:
            raise ValueError("unexpected rootfs stage members")
        by_name = {m.name: m for m in members}
        if any(not by_name[name].isdir() for name in DIRS):
            raise ValueError("invalid directory")
        if not by_name["bin/sh"].issym() or by_name["bin/sh"].linkname != "busybox":
            raise ValueError("unexpected shell link")
        payloads = {}
        for name in BINARIES:
            member = by_name[name]
            if not member.isfile():
                raise ValueError("expected regular executable: " + name)
            payload = archive.extractfile(member).read()
            cpio.elf_check.check_static_aarch64_elf(payload)
            if source.get("files_sha256", {}).get(name) != hashlib.sha256(payload).hexdigest():
                raise ValueError("ELF identity mismatch: " + name)
            payloads[name] = payload
    records = [(name, stat.S_IFDIR | 0o755, b"", 0, 0) for name in DIRS]
    records.extend((name, stat.S_IFREG | 0o755, payloads[name], 0, 0) for name in BINARIES)
    records.extend((
        ("bin/sh", stat.S_IFLNK | 0o777, b"busybox", 0, 0),
        ("init", stat.S_IFLNK | 0o777, b"sbin/init", 0, 0),
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3),
    ))
    raw = b"".join(cpio.entry(name, mode, data, i, major, minor)
                   for i, (name, mode, data, major, minor) in enumerate(records, 1))
    raw += cpio.entry("TRAILER!!!", 0, b"", len(records) + 1)
    parsed = cpio.unpack(raw)
    if (set(parsed) != {name for name, *_ in records} | {"TRAILER!!!"}
            or parsed["init"][1] != b"sbin/init"
            or parsed["dev/console"][2:] != (5, 1)):
        raise ValueError("cpio roundtrip mismatch")
    for name, data in payloads.items():
        if parsed[name][1] != data:
            raise ValueError("cpio executable mismatch: " + name)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    if cpio.unpack(gzip.decompress(compressed)) != parsed:
        raise ValueError("gzip roundtrip mismatch")
    record = {
        "scope": "NONINSTALLABLE_AIR6_PROCD_STAGE_EMBEDDED_INITRAMFS",
        "architecture": "aarch64",
        "libc": "native-musl-static-1.2.5",
        "rootfs_stage_sha256": source["archive_sha256"],
        "files_sha256": source["files_sha256"],
        "initramfs_sha256": hashlib.sha256(compressed).hexdigest(),
        "initramfs_bytes": len(compressed),
        "init": "symlink-to-real-upstream-procd-init-ELF",
        "rights_review": "pending",
        "not_proven": ["procd PID1 runtime", "preinit/service startup", "netifd",
                       "Wi-Fi AP", "Air6 boot", "release rights"],
    }
    output.write_bytes(compressed)
    manifest_out.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record


if __name__ == "__main__":
    try:
        if len(sys.argv) != 5:
            raise ValueError("usage: package-arm64-procd-stage-initramfs.py ROOTFS_TAR_GZ ROOTFS_MANIFEST NEW_CPIO_GZ NEW_MANIFEST")
        result = package(*(Path(p) for p in sys.argv[1:]))
        print("SBAT6_PROCD_STAGE_CPIO_WITH_REAL_PID1_PASS", json.dumps(result, sort_keys=True))
        print("LIMIT: no preinit or services, no verified PID1 execution, netifd, AP or hardware boot")
    except (OSError, ValueError, tarfile.TarError) as exc:
        print("SBAT6_PROCD_STAGE_CPIO_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
