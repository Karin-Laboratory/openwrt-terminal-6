#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate an OpenWrt feed *commit lock*, never fetch/install packages.

This check does not confer redistribution rights or validate signed source.
"""
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import re
import sys

FEED_NAMES = {"packages", "luci", "routing", "telephony", "video"}
FEED_KINDS = {"src-git", "src-git-full"}
# Reviewed *selection*, not proof of canonical origin reachability or license.
# A syntactically valid 40-character SHA is not sufficient to change feeds.
REVIEWED_COMMITS = {
    "packages": "11396c3434272b73294d29aa9d86497b25cf33da",
    "luci": "a8c110bed82375b69eb3881b2e54e617520e8c7d",
    "routing": "4b9891b9136259f93294a424507ed24c5e8c1cbd",
    "telephony": "5d68d53c160a325ea9d03fce393e051573bcc736",
    "video": "644a66261288b4a95dbc6e46fe805d33cb9f71d9",
}
COMMIT = re.compile(r"^[0-9a-f]{40}$")
NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


def inspect(text: str):
    errors = []
    accepted = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) != 3:
            errors.append(f"line {lineno}: expected exactly feed-kind name url^sha")
            continue
        kind, name, spec = parts
        if kind not in FEED_KINDS:
            errors.append(f"line {lineno}: unapproved feed transport")
        if not NAME.fullmatch(name) or name not in FEED_NAMES:
            errors.append(f"line {lineno}: unexpected feed name")
            continue
        if name in accepted:
            errors.append(f"line {lineno}: duplicate feed")
            continue
        accepted[name] = True
        url, delimiter, revision = spec.rpartition("^")
        if not delimiter or not COMMIT.fullmatch(revision):
            errors.append(f"line {lineno}: feed must have exact 40-char Git SHA")
            continue
        if revision != REVIEWED_COMMITS[name]:
            errors.append(f"line {lineno}: feed revision differs from reviewed exact commit")
            continue
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.port
                or any(p == ".." for p in parsed.path.split("/"))):
            errors.append(f"line {lineno}: unsafe feed URL")
            continue
        if parsed.hostname == "git.openwrt.org":
            if url != f"https://git.openwrt.org/{'project/luci.git' if name == 'luci' else 'feed/' + name + '.git'}":
                errors.append(f"line {lineno}: wrong canonical upstream for {name}")
        elif parsed.hostname == "github.com":
            if name != "video" or url != "https://github.com/openwrt/video.git":
                errors.append(f"line {lineno}: unexpected third-party feed location")
        else:
            errors.append(f"line {lineno}: untrusted upstream host")
    if set(accepted) != FEED_NAMES:
        errors.append("missing/extra required feed names")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="locally prepared feed lock, never an online URL")
    args = parser.parse_args()
    try:
        if args.path.is_symlink() or not args.path.is_file() or args.path.stat().st_size > 16384:
            raise ValueError("unsafe feed file")
        data = args.path.read_text(encoding="utf-8")
        issues = inspect(data)
    except (OSError, UnicodeError, ValueError):
        print("FEED LOCK BLOCKED: unreadable input")
        return 2
    for issue in issues:
        print("FEED LOCK BLOCKED:", issue)
    print("FEED LOCK", "PASS" if not issues else "FAIL")
    print("This does not validate author rights, feed content integrity or build completeness.")
    return int(bool(issues))


if __name__ == "__main__":
    sys.exit(main())
