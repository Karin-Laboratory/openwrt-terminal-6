#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed Air6 userland source-selection contract. Never builds/installs."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "config/sbat6-userspace-source.json"
FEEDS = ROOT / "config/feeds.lock"
SHA = re.compile(r"^[0-9a-f]{40}$")
PACKAGES = ("base-files", "busybox", "procd", "ubus", "uci", "netifd")
# An arbitrary full-length SHA is not the reviewed source selection.
# Changing the snapshot requires updating this gate and its tests in a PR.
REVIEWED_OPENWRT_COMMIT = "5700101d7c85381889d890dc1d3d001d0b4b6446"
# GitHub's official openwrt/openwrt commit tree was inspected for these
# six package Makefiles. These are Git blob identities, not license approvals,
# dependency closure, or an online integrity check of future checkouts.
REVIEWED_PACKAGE_MAKEFILES = (
    ("base-files", "package/base-files/Makefile", "910a3daa3fa545453e72423b463c1781078d9e8b"),
    ("busybox", "package/utils/busybox/Makefile", "a950cfff73a340df24c61353b0a68784fdbc0fb4"),
    ("procd", "package/system/procd/Makefile", "21868ce6b1e7beb708d6059fefdd113d1128f229"),
    ("ubus", "package/system/ubus/Makefile", "716f993b56ff0c256727c9645e13e12256a2410c"),
    ("uci", "package/system/uci/Makefile", "11f89b0b15a966f6cd3d3098cfdbcff706923dd0"),
    ("netifd", "package/network/config/netifd/Makefile", "d9479102ad9da067b963dcf7d889436e33ae5f8d"),
)

spec = importlib.util.spec_from_file_location(
    "air6_feedlock", ROOT / "tools/build/verify_feeds_lock.py"
)
feed_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = feed_module
spec.loader.exec_module(feed_module)

def validate(plan: dict, feed_text: str) -> list[str]:
    errors: list[str] = []
    required = {"schema", "scope", "target", "architecture", "openwrt",
                "feeds_path", "packages", "package_makefiles", "output_policy", "first_boot",
                "rights_review"}
    if not isinstance(plan, dict) or set(plan) != required:
        return ["invalid source plan schema"]
    if (type(plan["schema"]) is not int or plan["schema"] != 1
            or plan["scope"] != "SOURCE_INSPECTION_ONLY"):
        errors.append("not an approved source-inspection-only plan")
    if plan["target"] != "softbank-air-terminal-6" or plan["architecture"] != "aarch64":
        errors.append("unexpected target or architecture")
    source = plan["openwrt"]
    if not isinstance(source, dict) or set(source) != {"url", "commit", "selection"}:
        errors.append("invalid upstream identity")
    else:
        if (source["url"] != "https://github.com/openwrt/openwrt.git"
                or not isinstance(source["commit"], str)
                or not SHA.fullmatch(source["commit"])
                or source["commit"] != REVIEWED_OPENWRT_COMMIT):
            errors.append("upstream must be official and match the reviewed exact Git commit")
        if source["selection"] != "upstream-main-snapshot-2026-10-30-not-tested-for-sbat6":
            errors.append("upstream compatibility must remain explicitly unverified")
    if plan["feeds_path"] != "config/feeds.lock":
        errors.append("only reviewed local immutable feed lock is permitted")
    errors.extend("feeds: " + e for e in feed_module.inspect(feed_text))
    if (type(plan["packages"]) is not list
            or tuple(plan["packages"]) != PACKAGES):
        errors.append("package selection must remain exact minimal source-only inventory")
    records = plan["package_makefiles"]
    if (type(records) is not list
            or len(records) != len(REVIEWED_PACKAGE_MAKEFILES)
            or any(type(item) is not dict
                   or set(item) != {"package", "path", "git_blob_sha1"}
                   or (item["package"], item["path"], item["git_blob_sha1"]) != expected
                   for item, expected in zip(records, REVIEWED_PACKAGE_MAKEFILES))):
        errors.append("package Makefile provenance must match reviewed upstream blob identities")
    if plan["output_policy"] != {
        "rootfs_build_allowed": False,
        "installable_image_allowed": False,
        "signing_allowed": False,
        "device_write_allowed": False,
    }:
        errors.append("any install, rootfs, signing or device-write output is forbidden")
    if plan["first_boot"] != {
        "preset_root_password": None, "remote_admin_preconfigured": False
    }:
        errors.append("unsafe first-boot defaults")
    if plan["rights_review"] != "pending":
        errors.append("rights clearance cannot be inferred from source selection")
    return errors


def verify_local_makefiles(source_tree: Path, expected: tuple[tuple[str, str, str], ...]) -> list[str]:
    """Verify actual Makefile bytes in a local tree; never fetch or execute source."""
    problems = []
    max_size = 1024 * 1024
    # The POSIX no-follow operations reject symlinks at every traversed level.
    # Unsupported platforms must fail closed, not silently follow links.
    if not (hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")):
        return ["local byte verification requires POSIX no-follow file operations"]
    for package, path, digest in expected:
        fd = None
        try:
            fd = os.open(source_tree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            parts = path.split("/")
            for part in parts[:-1]:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            leaf_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                meta = os.fstat(leaf_fd)
                if not stat.S_ISREG(meta.st_mode) or meta.st_size > max_size:
                    raise ValueError("not a bounded regular file")
                chunks = []
                total = 0
                while True:
                    part = os.read(leaf_fd, min(65536, max_size + 1 - total))
                    if not part:
                        break
                    total += len(part)
                    if total > max_size:
                        raise ValueError("oversized source")
                    chunks.append(part)
                data = b"".join(chunks)
                actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                if actual != digest:
                    problems.append(f"{package}: upstream Makefile bytes differ from reviewed Git blob")
            finally:
                os.close(leaf_fd)
        except (OSError, ValueError):
            problems.append(f"{package}: upstream Makefile unavailable or unsafe")
        finally:
            if fd is not None:
                os.close(fd)
    return problems

def main() -> int:
    parser = argparse.ArgumentParser(description="Air6 source-only userspace inspection")
    parser.add_argument("--source-tree", type=Path,
                        help="optional local OpenWrt tree; read six Makefiles only, no Git/network/build")
    args = parser.parse_args()
    try:
        if (PLAN.is_symlink() or FEEDS.is_symlink()
                or PLAN.stat().st_size > 16384 or FEEDS.stat().st_size > 16384):
            raise ValueError("unsafe source plan input")
        plan = json.loads(PLAN.read_text())
        feed_text = FEEDS.read_text()
    except (OSError, ValueError, UnicodeError):
        print("AIR6_USERSPACE_SOURCE_PLAN_BLOCKED: unreadable input")
        return 2
    findings = validate(plan, feed_text)
    for finding in findings:
        print("AIR6_USERSPACE_SOURCE_PLAN_BLOCKED:", finding)
    if findings:
        return 1
    if args.source_tree is not None:
        byte_findings = verify_local_makefiles(args.source_tree, REVIEWED_PACKAGE_MAKEFILES)
        for finding in byte_findings:
            print("AIR6_USERSPACE_BYTES_BLOCKED:", finding)
        if byte_findings:
            return 1
        print("AIR6_USERSPACE_BYTES_PASS (six local Makefiles only; NOT full commit verification)")
    print("AIR6_USERSPACE_SOURCE_PLAN_PASS (selection only; NO ROOTFS BUILD)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
