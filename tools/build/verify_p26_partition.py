#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only independent unsigned p26 byte-layout gate (not filesystem acceptance)."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PARTITION_SIZE = 134217728
SUPERBLOCK_SIZE = 96

def verify(image: Path, receipt: Path):
    data = json.loads(receipt.read_text())
    assert image.stat().st_size == PARTITION_SIZE, 'incorrect p26 size'
    sha = hashlib.sha256()
    with image.open('rb') as stream:
        header = stream.read(SUPERBLOCK_SIZE)
        assert len(header) == SUPERBLOCK_SIZE and header[:4] == b'hsqs', 'invalid SquashFS magic'
        # SquashFS v4 superblock: bytes_used is u64 at offset 40.
        major, minor = struct.unpack_from('<HH', header, 28)
        assert (major, minor) == (4, 0), 'unsupported SquashFS version'
        used = struct.unpack_from('<Q', header, 40)[0]
        assert SUPERBLOCK_SIZE <= used < PARTITION_SIZE, 'invalid SquashFS bytes_used'
        assert used == data['squashfs_bytes'], 'receipt size mismatch'
        stream.seek(0)
        remaining = used
        fs_hash = hashlib.sha256()
        while remaining:
            chunk = stream.read(min(1 << 20, remaining))
            assert chunk, 'truncated filesystem'
            fs_hash.update(chunk)
            sha.update(chunk)
            remaining -= len(chunk)
        assert fs_hash.hexdigest() == data['squashfs_sha256'], 'filesystem hash mismatch'
        while chunk := stream.read(1 << 20):
            assert not any(chunk), 'nonzero partition padding'
            sha.update(chunk)
    assert sha.hexdigest() == data['p26_sha256'], 'partition hash mismatch'
    assert data.get('signed') is False, 'unexpected signing status'
    print('P26_INDEPENDENT_BYTE_LAYOUT_PASS', sha.hexdigest())
    print('NOT_FS_METADATA_OR_SOURCE_PROVENANCE_ACCEPTANCE')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args()
    verify(a.image, a.receipt)

if __name__ == '__main__':
    main()
