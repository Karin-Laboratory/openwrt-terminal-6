#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link independently checked unsigned p25/p26 in a private same-run pair receipt.

No signing, flashing, board-specific boot values, or binary publication.
P26 filesystem readback must have been completed by its separate verifier.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path

P25_BYTES = 33_554_432
P26_BYTES = 134_217_728
MAX_RECEIPT_BYTES = 1024 * 1024


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_nonfinite(value):
    raise ValueError("UNSIGNED_PAIR_BLOCKED_NONFINITE_JSON_CONSTANT")


def read_receipt(path):
    # Reject symlinked ancestor directories as well as the final component.
    # O_NOFOLLOW alone only protects the final pathname component.
    require(not any(p.is_symlink() for p in Path(path).parents),
            "RECEIPT_SYMLINK_OR_INVALID_PATH")
    # Bind validation and receipt identity to the same bytes, even if the
    # pathname is replaced between validation and attestation.
    # Open the actual file without following a final-component symlink. The
    # initial valid_path check alone cannot prevent pathname replacement.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "RECEIPT_NOT_REGULAR")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
    finally:
        os.close(fd)
    require(len(raw) <= MAX_RECEIPT_BYTES, "RECEIPT_TOO_LARGE")
    return json.loads(raw, object_pairs_hook=no_duplicate_keys,
                      parse_constant=reject_nonfinite), hashlib.sha256(raw).hexdigest()


def strict_int(value, expected):
    return type(value) is int and value == expected


def require(ok, reason):
    if not ok:
        raise ValueError("UNSIGNED_PAIR_BLOCKED_" + reason)


def valid_path(path):
    return (path.is_file() and not path.is_symlink()
            and not any(p.is_symlink() for p in path.parents))


