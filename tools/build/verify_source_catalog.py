#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed source-only catalog validation. No downloads or device access."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_COMPONENTS = {"ethernet", "modem-ethernet", "modem", "ab-recovery", "board-dt",
                      "kernel", "openwrt-userland", "wifi7", "signing"}
ALLOWED_ORIGINS = {"linux-v6.18-derived", "modified-gpl-parent-derived", "research-board-overlay",
                   "research-transformer", "independent-original"}
ALLOWED_LICENSES = {"MIT", "GPL-2.0-only"}
ALLOWED_REVIEWS = {"pending", "approved"}
EXPECTED_INPUT_KEYS = {"path", "component", "origin", "license",
                       "git_blob_sha1", "rights_review",
                       "contains_flashable_payload"}
MAX_SOURCE = 500_000


def validate(root: Path, catalog: dict, public: bool = False,
             source_public: bool = False):
    issues = []
    if not isinstance(catalog, dict) or set(catalog) != {
        "schema", "policy", "warning", "inputs", "missing_dependencies"
    }:
        return ["invalid top-level catalog schema"]
    if catalog["schema"] != 1 or catalog["policy"] != "SOURCE_ONLY":
        issues.append("must remain source-only schema 1")
    if not isinstance(catalog["warning"], str) or not catalog["warning"]:
        issues.append("missing hash identity warning")
    if not isinstance(catalog["inputs"], list) or not catalog["inputs"]:
        issues.append("source input list is empty")
    seen = set()
    for index, item in enumerate(catalog["inputs"] if isinstance(catalog["inputs"], list) else []):
        prefix = "input#" + str(index)
        if not isinstance(item, dict) or set(item) != EXPECTED_INPUT_KEYS:
            issues.append(prefix + ": unexpected or missing fields")
            continue
        name = item["path"]
        if not isinstance(name, str) or not name or "\\" in name:
            issues.append(prefix + ": invalid source path")
            continue
        rel = PurePosixPath(name)
        if (rel.is_absolute() or ".." in rel.parts or "." in rel.parts
                or name.startswith("/") or not name.startswith(
                    ("patches/", "scripts/", "tools/", "examples/", "tests/", "board/"))):
            issues.append(prefix + ": unsafe or unsupported path")
            continue
        if name in seen:
            issues.append(prefix + ": duplicate path")
            continue
        seen.add(name)
        if rel.suffix not in (".patch", ".py", ".c", ".h", ".sh", ".dtso") and rel.name != "Makefile":
            issues.append(prefix + ": non-source type")
        if item["component"] not in ALLOWED_COMPONENTS:
            issues.append(prefix + ": unknown component")
        if item["origin"] not in ALLOWED_ORIGINS:
            issues.append(prefix + ": invalid source origin")
        if item["license"] not in ALLOWED_LICENSES:
            issues.append(prefix + ": invalid SPDX license")
        if item["rights_review"] not in ALLOWED_REVIEWS:
            issues.append(prefix + ": invalid rights status")
        if item["contains_flashable_payload"] is not False:
            issues.append(prefix + ": flashable payload is forbidden")
        sha = item["git_blob_sha1"]
        if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{40}", sha):
            issues.append(prefix + ": invalid Git blob digest")
            continue
        file_path = root.joinpath(*rel.parts)
        if file_path.is_symlink() or not file_path.is_file():
            issues.append(prefix + ": unavailable or symbolic-link source")
            continue
        raw = file_path.read_bytes()
        if len(raw) > MAX_SOURCE or b"\x00" in raw:
            issues.append(prefix + ": oversized or non-text source")
            continue
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() +
                              b"\x00" + raw).hexdigest()
        if digest != sha:
            issues.append(prefix + ": source bytes differ from catalog identity")
        if (public or source_public) and item["rights_review"] != "approved":
            issues.append(prefix + ": independent rights review pending")
    # Enforce coverage of all current source/test/build files, not just the
    # seven original handpicked kernel/boot/modem entries.
    source_paths = set()
    for dirname in ("patches", "scripts", "tools", "examples", "tests", "board"):
        subtree = root / dirname
        if not subtree.exists():
            continue
        for location in subtree.rglob("*"):
            if location.suffix in (".patch", ".py", ".c", ".h", ".sh") or location.name == "Makefile":
                source_paths.add(location.relative_to(root).as_posix())
    for name in sorted(source_paths - seen):
        issues.append("uncatalogued source/test: " + name)
    missing = catalog["missing_dependencies"]
    if not isinstance(missing, list):
        issues.append("missing dependencies must be a list")
    else:
        components = set()
        for n, entry in enumerate(missing):
            if not isinstance(entry, dict) or set(entry) != {"component", "reason"}:
                issues.append("invalid missing dependency record #" + str(n))
                continue
            if (not isinstance(entry["component"], str) or not entry["component"]
                    or entry["component"] in components
                    or not isinstance(entry["reason"], str) or not entry["reason"]):
                issues.append("invalid or duplicate missing dependency #" + str(n))
            components.add(entry["component"])
        if public and missing:
            issues.append("public build readiness: missing build dependencies")
    return issues


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--public-source", action="store_true",
                       help="check source identity and rights labels; does NOT require full firmware")
    group.add_argument("--public-build", action="store_true",
                       help="stricter hypothetical firmware completeness gate")
    args = parser.parse_args()
    try:
        catalog = json.loads((ROOT / "config/source-catalog.json").read_text())
        issues = validate(ROOT, catalog, public=args.public_build,
                          source_public=args.public_source)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print("SOURCE CATALOG FAIL: unreadable or invalid input")
        return 2
    for issue in issues:
        print("SOURCE CATALOG BLOCKED:", issue)
    print("SOURCE CATALOG", "PASS" if not issues else "FAIL",
          "(checks declared source-rights status only; requires independent\n" +
          " copyright/license, Git history, issue/log and security reviews)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
