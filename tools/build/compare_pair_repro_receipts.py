#!/usr/bin/env python3
"""Compare independent public unsigned P25/P26 build receipts, without firmware bytes.

Origin: independently authored for this repository; SPDX-License-Identifier: MIT.
This is a metadata gate, not proof of matching underlying image bytes.
"""
import argparse
import hashlib
import json
import math
import os
import stat

MAX_RECEIPT_BYTES = 65536

FIELDS = (
    "p25_sha256", "p26_sha256", "bound_initramfs_sha256",
    "kernel_image_sha256", "initramfs_object_sha256", "p25_config_sha256",
)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number: " + value)
    return number


def load_with_identity(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as receipt:
        identity = os.fstat(receipt.fileno())
        if not stat.S_ISREG(identity.st_mode):
            raise ValueError("receipt must be a regular file")
        data = receipt.read(MAX_RECEIPT_BYTES + 1)
        after = os.fstat(receipt.fileno())
        if (identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns, identity.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("receipt changed during read")
    if len(data) != identity.st_size:
        raise ValueError("receipt short read or size mismatch")
    if len(data) > MAX_RECEIPT_BYTES:
        raise ValueError("receipt exceeds maximum size")
    obj = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_float=finite_json_float,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonstandard JSON constant: " + value)),
    )
    if not isinstance(obj, dict):
        raise ValueError("receipt must be an object")
    if (type(obj.get("schema")) is not int or obj["schema"] != 1 or
            obj.get("status") != "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED" or
            obj.get("signed") is not False or
            obj.get("device_writes") is not False or
            obj.get("public_binary") is not False):
        raise ValueError("invalid unsigned pair receipt status or safety flags")
    for field in FIELDS:
        value = obj.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(
            ch not in "0123456789abcdef" for ch in value
        ):
            raise ValueError("missing or malformed SHA-256: " + field)
    return obj, (identity.st_dev, identity.st_ino)


def load(path):
    return load_with_identity(path)[0]


def compare(a, b):
    return [field for field in FIELDS if a[field] != b[field]]


def verify_image(path, expected_digest, expected_size, return_identity=False):
    """Read the entire local image, rejecting symlinks and truncated files."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
                 getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
            raise ValueError("image is not a regular file of expected size")
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            count += len(chunk)
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                         after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("image changed during read")
        if count != expected_size or digest.hexdigest() != expected_digest:
            raise ValueError("image bytes do not match receipt")
    if return_identity:
        return (digest.hexdigest(), (before.st_dev, before.st_ino))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_a")
    parser.add_argument("workspace_b")
    parser.add_argument("--require-images", action="store_true",
                        help="fail closed unless all four P25/P26 image paths are supplied")
    parser.add_argument("--p25-a")
    parser.add_argument("--p25-b")
    parser.add_argument("--p26-a")
    parser.add_argument("--p26-b")
    args = parser.parse_args()
    image_paths = (args.p25_a, args.p25_b, args.p26_a, args.p26_b)
    if args.require_images and not all(image_paths):
        parser.error("--require-images requires all four image paths")
    if any(image_paths) and not all(image_paths):
        parser.error("all four image paths are required for byte verification")
    try:
        a, identity_a = load_with_identity(args.workspace_a)
        b, identity_b = load_with_identity(args.workspace_b)
        if identity_a == identity_b:
            raise ValueError("workspace A and B must be different receipt files")
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        parser.exit(2, "REPRO_RECEIPT_INVALID: " + str(exc) + "\n")
    if all(image_paths):
        try:
            image_identities = {}
            for path, receipt, field, size in (
                (args.p25_a, a, "p25_sha256", 32 * 1024 * 1024),
                (args.p25_b, b, "p25_sha256", 32 * 1024 * 1024),
                (args.p26_a, a, "p26_sha256", 128 * 1024 * 1024),
                (args.p26_b, b, "p26_sha256", 128 * 1024 * 1024),
            ):
                _, identity = verify_image(path, receipt[field], size, return_identity=True)
                if identity in image_identities:
                    raise ValueError("image paths must refer to four distinct files: " + image_identities[identity] + " and " + field)
                image_identities[identity] = field
        except (OSError, ValueError) as exc:
            parser.exit(2, "REPRO_IMAGE_INVALID: " + str(exc) + "\n")
        print("REPRO_IMAGE_FULL_READBACK_PASS")
    differences = compare(a, b)
    for field in FIELDS:
        print("REPRO_" + field.upper() + "=" + ("DIFF" if field in differences else "MATCH"))
    if differences:
        print("REPRO_RECEIPT_MISMATCH: " + ",".join(differences))
        return 1
    print("REPRO_RECEIPT_HASHES_MATCH; " + ("local image readback verified" if all(image_paths) else "independent byte verification remains required"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
