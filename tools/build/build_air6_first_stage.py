#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build experimental source-owned first-stage CPIO; no private RC14 code/assets.

Composes native OpenWrt BusyBox, its public-source runtime libs, an independently
authored /init and immutable SHA of the same-run verified P26. No device access.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import stat

P26_BYTES = 134_217_728
HERE = Path(__file__).resolve().parents[2]
REQUIRED_APPLETS = ("sh", "mount", "umount", "mkdir", "grep", "sleep",
                    "sha256sum", "cat", "readlink", "ln", "sync",
                    "switch_root")


def require(ok, code):
    if not ok:
        raise ValueError("FIRST_STAGE_BLOCKED_" + code)


def build(root, p26, out):
    require(root.is_dir() and not root.is_symlink(), "ROOTFS")
    require(p26.is_file() and not p26.is_symlink()
            and p26.stat().st_size == P26_BYTES, "P26_IDENTITY")
    require(not out.exists() and not out.is_symlink()
            and out.parent.is_dir(), "OUTPUT")
    bb = root / "bin/busybox"
    require(bb.is_file() and not bb.is_symlink() and bb.stat().st_size > 1024,
            "NATIVE_BUSYBOX")
    require(bb.read_bytes()[:6] == b"\x7fELF\x02\x01", "BUSYBOX_ELF64")
    import struct
    require(struct.unpack_from("<H", bb.read_bytes()[:32], 18)[0] == 183,
            "BUSYBOX_NOT_AARCH64")
    script = HERE / "tools/boot/air6_first_stage.sh"
    checker = HERE / "tools/boot/verify_bound_p26.sh"
    p44_state = HERE / "tools/boot/prepare_p44_state.sh"
    require(script.is_file() and checker.is_file() and p44_state.is_file(),
            "PUBLIC_SOURCES")
    for item in ("etc", "lib", "bin"):
        require(not (root / item).is_symlink(), "ROOTFS_PARENT_SYMLINK")
    import hashlib
    p26hash = hashlib.sha256()
    with p26.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            p26hash.update(block)
    sha = p26hash.hexdigest()
    spec = importlib.util.spec_from_file_location(
        "air6_cpio", HERE / "scripts/build-minimal-arm64-initramfs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    entries = {}
    def put(name, mode, payload=b"", major=0, minor=0):
        require(name not in entries, "DUPLICATE_ENTRY")
        entries[name] = (mode, payload, major, minor)
    for d in ("bin", "sbin", "lib", "dev", "proc", "sys", "usr",
              "usr/libexec", "usr/libexec/air6", "etc", "etc/air6",
              "mnt", "mnt/air6", "mnt/air6/rom", "mnt/air6/check",
              "mnt/air6/rw", "mnt/air6/newroot"):
        put(d, stat.S_IFDIR | 0o755)
    put("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1)
    put("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3)
    put("bin/busybox", stat.S_IFREG | 0o755, bb.read_bytes())
    for applet in REQUIRED_APPLETS:
        path = ("sbin/" if applet == "switch_root" else "bin/") + applet
        put(path, stat.S_IFLNK | 0o777,
            b"../bin/busybox" if applet == "switch_root" else b"busybox")
    # Source-built dynamic busybox needs its exact libc; support both common
    # OpenWrt musl aliases without dereferencing links outside the staged tree.
    for name in ("lib/libc.so", "lib/ld-musl-aarch64.so.1", "lib/libgcc_s.so.1"):
        src = root / name
        if src.is_symlink():
            value = os.readlink(src)
            require(not value.startswith("/") and ".." not in Path(value).parts,
                    "LIBRARY_SYMLINK_OUTSIDE")
            put(name, stat.S_IFLNK | 0o777, os.fsencode(value))
        elif src.is_file():
            put(name, stat.S_IFREG | 0o755, src.read_bytes())
        else:
            require(name == "lib/libgcc_s.so.1", "MISSING_LIBC")
    put("etc/air6/p26.sha256", stat.S_IFREG | 0o444,
        (sha + "  /dev/mmcblk0p26\n").encode("ascii"))
    put("usr/libexec/air6/verify-bound-p26", stat.S_IFREG | 0o755,
        checker.read_bytes())
    put("usr/libexec/air6/prepare-p44-state", stat.S_IFREG | 0o755,
        p44_state.read_bytes())
    put("init", stat.S_IFREG | 0o755, script.read_bytes())
    result = bytearray()
    for ino, name in enumerate(sorted(entries), 1):
        mode, contents, major, minor = entries[name]
        result += mod.newc_entry(name, mode, contents, ino, major, minor)
    result += mod.newc_entry("TRAILER!!!", 0, ino=len(entries) + 1)
    require(len(result) < 32 * 1024 * 1024, "INITRAMFS_SIZE")
    out.write_bytes(result)
    print("PUBLIC_AIR6_FIRST_STAGE_CPIO_SOURCE_BUILT_PASS",
          len(result), sha)
    return {"p26_sha256": sha, "cpio_sha256": hashlib.sha256(result).hexdigest(),
            "entries": len(entries), "first_stage_wired": True,
            "hardware_boot": False}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for name in ("rootfs", "p26", "output"):
        ap.add_argument("--" + name, required=True, type=Path)
    args = ap.parse_args()
    try:
        build(args.rootfs, args.p26, args.output)
    except (ValueError, OSError) as err:
        raise SystemExit(str(err))
