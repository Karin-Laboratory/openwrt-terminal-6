#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare independently generated unsigned pair receipts without firmware disclosure."""
import argparse
import json
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
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError('RECEIPT_TOO_LARGE')
    d = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(d, dict) or d.get('status') != 'UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED' or d.get('signed') is not False or d.get('device_writes') is not False or d.get('public_binary') is not False:
        raise ValueError('INVALID_PAIR_RECEIPT')
    for key in FIELDS:
        val = d.get(key)
        if not isinstance(val, str) or len(val) != 64 or any(c not in '0123456789abcdef' for c in val):
            raise ValueError('INVALID_DIGEST_' + key)
    return d

def compare(left, right):
    a, b = load(left), load(right)
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

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit('PUBLIC_PAIR_CROSS_WORKSPACE_BLOCKED: ' + str(exc))