def p25_verifier():
    path = Path(__file__).resolve().parents[1] / "boot/verify_p25_independent.py"
    spec = importlib.util.spec_from_file_location("public_p25_independent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def initramfs_verifier():
    path = Path(__file__).resolve().parents[1] / "boot/verify_kernel_initramfs.py"
    spec = importlib.util.spec_from_file_location("public_kernel_initramfs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_pair(p25, kernel, ramdisk, dtb, config, p26, producer,
                independent, cpio, initramfs_object, vmlinux, image, out,
                dtb_prefix=None, p25_verify=None, initramfs_verify=None):
    paths = [p25, kernel, ramdisk, dtb, config, p26, producer, independent,
             cpio, initramfs_object, vmlinux, image]
    if dtb_prefix is not None:
        paths.append(dtb_prefix)
    require(all(valid_path(p) for p in paths), "INVALID_INPUT")
    require(not out.exists() and not out.is_symlink()
            and out.parent.is_dir()
            and not any(p.is_symlink() for p in out.parents),
            "OUTPUT_EXISTS_OR_SYMLINK")
    # Independently recheck the p25 including all boot-sensitive config bytes.
    check = p25_verify or p25_verifier().verify
    p25_result = check(p25, kernel, ramdisk, dtb, config, dtb_prefix)
    require(isinstance(p25_result, dict) and
            strict_int(p25_result.get("partition_bytes"), P25_BYTES) and
            strict_int(p25_result.get("header_version"), 2) and
            p25_result.get("scope") == "UNSIGNED_V2_BYTE_LAYOUT_ONLY" and
            p25_result.get("ramdisk_mode") == "kernel_embedded" and
            p25_result.get("p25_sha256") == digest(p25), "P25_IDENTITY")
    cfg, config_hash = read_receipt(config)
    require(isinstance(cfg, dict), "P25_CONFIG_NOT_OBJECT")
    require(cfg.get("ramdisk_mode") == "kernel_embedded",
            "RC14_PROFILE_REQUIRES_KERNEL_EMBEDDED_INITRAMFS")
    # Snapshot the linked object before attestation; a digest first taken at
    # receipt construction cannot detect a post-attestation mutation.
    initramfs_object_hash = digest(initramfs_object)
    init_check = initramfs_verify or initramfs_verifier().verify
    initramfs_result = init_check(initramfs_object, vmlinux, image, kernel,
                                  cpio, "xz")
    require(isinstance(initramfs_result, dict) and
            initramfs_result.get("status") ==
            "ARM64_KERNEL_INITRAMFS_OBJECT_AND_IMAGE_VERIFIED" and
            initramfs_result.get("compression") == "xz" and
            initramfs_result.get("cpio_sha256") == digest(cpio) and
            initramfs_result.get("kernel_image_sha256") == digest(image) and
            initramfs_result.get("kernel_gzip_sha256") == digest(kernel),
            "INITRAMFS_ATTESTATION_IDENTITY")
    original, producer_hash = read_receipt(producer)
    approved, independent_hash = read_receipt(independent)
    require(isinstance(original, dict), "P26_PRODUCER_NOT_OBJECT")
    require(isinstance(approved, dict), "P26_ATTESTATION_NOT_OBJECT")
    require(strict_int(original.get("schema"), 1) and
            original.get("status") == "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK"
            and original.get("signed") is False and
            original.get("hardware") == "NONE", "P26_PRODUCER_STATUS")
    require(strict_int(approved.get("schema"), 1) and
            approved.get("status") == "P26_INDEPENDENT_FS_READBACK_VERIFIED" and
            approved.get("signed") is False and
            approved.get("hardware") == "NONE" and
            approved.get("verification") ==
            "INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA",
            "P26_NOT_INDEPENDENTLY_VERIFIED")
    require(p26.stat().st_size == P26_BYTES and
            strict_int(original.get("partition_bytes"), P26_BYTES) and
            strict_int(approved.get("partition_bytes"), P26_BYTES),
            "P26_SIZE")
    p26_hash = digest(p26)
    require(p26_hash == original.get("p26_sha256") ==
            approved.get("p26_sha256"), "P26_IMAGE_IDENTITY")
    require(approved.get("producer_receipt_sha256") == producer_hash,
            "P26_RECEIPT_IDENTITY")
    # The CPIO is verified against both Kbuild's linked initramfs section and
    # the exact ARM64 Image.gz; its P26 hash is a build binding, not proof the
    # early boot code ran on hardware.
    bound = (p26_hash + "  /dev/mmcblk0p26").encode("ascii")
    # Scan with overlap so a marker spanning two chunks is still counted.
    # A real initramfs may be large; do not load its entire contents into RAM.
    matches = 0
    tail = b""
    scanned_hash = hashlib.sha256()
    with cpio.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            scanned_hash.update(chunk)
            data = tail + chunk
            matches += data.count(bound)
            tail = data[-(len(bound) - 1):]
    # Bind the marker scan to the exact bytes independently attested above.
    # Otherwise an input replaced after the first digest could be scanned
    # successfully even though the receipt describes different CPIO bytes.
    require(scanned_hash.hexdigest() == initramfs_result["cpio_sha256"],
            "CPIO_CHANGED_DURING_VERIFICATION")
    require(matches == 1, "P26_INITRAMFS_SHA_BINDING")
    # A pair receipt must not accept arbitrary equal strings as a digest.
    # The separate independent verifier establishes the filesystem identity.
    squashfs_hash = original.get("squashfs_sha256")
    require(type(squashfs_hash) is str and len(squashfs_hash) == 64 and
            all(ch in "0123456789abcdef" for ch in squashfs_hash),
            "P26_SQUASHFS_IDENTITY")
    require(type(original.get("squashfs_bytes")) is int and
            type(approved.get("squashfs_bytes")) is int and
            0 < original["squashfs_bytes"] < P26_BYTES and
            original.get("squashfs_sha256") ==
            approved.get("squashfs_sha256") and
            original["squashfs_bytes"] ==
            approved["squashfs_bytes"], "P26_SQUASHFS_IDENTITY")
    receipt = {
        "schema": 1, "status": "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED",
        "p25_sha256": p25_result["p25_sha256"],
        "p26_sha256": p26_hash,
        "p26_independent_receipt_sha256": independent_hash,
        "p25_config_sha256": config_hash,
        "bound_initramfs_sha256": scanned_hash.hexdigest(),
        "initramfs_object_sha256": initramfs_object_hash,
        "kernel_image_sha256": initramfs_result["kernel_image_sha256"],
        "signed": False, "device_writes": False, "public_binary": False,
        "not_proven": ["Air6 LK accepts p25", "RC14 boot compatibility",
                       "hardware cold boot", "LAN/SSH", "publication rights"],
    }
    # The linked kernel artifacts are attested earlier. Reject a later edit
    # before recording their identities in the same-run receipt.
    require(digest(kernel) == initramfs_result["kernel_gzip_sha256"],
            "KERNEL_GZIP_CHANGED_BEFORE_RECEIPT")
    require(digest(image) == initramfs_result["kernel_image_sha256"],
            "KERNEL_IMAGE_CHANGED_BEFORE_RECEIPT")
    require(digest(initramfs_object) == receipt["initramfs_object_sha256"],
            "INITRAMFS_OBJECT_CHANGED_BEFORE_RECEIPT")
    # Recheck p25 after all other inputs were scanned. A concurrent replacement
    # must not yield a receipt for bytes different from the verified boot image.
    require(digest(p25) == p25_result["p25_sha256"],
            "P25_CHANGED_DURING_VERIFICATION")
    # Rehash p26 after CPIO and receipt checks; the initial hash alone does
    # not protect against an in-place edit during later verification.
    require(digest(p26) == p26_hash, "P26_CHANGED_DURING_VERIFICATION")
    # The scan proves CPIO identity at scan time; reject a later in-place
    # change before recording the bound initramfs in the final receipt.
    require(digest(cpio) == scanned_hash.hexdigest(),
            "CPIO_CHANGED_BEFORE_RECEIPT")
    # The metadata receipts are part of the provenance chain. Reject edits
    # after parsing instead of recording a hash for bytes no longer present.
    require(digest(config) == config_hash, "P25_CONFIG_CHANGED")
    require(digest(producer) == producer_hash, "P26_PRODUCER_RECEIPT_CHANGED")
    require(digest(independent) == independent_hash,
            "P26_INDEPENDENT_RECEIPT_CHANGED")
    # Do not overwrite stale pair evidence.
    created = False
    try:
        with os.fdopen(os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       "w", encoding="utf-8") as stream:
            created = True
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Persist the new directory entry, not only the receipt contents.
        directory_fd = os.open(out.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        if created:
            try:
                out.unlink(missing_ok=True)
                directory_fd = os.open(out.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass  # Preserve the original write/sync failure.
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("p25", "kernel", "ramdisk", "dtb", "config",
                 "p26", "producer", "independent", "cpio",
                 "initramfs-object", "vmlinux", "image", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--dtb-prefix", type=Path)
    a = parser.parse_args()
    result = verify_pair(a.p25, a.kernel, a.ramdisk, a.dtb, a.config,
                         a.p26, a.producer, a.independent, a.cpio,
                         a.initramfs_object, a.vmlinux, a.image, a.out,
                         dtb_prefix=a.dtb_prefix)
    print("PUBLIC_UNSIGNED_P25_P26_PAIR_BYTE_IDENTITIES_PASS",
          result["p25_sha256"], result["p26_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
