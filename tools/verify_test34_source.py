#!/usr/bin/env python3
"""Read-only verification of privately reported Test32/Test34 Ethernet source digests.

This tool does not contain or retrieve the source, and never modifies files.
It cannot prove that the sources are licensed or that the driver works.
"""
import argparse
import hashlib
from pathlib import Path
import sys

DIGESTS = {
    "test32": {
        "mtk_eth_soc.c": "0b8828e99c77249e39790af9f0cccf997d1e0b89b1c9b31634c7d0684ed20e44",
        "mtk_eth_soc.h": "9cc916f920c0a0895ab6e0a954fb5df07d509cf3a5e94347cb0445529b180488",
    },
    "test34": {
        "mtk_eth_soc.c": "f03dd3e6d3ea1262a697776afa4df1ab637ed56e5c84b629cb73f96f7738a9ae",
        "mtk_eth_soc.h": "594bb9ed0aa795d05f1ef42e90e28a9fbd2ddb71b92c08e7b063a36b62d4c40c",
    },
}


def verify(directory: Path, version: str) -> bool:
    expected = DIGESTS[version]
    results = []
    for filename, digest in expected.items():
        path = directory / filename
        if not path.is_file() or path.is_symlink():
            print(f"FAIL {filename}: missing, unreadable, or symlink")
            results.append(False)
            continue
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        match = h.hexdigest() == digest
        print(f"{'PASS' if match else 'FAIL'} {filename}: SHA-256 {'matches' if match else 'mismatch'}")
        results.append(match)
    return all(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="local directory containing mtk_eth_soc.c and mtk_eth_soc.h")
    parser.add_argument("--version", choices=sorted(DIGESTS), required=True)
    args = parser.parse_args()
    ok = verify(args.source_dir, args.version)
    print("SOURCE DIGEST CHECK ONLY; NOT A BUILD OR INSTALL VALIDATION")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
