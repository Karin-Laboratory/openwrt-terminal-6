#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage a source-only, noninstallable MT6990 subtarget into pinned OpenWrt.

This touches only a CLEAN, isolated OpenWrt checkout. No donor code, external
network operations, firmware artifacts, signing, or device I/O.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

OPENWRT_PIN = "5799d2da76998be50432b0a3325b42713b4b619b"
OLD_SUBTARGETS = "SUBTARGETS:=filogic mt7622 mt7623 mt7629"
NEW_SUBTARGETS = "SUBTARGETS:=filogic mt6990 mt7622 mt7623 mt7629"
# Parent MediaTek defaults require a built kernel; keep them for other targets.
PARENT_KMOD_DEFAULTS = "DEFAULT_PACKAGES += \\\n\tkmod-leds-gpio kmod-gpio-button-hotplug"
MT6990_PARENT_DEFAULTS = "ifneq ($(SUBTARGET),mt6990)\n" + PARENT_KMOD_DEFAULTS + "\nendif"
ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "tools/build/mt6990-target"
TARGET = "target/linux/mediatek/mt6990/target.mk"
IMAGE = "target/linux/mediatek/image/mt6990.mk"
CONFIG = "target/linux/mediatek/mt6990/config-6.18"
# Same minimal Alpha 3 source-only Kconfig *bootstrap*, not a final board config.
KERNEL_CONFIG = """# SPDX-License-Identifier: GPL-2.0-only
# MT6990 standalone kernel bootstrap. NO board DTS/NETSYS/TOPCK/radio runtime.
CONFIG_64BIT=y
CONFIG_ARM64=y
CONFIG_ARCH_MEDIATEK=y
CONFIG_MFD_SYSCON=y
CONFIG_GENERIC_PHY=y
CONFIG_COMMON_CLK_MEDIATEK=y
CONFIG_NET_VENDOR_MEDIATEK=y
CONFIG_NET_MEDIATEK_SOC=y
CONFIG_NET_DSA=y
CONFIG_NET_DSA_MT7530=y
CONFIG_NET_DSA_MT7530_MDIO=y
CONFIG_PCS_MTK_LYNXI=y
CONFIG_BRIDGE=y
CONFIG_IPV6=y
CONFIG_SQUASHFS=y
CONFIG_SQUASHFS_XZ=y
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=30
    ).strip()


def stage(tree, report, templates=TEMPLATES):
    if tree.is_symlink() or templates.is_symlink() or not tree.is_dir():
        raise ValueError("source tree and templates must be real directories")
    tree = tree.resolve(strict=True)
    templates = templates.resolve(strict=True)
    if tree == templates or tree.is_relative_to(templates) or templates.is_relative_to(tree):
        raise ValueError("OpenWrt and source templates must be independent")
    if git(tree, "rev-parse", "HEAD") != OPENWRT_PIN or git(tree, "status", "--porcelain"):
        raise ValueError("OpenWrt checkout must be exactly pinned and clean")
    if not report.is_absolute() or report.exists() or report.is_symlink() or not report.parent.is_dir():
        raise ValueError("report path must be a new absolute file")
    mediatek_makefile = tree / "target/linux/mediatek/Makefile"
    if mediatek_makefile.is_symlink() or not mediatek_makefile.is_file():
        raise ValueError("missing or unsafe upstream Makefile")
    original = mediatek_makefile.read_text(encoding="utf-8")
    if (original.count(OLD_SUBTARGETS) != 1 or NEW_SUBTARGETS in original
            or "KERNEL_PATCHVER:=6.18" not in original
            or original.count(PARENT_KMOD_DEFAULTS) != 1):
        raise ValueError("unexpected pinned OpenWrt target source")
    files = {
        TARGET: templates / "target.mk",
        IMAGE: templates / "mt6990.mk",
    }
    payloads = {CONFIG: KERNEL_CONFIG.encode("utf-8")}
    for dest, source in files.items():
        if source.is_symlink() or not source.is_file():
            raise ValueError("missing or unsafe source template: " + source.name)
        body = source.read_bytes()
        if not 0 < len(body) < 65536 or b"\0" in body:
            raise ValueError("invalid source template: " + source.name)
        payloads[dest] = body
    if re.search(rb"(?m)^\s*define\s+Device/", payloads[IMAGE]):
        raise ValueError("installable Device profile forbidden")
    for dest in payloads:
        target = tree / dest
        if target.exists() or target.is_symlink():
            raise ValueError("refusing overwrite: " + dest)
        # Never write through an existing symlink in the parent chain.
        for parent in list(target.parents)[:-1]:
            if parent == tree.parent:
                break
            if parent.is_symlink():
                raise ValueError("symlinked target parent: " + dest)
    # All validation is complete; write only four whitelisted upstream files.
    mediatek_makefile.write_text(
        original.replace(OLD_SUBTARGETS, NEW_SUBTARGETS, 1).replace(
            PARENT_KMOD_DEFAULTS, MT6990_PARENT_DEFAULTS, 1
        ), encoding="utf-8"
    )
    for dest, data in payloads.items():
        target = tree / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    output = {
        "status": "MT6990_NATIVE_OPENWRT_SOURCE_SUBTARGET_STAGED",
        "upstream_openwrt_commit": OPENWRT_PIN,
        "target": "mediatek/mt6990",
        "files": {k: {"bytes": len(v), "sha256": digest(v)}
                  for k, v in sorted(payloads.items())},
        "upstream_makefile_sha256": digest(mediatek_makefile.read_bytes()),
        "firmware_outputs": "NONE",
        "signed": False,
        "verified": ["source-identity", "noninstallable-target-registration"],
        "not_verified": ["OpenWrt make defconfig", "kernel compilation", "package compilation",
                         "Air6 board DTS", "NETSYS/clocks/PCIe/Wi-Fi", "AP operation",
                         "driver provenance and redistribution rights", "device boot"],
        "hardware_operations": "NONE",
    }
    report.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tree", required=True, type=Path, help="clean pinned OpenWrt checkout")
    p.add_argument("--report", required=True, type=Path, help="new absolute JSON report")
    args = p.parse_args()
    result = stage(args.tree, args.report)
    print(result["status"], result["upstream_openwrt_commit"])
    print("NO_DEVICE_PROFILE_NO_FIRMWARE_NO_SIGNING_NO_HARDWARE")


if __name__ == "__main__":
    main()
