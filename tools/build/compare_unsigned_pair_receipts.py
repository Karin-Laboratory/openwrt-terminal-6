#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare independently generated unsigned pair receipts without firmware disclosure."""
import argparse
import json
import os
import stat
from pathlib import Path

FIELDS = ('p25_sha256', 'p26_sha256', 'bound_initramfs_sha256', 'kernel_image_sha256', 'initramfs_object_sha256', 'p25_config_sha256')

def load(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('DUPLICATE_KEY')
            d[k] = v
        return d
    # Fail closed on platforms without no-follow opens; silently dropping this
    # flag would permit a symlink swap after any path preflight.
    if not hasattr(os, 'O_NOFOLLOW'):
        raise ValueError('NOFOLLOW_UNAVAILABLE')
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('RECEIPT_NOT_REGULAR')
        if info.st_size > 1024 * 1024:
            raise ValueError('RECEIPT_TOO_LARGE')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('RECEIPT_TOO_LARGE')
        after = os.fstat(fd)
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or len(raw) != after.st_size:
            raise ValueError('RECEIPT_CHANGED_DURING_READ')
    finally:
        os.close(fd)
    def reject_constant(value):
        raise ValueError('INVALID_RECEIPT_JSON_CONSTANT')
    try:
        d = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('INVALID_RECEIPT_JSON') from exc
    if not isinstance(d, dict) or d.get('status') != 'UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED' or d.get('signed') is not False or d.get('device_writes') is not False or d.get('public_binary') is not False:
        raise ValueError('INVALID_PAIR_RECEIPT')
    for key in FIELDS:
        val = d.get(key)
        if not isinstance(val, str) or len(val) != 64 or any(c not in '0123456789abcdef' for c in val):
            raise ValueError('INVALID_DIGEST_' + key)
    return d, (info.st_dev, info.st_ino)

def compare(left, right):
    a, a_identity = load(left)
    b, b_identity = load(right)
    if a_identity == b_identity:
        raise ValueError('RECEIPTS_NOT_INDEPENDENT_FILES')
    # Detect replacement or in-place mutation of the first receipt while the
    # second receipt is read. A matching pair must be stable across both reads.
    a_again, identity_again = load(left)
    if identity_again != a_identity or a_again != a:
        raise ValueError('FIRST_RECEIPT_CHANGED_DURING_COMPARISON')
    # The second receipt may also be replaced while the first is rechecked.
    b_again, b_identity_again = load(right)
    if b_identity_again != b_identity or b_again != b:
        raise ValueError('SECOND_RECEIPT_CHANGED_DURING_COMPARISON')
    # Recheck that the final opened files remain distinct: a path can be
    # replaced with a hardlink to its peer after the initial identity check.
    if identity_again == b_identity_again:
        raise ValueError('RECEIPTS_NOT_INDEPENDENT_FILES')
    return [k for k in FIELDS if a[k] != b[k]]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('first', type=Path)
    p.add_argument('second', type=Path)
    args = p.parse_args()
    mismatches = compare(args.first, args.second)
    if mismatches:
        print('PUBLIC_PAIR_CROSS_WORKSPACE_DIFFERENCE ' + ','.join(mismatches))
        raise SystemExit(1)
    print('PUBLIC_PAIR_CROSS_WORKSPACE_RECEIPT_IDENTITIES_MATCH')
    print('INDEPENDENT_BUILD_PROVENANCE_NOT_VERIFIED')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit('PUBLIC_PAIR_CROSS_WORKSPACE_BLOCKED: ' + str(exc))
