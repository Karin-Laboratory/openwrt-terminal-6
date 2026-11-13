#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pack a verified, source-built OpenWrt staging root into unsigned 128 MiB p26.

No download, device access, signing or publication. Caller supplies a real
OpenWrt package/install root and a PRIVATE output directory. SquashFS
compression/layout follow the independently recorded R34 acceptance format;
the source of installed packages must be the public pinned OpenWrt build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

PARTITION_BYTES = 134_217_728
REQUIRED = ("bin/busybox", "sbin/procd", "sbin/ubusd", "sbin/netifd",
            "sbin/uci", "usr/sbin/dropbear", "etc/shadow")
FORBIDDEN = ("root/.ssh/authorized_keys", "etc/dropbear/dropbear_rsa_host_key",
             "etc/dropbear/dropbear_ed25519_host_key", "etc/config/wireless")


def require(ok, why):
    if not ok:
        raise ValueError("P26_BLOCKED_" + why)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_tree(root):
    require(root.is_dir() and not root.is_symlink(), "ROOTFS_NOT_REAL_DIRECTORY")
    require(root != Path("/"), "HOST_ROOT_FORBIDDEN")
    for name in REQUIRED:
        # Required executables must be inside the staged tree, not reached via
        # a parent-directory symlink into the build host.
        parts = Path(name).parts
        require(all(not (root / Path(*parts[:i])).is_symlink()
                    for i in range(1, len(parts))),
                "REQUIRED_PARENT_SYMLINK_" + name.replace("/", "_").upper())
        item = root / name
        require(item.is_file() and not item.is_symlink() and item.stat().st_size > 0,
                "MISSING_" + name.replace("/", "_").upper())
    shadow = (root / "etc/shadow").read_text()
    rows = [line for line in shadow.splitlines() if line.startswith("root:")]
    require(len(rows) == 1 and rows[0].split(":")[1].startswith(("!", "*")),
            "ROOT_ACCOUNT_NOT_LOCKED")
    # Do not follow symlinked ancestors when inspecting forbidden paths.
    # Otherwise a staged link can hide credentials outside the tree.
    for name in FORBIDDEN:
        parts = Path(name).parts
        require(all(not (root / Path(*parts[:i])).is_symlink()
                    for i in range(1, len(parts))),
                "FORBIDDEN_PARENT_SYMLINK_" + name.replace("/", "_").upper())
        item = root / name
        require(not item.exists() and not item.is_symlink(),
                "DEVICE_SECRET_OR_UNPROVISIONED_RADIO_" + name.replace("/", "_").upper())
    for directory in ("lib/firmware", "usr/lib/firmware"):
        parts = Path(directory).parts
        require(all(not (root / Path(*parts[:i])).is_symlink()
                    for i in range(1, len(parts))),
                "FIRMWARE_PARENT_SYMLINK")
        item = root / directory
        # A stock OpenWrt package/install may create an empty firmware
        # directory. Only reject real entries, not that harmless directory.
        # Symlinks (including dangling ones) and any nested payload are
        # never accepted without separate rights review.
        require(not item.is_symlink(), "FIRMWARE_RIGHTS_UNPROVEN")
        if item.exists():
            require(item.is_dir(), "FIRMWARE_RIGHTS_UNPROVEN")
            require(not any(item.iterdir()), "FIRMWARE_RIGHTS_UNPROVEN")
    # The staging root itself can carry capabilities or other xattrs too.
    # Checking only descendants would silently discard root-directory metadata.
    if hasattr(os, "listxattr"):
        try:
            root_attrs = os.listxattr(root, follow_symlinks=False)
        except OSError as exc:
            raise ValueError("P26_BLOCKED_XATTR_INSPECTION_FAILED") from exc
        require(not root_attrs, "XATTR_WOULD_BE_DROPPED")
    for path in root.rglob("*"):
        # OpenWrt legitimately uses in-filesystem absolute links such as /var -> /tmp.
        # Preserve them; the filesystem is not mounted or dereferenced by this validator.
        if not path.is_symlink():
            require(path.is_file() or path.is_dir(), "SPECIAL_FILE")
        # -no-xattrs would silently discard capabilities and other metadata.
        # Refuse such trees until a faithful metadata-preserving path exists.
        if hasattr(os, "listxattr"):
            try:
                attrs = os.listxattr(path, follow_symlinks=False)
            except OSError as exc:
                raise ValueError("P26_BLOCKED_XATTR_INSPECTION_FAILED") from exc
            require(not attrs, "XATTR_WOULD_BE_DROPPED")
        rel = path.relative_to(root).as_posix()
        require(not any(token in rel.lower() for token in
                ("dropbear_rsa_host_key", "dropbear_ed25519_host_key", "calibration", "eeprom.bin")),
                "CREDENTIAL_OR_CALIBRATION")
    require(not (root / "etc").is_symlink(), "AUTOSTART_PARENT_SYMLINK")
    rc = root / "etc/rc.d"
    require(not rc.is_symlink(), "AUTOSTART_DIRECTORY_SYMLINK")
    if rc.exists():
        for item in rc.iterdir():
            require(not any(x in item.name.lower() for x in ("dropbear", "wpad", "hostapd")),
                    "UNPROVISIONED_AUTOSTART")
    return True


