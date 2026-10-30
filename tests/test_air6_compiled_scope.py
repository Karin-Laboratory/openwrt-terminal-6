# SPDX-License-Identifier: MIT
"""Synthetic DTB round-trip status tests; no device access or downloads."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "compiled_air6_scope", ROOT / "tools/board/check_air6_compiled_scope.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def tree(eth: str, pcs: str, phy: str = "okay",
         mac0: str = "disabled", mac1: str = "okay") -> str:
    return f'''/dts-v1/;
/ {{
    netsys@15100000 {{
        ethernet@15100000 {{
            status = "{eth}";
            mac@0 {{ status = "{mac0}"; }};
            mac@1 {{
                reg = <0x01>;
                phy-mode = "2500base-x";
                fixed-link {{
                    speed = <0x9c4>;
                    full-duplex;
                }};
                status = "{mac1}";
                phandle = <0x10>;
            }};
            mdio-bus {{
                switch@1f {{
                    reg = <0x1f>;
                    ports {{
                        port@5 {{
                            reg = <0x05>;
                            ethernet = <0x10>;
                            phy-mode = "2500base-x";
                            fixed-link {{
                                speed = <0x9c4>;
                                full-duplex;
                            }};
                        }};
                    }};
                }};
            }};
        }};
    }};
    syscon@11305000 {{ status = "{pcs}"; }};
    phy@11e60000 {{ status = "{phy}"; }};
}};
'''


class CompiledAir6ScopeTests(unittest.TestCase):
    def test_base_disabled_trial_opt_in(self):
        self.assertEqual(checker.validate(tree("disabled", "disabled"),
                                          tree("okay", "okay")), [])

    def test_base_ethernet_enabled_is_blocked(self):
        findings = checker.validate(tree("okay", "disabled"), tree("okay", "okay"))
        self.assertTrue(any("base: Ethernet" in x for x in findings), findings)

    def test_base_pcs_enabled_is_blocked(self):
        findings = checker.validate(tree("disabled", "okay"), tree("okay", "okay"))
        self.assertTrue(any("base: SGMII1 PCS" in x for x in findings), findings)

    def test_trial_phy_disabled_is_blocked(self):
        findings = checker.validate(tree("disabled", "disabled"),
                                    tree("okay", "okay", "disabled"))
        self.assertTrue(any("trial: SGMII1 PHY" in x for x in findings), findings)

    def test_trial_unreviewed_mac0_enablement_is_blocked(self):
        findings = checker.validate(tree("disabled", "disabled"),
                                    tree("okay", "okay", mac0="okay"))
        self.assertTrue(any("trial: mac@0" in x for x in findings), findings)

    def test_trial_required_mac1_disablement_is_blocked(self):
        findings = checker.validate(tree("disabled", "disabled"),
                                    tree("okay", "okay", mac1="disabled"))
        self.assertTrue(any("trial: mac@1" in x for x in findings), findings)


    def test_trial_link_mode_mismatch_is_blocked_on_either_end(self):
        for target in ("mac@1", "port@5"):
            with self.subTest(target=target):
                original = tree("okay", "okay")
                prefix, suffix = original.split(target + " {", 1)
                suffix = suffix.replace('phy-mode = "2500base-x";',
                                        'phy-mode = "sgmii";', 1)
                findings = checker.validate(tree("disabled", "disabled"),
                                            prefix + target + " {" + suffix)
                self.assertTrue(any("unexpected phy-mode" in x for x in findings),
                                findings)

    def test_trial_fixed_link_speed_mismatch_is_blocked_on_either_end(self):
        for target in ("mac@1", "port@5"):
            with self.subTest(target=target):
                original = tree("okay", "okay")
                prefix, suffix = original.split(target + " {", 1)
                suffix = suffix.replace("speed = <0x9c4>;", "speed = <0x3e8>;", 1)
                findings = checker.validate(tree("disabled", "disabled"),
                                            prefix + target + " {" + suffix)
                self.assertTrue(any("fixed-link speed mismatch" in x for x in findings),
                                findings)

    def test_trial_missing_full_duplex_is_blocked_on_either_end(self):
        for target in ("mac@1", "port@5"):
            with self.subTest(target=target):
                original = tree("okay", "okay")
                prefix, suffix = original.split(target + " {", 1)
                suffix = suffix.replace("full-duplex;", "", 1)
                findings = checker.validate(tree("disabled", "disabled"),
                                            prefix + target + " {" + suffix)
                self.assertTrue(any("full-duplex" in x for x in findings), findings)

    def test_trial_cpu5_wrong_register_is_blocked(self):
        bad = tree("okay", "okay").replace("reg = <0x05>;", "reg = <0x06>;")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("CPU5 compiled reg mismatch" in x for x in findings), findings)

    def test_trial_switch_wrong_register_is_blocked(self):
        bad = tree("okay", "okay").replace("reg = <0x1f>;", "reg = <0x1e>;")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("MT7531 switch compiled reg mismatch" in x for x in findings), findings)

    def test_trial_mac1_wrong_register_is_blocked(self):
        bad = tree("okay", "okay").replace("reg = <0x01>;", "reg = <0x02>;")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("MAC1 compiled reg mismatch" in x for x in findings), findings)

    def test_trial_cpu5_missing_register_is_blocked(self):
        bad = tree("okay", "okay").replace("reg = <0x05>;", "")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("direct reg cell" in x for x in findings), findings)

    def test_trial_cpu5_wrong_mac_phandle_is_blocked(self):
        bad = tree("okay", "okay").replace(
            "ethernet = <0x10>;", "ethernet = <0x11>;")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("CPU5 ethernet phandle" in x for x in findings), findings)

    def test_trial_cpu5_missing_ethernet_reference_is_blocked(self):
        bad = tree("okay", "okay").replace("ethernet = <0x10>;", "")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("direct ethernet cell" in x for x in findings), findings)

    def test_trial_mac1_missing_phandle_is_blocked(self):
        bad = tree("okay", "okay").replace("phandle = <0x10>;", "")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("direct phandle cell" in x for x in findings), findings)

    def test_trial_cpu5_duplicate_ethernet_reference_is_blocked(self):
        bad = tree("okay", "okay").replace(
            "ethernet = <0x10>;", "ethernet = <0x10>;\n                            ethernet = <0x10>;")
        findings = checker.validate(tree("disabled", "disabled"), bad)
        self.assertTrue(any("direct ethernet cell" in x for x in findings), findings)

    def test_trial_missing_mac_child_fails_closed(self):
        trial = tree("okay", "okay").replace(
            'mac@0 { status = "disabled"; };', 'unused@0 { status = "disabled"; };')
        findings = checker.validate(tree("disabled", "disabled"), trial)
        self.assertTrue(any("expected one mac@0" in x for x in findings), findings)

    def test_child_status_cannot_masquerade_as_parent_status(self):
        bad = tree("disabled", "disabled").replace(
            'status = "disabled";\n            mac@0', '/* removed */\n            mac@0')
        findings = checker.validate(bad, tree("okay", "okay"))
        self.assertTrue(any("missing, duplicated or malformed" in x for x in findings), findings)

    def test_missing_node_fails_closed(self):
        bad = tree("disabled", "disabled").replace("syscon@11305000", "other@11305000")
        self.assertTrue(checker.validate(bad, tree("okay", "okay")))


if __name__ == "__main__":
    unittest.main()
