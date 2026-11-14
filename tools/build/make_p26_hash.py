#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Produce the exact P26 hash-file payload for an unsigned P25 initramfs.

Host-side build input, not a boot-time verifier or release approval.
Requires the independent P26 filesystem readback receipt.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

P26_BYTES = 134_217_728
DEVICE = '/dev/mmcblk0p26'

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def create(p26, producer, independent, output):
    for path in (p26, producer, independent):
        if not path.is_file() or path.is_symlink() or any(x.is_symlink() for x in path.parents):
            raise ValueError('invalid input path')
    if output.exists() or output.is_symlink() or any(x.is_symlink() for x in output.parents):
        raise ValueError('output exists or has symlink parent')
    if not output.parent.is_dir():
        raise ValueError('output parent missing')
    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f'duplicate P26 receipt JSON key: {key}')
            obj[key] = value
        return obj

    original = json.loads(producer.read_text(), object_pairs_hook=unique_object)
    approved = json.loads(independent.read_text(), object_pairs_hook=unique_object)
    if not isinstance(original, dict) or not isinstance(approved, dict):
        raise ValueError('P26 receipts must be JSON objects')
    if (type(original.get('schema')) is not int or original.get('schema') != 1 or original.get('status') != 'P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK'
            or original.get('signed') is not False or original.get('hardware') != 'NONE'
            or type(approved.get('schema')) is not int or approved.get('schema') != 1 or approved.get('status') != 'P26_INDEPENDENT_FS_READBACK_VERIFIED'
            or approved.get('verification') != 'INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA'
            or approved.get('signed') is not False or approved.get('hardware') != 'NONE'
            or approved.get('producer_receipt_sha256') != sha256(producer)):
        raise ValueError('P26 independent receipt mismatch')
    if (p26.stat().st_size != P26_BYTES or type(original.get('partition_bytes')) is not int or original.get('partition_bytes') != P26_BYTES
            or type(approved.get('partition_bytes')) is not int or approved.get('partition_bytes') != P26_BYTES):
        raise ValueError('P26 partition size mismatch')
    digest = sha256(p26)
    if (original.get('p26_sha256') != digest or approved.get('p26_sha256') != digest
            or original.get('squashfs_sha256') != approved.get('squashfs_sha256')
            or original.get('squashfs_bytes') != approved.get('squashfs_bytes')):
        raise ValueError('P26 identity mismatch')
    # Both receipts are untrusted JSON. Matching absent or malformed metadata
    # must not be treated as proof of a valid SquashFS payload.
    squash_hash = original.get('squashfs_sha256')
    squash_size = original.get('squashfs_bytes')
    if (not isinstance(squash_hash, str) or re.fullmatch(r'[0-9a-f]{64}', squash_hash) is None
            or type(squash_size) is not int or not 0 < squash_size <= P26_BYTES):
        raise ValueError('invalid SquashFS identity metadata')
    payload = (digest + '  ' + DEVICE + '\n').encode('ascii')
    # An exclusive create prevents replacing evidence from an earlier build.
    # A short write or an I/O failure must never leave a plausible hash input.
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            count = stream.write(payload)
            if count != len(payload):
                raise OSError('short P26 hash payload write')
            stream.flush()
            os.fsync(stream.fileno())
        # Persist the directory entry as well as the payload before reporting
        # an input that may be embedded in the unsigned P25 initramfs.
        dir_fd = os.open(output.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException as original_error:
        if created:
            try:
                output.unlink(missing_ok=True)
                # Persist removal too: a failed directory sync must not leave
                # a plausible hash input after power loss and rollback.
                rollback_fd = os.open(output.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
                try:
                    os.fsync(rollback_fd)
                finally:
                    os.close(rollback_fd)
            except OSError as cleanup_error:
                # Preserve the primary failure even if rollback itself fails.
                if hasattr(original_error, 'add_note'):
                    original_error.add_note(f'P26 hash cleanup failed: {cleanup_error}')
        raise
    return digest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('p26', 'producer', 'independent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    digest = create(args.p26, args.producer, args.independent, args.output)
    print('P26_HASH_INPUT_VERIFIED', digest)
    print('LIMIT: install output as etc/air6/p26.sha256 in newc; P25 packaging and boot checks not proven')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
