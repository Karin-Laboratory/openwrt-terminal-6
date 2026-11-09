#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed post-olddefconfig gate for P26(XZ SquashFS)/P44(ext4) bootstrap.

Checking requested Kconfig alone is insufficient; inspect the real Kbuild
.config AFTER olddefconfig and BEFORE claiming a runnable image. This gate
does not assert a wired MT6990 MMC controller, bootloader or hardware support.
"""
import argparse
from pathlib import Path
import struct

BUILTIN = (
    "CONFIG_MMC",
    "CONFIG_MMC_BLOCK",
    "CONFIG_EFI_PARTITION",
    "CONFIG_EXT4_FS",
    "CONFIG_SQUASHFS",
    "CONFIG_SQUASHFS_XZ",
    "CONFIG_XZ_DEC",
    "CONFIG_OVERLAY_FS",
    "CONFIG_DEVTMPFS",
    "CONFIG_DEVTMPFS_MOUNT",
    "CONFIG_PROC_FS",
    "CONFIG_SYSFS",
    "CONFIG_TMPFS",
)
P26_BYTES = 134_217_728
SQUASHFS_MAGIC = b"hsqs"
SQUASHFS_XZ_COMPRESSION = 4


def parse_config(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("ascii")
    symbols = {}
    for line in raw.splitlines():
        if not line.startswith("CONFIG_") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key in symbols:
            raise ValueError("BOOT_KCONFIG_DUPLICATE_" + key)
        symbols[key] = val
    return symbols


def check_config(raw):
    symbols = parse_config(raw)
    missing = [key for key in BUILTIN if symbols.get(key) != "y"]
    if missing:
        raise ValueError("P26_P44_KERNEL_NOT_BUILTIN:" + ",".join(missing))
    return {"kernel_config": "P26_P44_BOOT_FILESYSTEM_BUILTIN_PASS",
            "required_builtin": len(BUILTIN),
            "device_mmc_controller_proven": False,
            "physical_rootfs_switch_proven": False}


def check_squashfs_header(p26):
    """Validate actual 128MiB packed p26 prefix, never copy firmware bytes."""
    p26 = Path(p26)
    if p26.is_symlink() or not p26.is_file() or p26.stat().st_size != P26_BYTES:
        raise ValueError("P26_PARTITION_BYTES")
    with p26.open("rb") as stream:
        sb = stream.read(96)
    if len(sb) != 96 or sb[:4] != SQUASHFS_MAGIC:
        raise ValueError("P26_SQUASHFS_MAGIC")
    comp = struct.unpack_from("<H", sb, 20)[0]
    major, minor = struct.unpack_from("<HH", sb, 28)
    used = struct.unpack_from("<Q", sb, 40)[0]
    if comp != SQUASHFS_XZ_COMPRESSION:
        raise ValueError("P26_NOT_XZ_SQUASHFS")
    if (major, minor) != (4, 0) or used < 96 or used > P26_BYTES:
        raise ValueError("P26_SQUASHFS_SUPERBLOCK")
    return {"p26_bytes": P26_BYTES, "squashfs_bytes_used": used,
            "squashfs_compression": "xz",
            "kernel_must_include": ["CONFIG_SQUASHFS=y", "CONFIG_SQUASHFS_XZ=y", "CONFIG_XZ_DEC=y"],
            "device_boot_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel-config", type=Path, required=True)
    ap.add_argument("--p26", type=Path, required=True)
    a = ap.parse_args()
    print(check_config(a.kernel_config.read_bytes()))
    print(check_squashfs_header(a.p26))
    print("LIMIT: Kconfig and SquashFS/XZ format only, no P44 mounting or C-unit MMC proof")


if __name__ == "__main__":
    main()
