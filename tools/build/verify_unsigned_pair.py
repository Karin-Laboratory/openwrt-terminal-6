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
from pathlib import Path

P25_BYTES = 33_554_432
P26_BYTES = 134_217_728


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


def read_receipt(path):
    return json.loads(path.read_text(), object_pairs_hook=no_duplicate_keys)


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
    require(strict_int(p25_result["partition_bytes"], P25_BYTES) and
            p25_result["p25_sha256"] == digest(p25), "P25_IDENTITY")
    cfg = read_receipt(config)
    require(isinstance(cfg, dict), "P25_CONFIG_NOT_OBJECT")
    require(cfg.get("ramdisk_mode") == "kernel_embedded",
            "RC14_PROFILE_REQUIRES_KERNEL_EMBEDDED_INITRAMFS")
    init_check = initramfs_verify or initramfs_verifier().verify
    initramfs_result = init_check(initramfs_object, vmlinux, image, kernel,
                                  cpio, "xz")
    original = read_receipt(producer)
    approved = read_receipt(independent)
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
    require(approved.get("producer_receipt_sha256") == digest(producer),
            "P26_RECEIPT_IDENTITY")
    # The CPIO is verified against both Kbuild's linked initramfs section and
    # the exact ARM64 Image.gz; its P26 hash is a build binding, not proof the
    # early boot code ran on hardware.
    bound = (p26_hash + "  /dev/mmcblk0p26").encode("ascii")
    require(cpio.read_bytes().count(bound) == 1, "P26_INITRAMFS_SHA_BINDING")
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
        "p26_independent_receipt_sha256": digest(independent),
        "p25_config_sha256": digest(config),
        "bound_initramfs_sha256": digest(cpio),
        "initramfs_object_sha256": digest(initramfs_object),
        "kernel_image_sha256": initramfs_result["kernel_image_sha256"],
        "signed": False, "device_writes": False, "public_binary": False,
        "not_proven": ["Air6 LK accepts p25", "RC14 boot compatibility",
                       "hardware cold boot", "LAN/SSH", "publication rights"],
    }
    # Do not overwrite stale pair evidence.
    created = False
    try:
        with out.open("x", encoding="utf-8") as stream:
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
