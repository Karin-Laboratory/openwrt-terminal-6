#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Safe *offline* P44 overlay change promotion to new public rootfs staging.

Does not mount, format, write P44, or interpret its whiteout representation as
regular files. Only explicitly allowlisted service/preinit paths are staged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat

PREFIXES = ("lib/preinit/", "etc/init.d/", "usr/libexec/air6/")
DENY = ("etc/config/", "etc/dropbear/", "etc/ssh/", "etc/shadow", "etc/passwd",
        "etc/uci-defaults/", "etc/rc.local", "etc/machine-id", "etc/wireless/",
        "lib/firmware/", "overlay/", "upper/", "work/")


def safe_path(value):
    if not isinstance(value, str) or "\\" in value or value.startswith("/"):
        raise ValueError("P44_PATH_INVALID")
    parts = PurePosixPath(value).parts
    if not parts or any(p in (".", "..") or p.startswith(".wh.") for p in parts):
        raise ValueError("P44_WHITEOUT_OR_TRAVERSAL")
    if any(value.startswith(p) for p in DENY) or not any(value.startswith(p) for p in PREFIXES):
        raise ValueError("P44_PROTECTED_OR_UNREVIEWED_PATH")
    return parts


def audit_source(upper, requested):
    upper = Path(upper)
    if upper.is_symlink() or not upper.is_dir():
        raise ValueError("P44_UPPER_NOT_DIRECTORY")
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("P44_EXPLICIT_UNIQUE_ALLOWLIST_REQUIRED")
    result = []
    for relative in requested:
        parts = safe_path(relative)
        parent = upper
        for p in parts:
            parent = parent / p
            if parent.is_symlink():
                raise ValueError("P44_SYMLINK_REFUSED")
            for name in os.listxattr(parent, follow_symlinks=False):
                if name.endswith("overlay.opaque") or name.endswith("overlay.whiteout"):
                    raise ValueError("P44_OPAQUE_OR_WHITEOUT")
        mode = parent.lstat().st_mode
        if not stat.S_ISREG(mode) or parent.stat().st_size > 1_048_576:
            raise ValueError("P44_INVALID_FILE_TYPE_SIZE")
        data = parent.read_bytes()
        if b"\x00" in data or b"PRIVATE KEY" in data or b"password=" in data.lower():
            raise ValueError("P44_SECRET_OR_BINARY_PAYLOAD")
        result.append({"relative": relative, "sha256": hashlib.sha256(data).hexdigest(),
                       "bytes": len(data), "mode": stat.S_IMODE(mode)})
    return result


def stage(upper, requested, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("P44_DESTINATION_EXISTS")
    manifest = audit_source(upper, requested)
    destination.mkdir(parents=False, mode=0o700)
    try:
        for entry in manifest:
            src = Path(upper) / entry["relative"]
            tgt = destination / entry["relative"]
            tgt.parent.mkdir(parents=True, exist_ok=True)
            with tgt.open("xb") as dst:
                dst.write(src.read_bytes())
            tgt.chmod(entry["mode"])
            if hashlib.sha256(tgt.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("P44_STAGE_READBACK_FAILED")
        (destination / "air6-p44-promotion-manifest.json").write_text(
            json.dumps({"scope": "SOURCE_ONLY_REVIEW_REQUIRED", "files": manifest,
                        "from_live_p44": False, "p26_rebuilt": False,
                        "p25_sha_binding_updated": False}, indent=2) + "\n")
        return manifest
    except BaseException:
        shutil.rmtree(destination)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upper-readonly", required=True, type=Path)
    ap.add_argument("--allow", required=True, action="append")
    ap.add_argument("--new-output", required=True, type=Path)
    args = ap.parse_args()
    print("P44_OFFLINE_PROMOTION_STAGED", len(stage(args.upper_readonly, args.allow, args.new_output)))
    print("LIMIT: no live mount, no p26 merge or p25 binding, no redistribution approval")


if __name__ == "__main__":
    main()
