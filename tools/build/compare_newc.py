#!/usr/bin/env python3
"""Offline comparison of two uncompressed newc initramfs archives (metadata only).

SPDX-License-Identifier: MIT
Never prints file payloads. Intended for private build workspaces, not firmware publication.
"""
import argparse
import hashlib
import json
import os

MAGIC = (b'070701', b'070702')
FIELDS = ('ino', 'mode', 'uid', 'gid', 'nlink', 'mtime', 'filesize', 'devmajor', 'devminor', 'rdevmajor', 'rdevminor', 'namesize', 'check')


def align4(n):
    return (n + 3) & ~3


def entries(path):
    result = []
    with open(path, 'rb') as f:
        while True:
            offset = f.tell()
            header = f.read(110)
            if len(header) != 110 or header[:6] not in MAGIC:
                raise ValueError(f'invalid newc header at offset {offset}')
            if any(byte not in b'0123456789abcdefABCDEF' for byte in header[6:]):
                raise ValueError(f'invalid newc field at {offset}')
            try:
                values = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
            except ValueError as exc:
                raise ValueError(f'invalid newc field at {offset}') from exc
            item = dict(zip(FIELDS, values))
            size = item['filesize']
            namesize = item['namesize']
            if not 1 <= namesize <= 4096:
                raise ValueError(f'invalid name length at {offset}')
            name = f.read(namesize)
            if len(name) != namesize or not name.endswith(b'\0') or b'\0' in name[:-1]:
                raise ValueError(f'invalid name at {offset}')
            padding = align4(f.tell()) - f.tell()
            if f.read(padding) != b'\0' * padding:
                raise ValueError(f'invalid name padding at {offset}')
            if name == b'TRAILER!!!\0':
                if header[:6] == b'070702' and item['check'] != 0:
                    raise ValueError('nonzero trailer CRC')
                if header[:6] == b'070701' and item['check'] != 0:
                    raise ValueError('nonzero trailer checksum')
                if size != 0:
                    raise ValueError('nonempty trailer')
                while True:
                    tail = f.read(1024 * 1024)
                    if not tail:
                        break
                    if tail.strip(b'\0'):
                        raise ValueError('nonzero bytes after trailer')
                break
            digest = hashlib.sha256()
            checksum = 0
            remaining = size
            while remaining:
                chunk = f.read(min(1024*1024, remaining))
                if not chunk:
                    raise ValueError(f'truncated payload at {offset}')
                digest.update(chunk)
                if header[:6] == b'070702':
                    checksum = (checksum + sum(chunk)) & 0xffffffff
                remaining -= len(chunk)
            if header[:6] == b'070702' and checksum != item['check']:
                raise ValueError(f'newc CRC mismatch at {offset}')
            if header[:6] == b'070701' and item['check'] != 0:
                raise ValueError(f'nonzero checksum in non-CRC newc at {offset}')
            padding = align4(f.tell()) - f.tell()
            if f.read(padding) != b'\0' * padding:
                raise ValueError(f'invalid payload padding at {offset}')
            result.append({'name': os.fsdecode(name[:-1]), 'sha256': digest.hexdigest(), **item})
    return result


def file_sha256(path):
    """Hash complete archive bytes, including trailer padding."""
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def compare(a, b):
    left, right = entries(a), entries(b)
    la = {e['name']: e for e in left}
    lb = {e['name']: e for e in right}
    if len(la) != len(left) or len(lb) != len(right):
        raise ValueError('duplicate archive paths')
    changes = []
    for name in sorted(la.keys() | lb.keys()):
        x, y = la.get(name), lb.get(name)
        changed = ['missing'] if x is None or y is None else [k for k in x if k != 'name' and x[k] != y[k]]
        if changed:
            changes.append({'path': name, 'fields': changed})
    order_a = [e['name'] for e in left]
    order_b = [e['name'] for e in right]
    return {'entries_a': len(left), 'entries_b': len(right), 'order_matches': order_a == order_b, 'changed': changes, 'byte_identical': file_sha256(a) == file_sha256(b)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive_a')
    p.add_argument('archive_b')
    args = p.parse_args()
    try:
        result = compare(args.archive_a, args.archive_b)
    except (OSError, ValueError) as exc:
        p.exit(2, f'NEWC_INVALID: {exc}\n')
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result['changed'] or not result['order_matches'] or not result['byte_identical'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
