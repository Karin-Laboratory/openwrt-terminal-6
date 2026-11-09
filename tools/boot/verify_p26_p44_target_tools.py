#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect actual target-AArch64 BusyBox --list and staged rootfs commands.

The BusyBox applet list MUST be acquired by running the *target binary*
under isolated QEMU user emulation, never by executing host BusyBox.
An alternate standalone executable in rootfs is acceptable, but a symlink
to BusyBox is only acceptable if that applet is actually compiled in.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import stat

REQUIRED = ("sh", "mount", "umount", "sha256sum", "switch_root",
            "grep", "cat", "readlink", "cmp", "mkdir", "sleep")
DIRECTORIES = ("bin", "sbin", "usr/bin", "usr/sbin")


def _target_path(rootfs, path):
    """Resolve links *inside* an isolated rootfs, rejecting escapes/cycles."""
    seen = set()
    path = PurePosixPath(path)
    for _ in range(20):
        if path.is_absolute():
            raise ValueError("TARGET_PATH_ESCAPE")
        # Normalize in a synthetic *target* root. '../' is legitimate for
        # sbin/switch_root -> ../bin/busybox, but may never cross above /.
        parts = []
        for component in path.parts:
            if component in ("", "."):
                continue
            if component == "..":
                if not parts:
                    raise ValueError("TARGET_PATH_ESCAPE")
                parts.pop()
            else:
                parts.append(component)
        if not parts:
            raise ValueError("TARGET_PATH_ESCAPE")
        path = PurePosixPath(*parts)
        item = Path(rootfs).joinpath(*parts)
        if any((Path(rootfs) / PurePosixPath(*parts[:i])).is_symlink()
               for i in range(1, len(parts))):
            raise ValueError("TARGET_PATH_ANCESTOR_SYMLINK")
        if not item.is_symlink():
            return item
        if str(path) in seen:
            raise ValueError("TARGET_PATH_SYMLINK_LOOP")
        seen.add(str(path))
        target = item.readlink()
        if target.is_absolute():
            path = PurePosixPath(str(target).lstrip("/"))
        else:
            path = path.parent / target
    raise ValueError("TARGET_PATH_LINK_DEPTH")


def validate(rootfs, target_applet_list):
    rootfs = Path(rootfs)
    if rootfs.is_symlink() or not rootfs.is_dir():
        raise ValueError("TARGET_ROOTFS_NOT_DIRECTORY")
    if not isinstance(target_applet_list, str):
        raise ValueError("TARGET_APPLET_LIST_INVALID")
    applets = set(target_applet_list.splitlines())
    if any(not name or "/" in name or name.strip() != name for name in applets):
        raise ValueError("TARGET_APPLET_LIST_INVALID")
    busybox = _target_path(rootfs, "bin/busybox")
    if not busybox.is_file() or not busybox.stat().st_mode & 0o111:
        raise ValueError("TARGET_BUSYBOX_MISSING")
    results = {}
    for name in REQUIRED:
        if name in applets:
            results[name] = "target-busybox-applet"
            continue
        choices = []
        for directory in DIRECTORIES:
            candidate = PurePosixPath(directory, name)
            loc = rootfs / str(candidate)
            if loc.exists() or loc.is_symlink():
                resolved = _target_path(rootfs, candidate)
                if (resolved.is_file() and resolved.stat().st_mode & 0o111 and
                    resolved != busybox):
                    choices.append(str(candidate))
        if not choices:
            raise ValueError("TARGET_COMMAND_NOT_AVAILABLE:" + name)
        results[name] = "target-executable:" + choices[0]
    return {"status": "TARGET_BUSYBOX_RUNTIME_APPLETS_PASS",
            "commands": results, "host_busybox_was_used": False,
            "air6_boot_or_mount_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rootfs", type=Path, required=True)
    ap.add_argument("--target-busybox-applets", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(validate(a.rootfs, a.target_busybox_applets.read_text()),
                     sort_keys=True))


if __name__ == "__main__":
    main()
