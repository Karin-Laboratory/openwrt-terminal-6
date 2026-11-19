#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression gate for Ethernet symbols in the *actual staged* native Kconfig.

Source-only: does not imply that a driver compiles or the board boots.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/build/stage_mt6990_subtarget.py"
REQUIRED_BUILTIN = {
    "CONFIG_ARCH_MEDIATEK",
    "CONFIG_MFD_SYSCON",
    "CONFIG_GENERIC_PHY",
    "CONFIG_COMMON_CLK_MEDIATEK",
    "CONFIG_NET_VENDOR_MEDIATEK",
    "CONFIG_NET_MEDIATEK_SOC",
    "CONFIG_NET_DSA",
    "CONFIG_NET_DSA_MT7530",
    "CONFIG_NET_DSA_MT7530_MDIO",
    "CONFIG_PCS_MTK_LYNXI",
}
# Do not accept =m: early boot Ethernet must not depend on absent modules.

def read_staged_kernel_config():
    spec = importlib.util.spec_from_file_location("air6_stage", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("native stage script unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.KERNEL_CONFIG

def validate_config(config):
    lines = config.splitlines()
    settings = {}
    for line in lines:
        if not line.startswith("CONFIG_") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in settings:
            raise ValueError("duplicate Kconfig assignment: " + key)
        settings[key] = value
    missing = sorted(key for key in REQUIRED_BUILTIN if settings.get(key) != "y")
    if missing:
        raise ValueError("native Ethernet bootstrap missing builtins: " + ", ".join(missing))
    if "CONFIG_ARM64_4K_PAGES" not in settings or settings["CONFIG_ARM64_4K_PAGES"] != "y":
        raise ValueError("native ARM64 4K page selection missing")
    return settings

class NativeEthernetKconfigContract(unittest.TestCase):
    def test_current_native_stage(self):
        validate_config(read_staged_kernel_config())

    def test_rejects_module_instead_of_builtin(self):
        config = read_staged_kernel_config().replace("CONFIG_NET_DSA=y", "CONFIG_NET_DSA=m")
        with self.assertRaisesRegex(ValueError, "CONFIG_NET_DSA"):
            validate_config(config)

    def test_rejects_missing_pcs(self):
        config = read_staged_kernel_config().replace("CONFIG_PCS_MTK_LYNXI=y", "")
        with self.assertRaisesRegex(ValueError, "CONFIG_PCS_MTK_LYNXI"):
            validate_config(config)

    def test_rejects_duplicate_assignment(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_config(read_staged_kernel_config() + "\nCONFIG_NET_DSA=n\n")

if __name__ == "__main__":
    unittest.main()