def check_target_ownership(root):
    # OpenWrt system binaries and shadow must retain target root ownership.
    # A hosted runner may create a uniformly uid=1001 staging tree; matching
    # that tree in unsquashfs is not proof of faithful target metadata.
    for name in ("etc/shadow", "sbin/procd", "sbin/netifd", "sbin/ubusd"):
        metadata = (root / name).stat(follow_symlinks=False)
        require(metadata.st_uid == 0 and metadata.st_gid == 0,
                "TARGET_ROOT_OWNERSHIP_UNPROVEN_" + name.replace("/", "_").upper())
    return True


def produce(root, output, source_receipt):
    require(not root.is_symlink(), "ROOTFS_SYMLINK")
    require(all(not parent.is_symlink() for parent in root.parents),
            "ROOTFS_ANCESTOR_SYMLINK")
    root = root.resolve(strict=True)
    # Never write output inside the input tree: mksquashfs would ingest its
    # own output, and an ancestor symlink could conceal that relationship.
    require(not output.resolve().is_relative_to(root),
            "OUTPUT_INSIDE_INPUT_ROOTFS")
    # Reject linked output ancestors before inspecting source receipts.
    require(all(not parent.is_symlink() for parent in output.parents),
            "OUTPUT_ANCESTOR_SYMLINK")
    require(all(not parent.is_symlink() for parent in source_receipt.parents),
            "SOURCE_RECEIPT_ANCESTOR_SYMLINK")
    require(source_receipt.is_file() and not source_receipt.is_symlink(),
            "SOURCE_RECEIPT_REQUIRED")
    record = json.loads(source_receipt.read_text())
    require(record.get("openwrt_commit") ==
            "5799d2da76998be50432b0a3325b42713b4b619b",
            "UNPINNED_OPENWRT_SOURCE")
    require(record.get("package_install") is True and
            record.get("source_built") is True, "UNVERIFIED_PACKAGE_SOURCE")
    require(isinstance(record.get("packages"), list) and
            all(isinstance(p, str) and p for p in record["packages"]) and
            set(("base-files", "busybox", "procd", "ubus", "uci", "netifd", "dropbear")).issubset(record["packages"]),
            "INCOMPLETE_PACKAGE_INVENTORY")
    require(isinstance(record.get("feeds"), dict), "PINNED_FEEDS_RECEIPT_REQUIRED")
    check_tree(root)
    check_target_ownership(root)
    require(output.is_absolute() and not output.exists() and
            output.parent.is_dir() and not output.parent.is_symlink() and
            stat.S_IMODE(output.parent.stat().st_mode) & 0o077 == 0,
            "NEW_ABSOLUTE_OUTPUT_DIRECTORY_REQUIRED")
    require(shutil.which("mksquashfs") is not None and
            shutil.which("unsquashfs") is not None, "SQUASHFS_TOOLS_MISSING")
    os.umask(0o077)
    output.mkdir(mode=0o700)
    try:
        raw = output / "rootfs.squashfs"
        full = output / "rootfs_a.p26"
        # Fixed time improves repeatability; pin squashfs-tools version independently.
        # Exact byte reproducibility still depends on pinned squashfs-tools version.
        subprocess.run(["mksquashfs", str(root), str(raw), "-noappend", "-comp", "xz",
                        "-b", "262144", "-processors", "1", "-no-progress",
                        "-all-time", "0", "-mkfs-time", "0", "-no-xattrs"],
                       check=True, timeout=1800)
        size = raw.stat().st_size
        require(0 < size < PARTITION_BYTES, "SQUASHFS_EXCEEDS_P26")
        with raw.open("rb") as src, full.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
            dst.truncate(PARTITION_BYTES)  # Zero-padding, as in real R34.
        require(full.stat().st_size == PARTITION_BYTES, "PARTITION_SIZE")
        with raw.open("rb") as src, full.open("rb") as img:
            for chunk in iter(lambda: src.read(1 << 20), b""):
                require(img.read(len(chunk)) == chunk, "PREFIX_READBACK")
            for chunk in iter(lambda: img.read(1 << 20), b""):
                require(not chunk.strip(b"\x00"), "PADDING_NOT_ZERO")
        receipt = {"schema": 1, "status": "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK",
                   "partition_bytes": PARTITION_BYTES, "p26_sha256": digest(full),
                   "squashfs_bytes": size, "squashfs_sha256": digest(raw),
                   "openwrt_commit": record["openwrt_commit"],
                   "feeds": record.get("feeds"), "packages": record.get("packages"),
                   "squashfs_tools": subprocess.check_output(
                       ["mksquashfs", "-version"], text=True).splitlines()[0],
                   "signed": False, "hardware": "NONE", "public_binary": False}
        (output / "p26-receipt.json").write_text(json.dumps(receipt, indent=2,
                                                         sort_keys=True) + "\n")
        print("P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK", PARTITION_BYTES,
              receipt["p26_sha256"])
        return receipt

    except Exception:
        # Only remove the fresh directory created by this invocation.
        # Never touch the staging root, source receipt, or pre-existing paths.
        try:
            shutil.rmtree(output)
        except OSError as cleanup_error:
            # Preserve the manufacturing failure as the primary exception.
            # The incomplete directory remains for explicit operator cleanup.
            if hasattr(original_error := __import__("sys").exception(), "add_note"):
                original_error.add_note(f"P26 partial output cleanup failed: {cleanup_error}")
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    args = parser.parse_args()
    produce(args.rootfs, args.output, args.source_receipt)


if __name__ == "__main__":
    main()
