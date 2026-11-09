#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source-only Test27-derived Wi-Fi/SSH conditions, NEVER a working-AP claim.

No EEPROM, firmware payload, key, PSK, host key or user credentials accepted.
Requires real matching kernel .config and Module.symvers SHA identities before
any *owner-private* activation step can even be considered.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

MODULE_ORDER = ("compat", "cfg80211", "mac80211", "mt76",
                "mt76_connac_lib", "mt7996e")
EXPECTED_RADIOS = (("2.4GHz", 1, 20), ("5GHz", 36, 20))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(profile, kernel_config, module_symvers):
    if not isinstance(profile, dict):
        raise ValueError("AP_PROFILE_TYPE")
    prohibited = {"password", "psk", "secret", "private_key", "eeprom",
                  "calibration_data", "host_key", "authorized_keys", "ssid"}
    if any(k.lower() in prohibited for k in profile):
        raise ValueError("AP_EMBEDDED_SECRET_OR_IDENTITY")
    if profile.get("format") != "air6-ap-public-contract-v1":
        raise ValueError("AP_FORMAT")
    for field, contents in (("kernel_config_sha256", kernel_config),
                            ("module_symvers_sha256", module_symvers)):
        h = profile.get(field)
        if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) or digest(contents) != h:
            raise ValueError("AP_KERNEL_ABI_IDENTITY_" + field)
    if tuple(profile.get("module_order", ())) != MODULE_ORDER:
        raise ValueError("AP_MODULE_LOAD_ORDER")
    if not all(isinstance(x, str) and x.startswith("CONFIG_") for x in profile.get("kernel_config_symbols", ())):
        raise ValueError("AP_KCONFIG_SYMBOLS")
    for symbol in profile["kernel_config_symbols"]:
        if not any(line.encode("ascii") in kernel_config.splitlines() for line in
                   (symbol + "=y", symbol + "=m")):
            raise ValueError("AP_KCONFIG_MISSING_" + symbol)
    bands = profile.get("radios")
    if not isinstance(bands, list) or tuple((x.get("band"), x.get("channel"), x.get("width_mhz"))
                                                  for x in bands) != EXPECTED_RADIOS:
        raise ValueError("AP_CHANNEL_PLAN")
    if profile.get("wifi_default_enabled") is not False:
        raise ValueError("AP_PUBLIC_DEFAULT_MUST_BE_DISABLED")
    ssh = profile.get("ssh", {})
    if ssh != {"password_auth": False, "root_password_auth": False,
               "authorized_keys_source": "owner-private-at-runtime",
               "host_key": "generate-per-device-at-first-boot"}:
        raise ValueError("AP_SSH_SECURITY")
    if profile.get("calibration_source") != "owner-private-at-runtime":
        raise ValueError("AP_CALIBRATION_SCOPE")
    if profile.get("firmware_rights") != "pending":
        raise ValueError("AP_NO_FIRMWARE_LICENSE_APPROVAL")
    # This preflight does not read device firmware, run modprobe or start AP.
    return {"status": "SOURCE_ONLY_ABI_SECURITY_CONTRACT_PASS",
            "module_order": list(MODULE_ORDER), "wifi_enabled": False,
            "radio_runtime_proven": False, "ethernet_runtime_proven": False,
            "ssh_runtime_proven": False, "device_boot_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--kernel-config", type=Path, required=True)
    ap.add_argument("--module-symvers", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(validate(json.loads(a.profile.read_text()),
                              a.kernel_config.read_bytes(),
                              a.module_symvers.read_bytes()), sort_keys=True))


if __name__ == "__main__":
    main()
