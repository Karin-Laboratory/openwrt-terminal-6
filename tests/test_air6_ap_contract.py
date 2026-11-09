# SPDX-License-Identifier: MIT
import hashlib
import unittest
from tools.wifi import air6_ap_contract as ap


class PublicAPTests(unittest.TestCase):
    def setUp(self):
        self.config = b"CONFIG_CFG80211=m\nCONFIG_MAC80211=m\nCONFIG_MT7996E=m\n"
        self.symvers = b"abcdef12\tmt7996_something\tmt7996e\tEXPORT_SYMBOL\n"
        self.profile = dict(format="air6-ap-public-contract-v1",
                            kernel_config_sha256=hashlib.sha256(self.config).hexdigest(),
                            module_symvers_sha256=hashlib.sha256(self.symvers).hexdigest(),
                            module_order=list(ap.MODULE_ORDER),
                            kernel_config_symbols=["CONFIG_CFG80211", "CONFIG_MAC80211",
                                                   "CONFIG_MT7996E"],
                            radios=[{"band": "2.4GHz", "channel": 1, "width_mhz": 20},
                                    {"band": "5GHz", "channel": 36, "width_mhz": 20}],
                            wifi_default_enabled=False,
                            ssh={"password_auth": False, "root_password_auth": False,
                                 "authorized_keys_source": "owner-private-at-runtime",
                                 "host_key": "generate-per-device-at-first-boot"},
                            calibration_source="owner-private-at-runtime",
                            firmware_rights="pending")

    def test_valid_public_profile_is_disabled(self):
        r = ap.validate(self.profile, self.config, self.symvers)
        self.assertFalse(r["wifi_enabled"])
        self.assertFalse(r["radio_runtime_proven"])

    def test_symvers_and_config_must_match(self):
        with self.assertRaisesRegex(ValueError, "AP_KERNEL_ABI"):
            ap.validate(self.profile, self.config, b"changed")

    def test_no_active_public_wifi_or_credentials(self):
        self.profile["wifi_default_enabled"] = True
        with self.assertRaisesRegex(ValueError, "MUST_BE_DISABLED"):
            ap.validate(self.profile, self.config, self.symvers)
        self.profile["wifi_default_enabled"] = False
        self.profile["psk"] = "unsafe"
        with self.assertRaisesRegex(ValueError, "SECRET"):
            ap.validate(self.profile, self.config, self.symvers)

    def test_no_password_ssh(self):
        self.profile["ssh"]["password_auth"] = True
        with self.assertRaisesRegex(ValueError, "AP_SSH_SECURITY"):
            ap.validate(self.profile, self.config, self.symvers)

    def test_reject_old_modules_or_unconfigured_driver(self):
        self.profile["module_order"] = ["mt7996e"]
        with self.assertRaisesRegex(ValueError, "AP_MODULE_LOAD_ORDER"):
            ap.validate(self.profile, self.config, self.symvers)
        self.profile["module_order"] = list(ap.MODULE_ORDER)
        partial = b"CONFIG_CFG80211=m\n"
        self.profile["kernel_config_sha256"] = hashlib.sha256(partial).hexdigest()
        with self.assertRaisesRegex(ValueError, "KCONFIG_MISSING"):
            ap.validate(self.profile, partial, self.symvers)


if __name__ == "__main__":
    unittest.main()
