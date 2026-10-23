#!/usr/bin/env python3
"""Create a deterministic, source-only RFC bundle from an audited working tree.

This is NOT a bootable image. Refuse missing inputs and symbolic links.
"""
import argparse
import hashlib
import gzip
import io
import json
from pathlib import Path
import tarfile

FILES = (
    "patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch",
    "patches/rfc/0002-mediatek-serialize-reset-requeue.patch",
    "docs/RFC-2-RESET-REQUEUE.ja.md",
    "docs/PUBLIC-SOURCE-VERIFICATION.md",
    "tools/check_mediatek_rfc_series.py",
)
BASE = "openwrt-terminal-6-source-rfc"


def pack(root: Path, output: Path) -> dict:
    entries = {}
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or symlinked required input: {name}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Empty required input: {name}")
        entries[name] = data
    manifest = {
        "format": "source-rfc-v1",
        "flashable": False,
        "upstream": "torvalds/linux v6.18",
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                  for name, data in sorted(entries.items())},
    }
    entries["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as destination:
        with gzip.GzipFile(fileobj=destination, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name, data in sorted(entries.items()):
                    info = tarfile.TarInfo(f"{BASE}/{name}")
                    info.size = len(data)
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    tar.addfile(info, io.BytesIO(data))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("dist/source-rfc.tar.gz"))
    args = parser.parse_args()
    m = pack(args.root, args.output)
    print(json.dumps(m, indent=2, sort_keys=True))
    print(f"Created source-only archive: {args.output}")
