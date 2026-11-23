#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Privacy-minimizing rootfs drift diagnostics for independent CI builds."""
import hashlib
import os
import stat
import sys
from pathlib import Path


def fingerprints(root: Path, bucket_count: int = 32):
    if bucket_count < 2 or bucket_count & (bucket_count - 1):
        raise ValueError('bucket_count must be a power of two')
    content = [hashlib.sha256() for _ in range(bucket_count)]
    metadata = [hashlib.sha256() for _ in range(bucket_count)]
    counts = [0] * bucket_count
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        for name in ([None] if Path(base) == root else []) + sorted(dirs + files):
            path = Path(base) if name is None else Path(base) / name
            rel = '.' if name is None else path.relative_to(root).as_posix()
            info = path.lstat()
            kind = stat.S_IFMT(info.st_mode)
            if kind not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK):
                raise ValueError('unsupported filesystem entry')
            identity = rel.encode('utf-8', 'surrogateescape') + b'\0'
            index = int.from_bytes(hashlib.sha256(identity).digest()[:4], 'big') % bucket_count
            meta = '\0'.join(map(str, (kind, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid))).encode() + b'\n'
            if stat.S_ISLNK(info.st_mode):
                payload = os.fsencode(os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                payload = digest.hexdigest().encode()
            else:
                payload = b''
            content[index].update(identity + payload + b'\n')
            metadata[index].update(identity + meta)
            counts[index] += 1
    return [(i, counts[i], content[i].hexdigest(), metadata[i].hexdigest()) for i in range(bucket_count)]


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: repro_buckets.py ROOTFS')
    for i, count, content, metadata in fingerprints(Path(sys.argv[1])):
        print(f'PUBLIC_P26_REPRO_BUCKET_{i:02d}=count:{count},content:{content},metadata:{metadata}')


if __name__ == '__main__':
    main()
