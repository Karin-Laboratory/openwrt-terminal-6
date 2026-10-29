# SPDX-License-Identifier: MIT
"""Source-only regression gates for the opt-in NETSYS / SGMII1 DT variant."""
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parents[1]
DEFAULT = (BASE / 'board/mt6990-air-terminal-6.dts').read_text()
TRIAL = (BASE / 'board/mt6990-air-terminal-6-ethernet-test.dts').read_text()
PHY_PATCH = (BASE / 'patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch').read_text()
CHECKER = (BASE / 'scripts/verify-air6-board-dtc.sh').read_text()


class Air6EthernetVariantTests(unittest.TestCase):
    def test_separate_opt_in_variant(self):
        self.assertIn('#include "mt6990-air-terminal-6.dts"', TRIAL)
        self.assertRegex(DEFAULT, r'(?s)&eth \{.*?status = "disabled";')
        self.assertRegex(DEFAULT, r'(?s)&sgmiisys1 \{.*?status = "disabled";')
        self.assertRegex(TRIAL, r'(?s)&eth \{.*?status = "okay";')
        self.assertRegex(TRIAL, r'(?s)&sgmiisys1 \{.*?status = "okay";')

    def test_preserve_existing_bootloader_netsys_child_path(self):
        self.assertIn('&netsys {', TRIAL)
        self.assertIn('"mediatek,mt6990-netsys", "simple-bus"', TRIAL)
        self.assertIn('#address-cells = <2>;', TRIAL)
        self.assertIn('#size-cells = <2>;', TRIAL)
        self.assertIn('ranges;', TRIAL)
        self.assertIn('/delete-node/ sgmii-pwr0;', TRIAL)
        self.assertIn('/delete-node/ sgmii-pwr1;', TRIAL)
        self.assertNotIn('ethernet@15100000 {', TRIAL)

    def test_real_phy_provider_and_consumer(self):
        for token in (
            'phy@11e60000 {',
            '"mediatek,mt6990-sgmii-phy"',
            'mediatek,sgmii-id = <1>;',
            'mediatek,sgmii-pll = <&air6_sgmii_pll>;',
            'mediatek,spm = <&scpsys>;',
            'power-domains = <&scpsys MT6990_POWER_DOMAIN_SGMII_TOP_1>;',
            'phys = <&air6_sgmii_phy1>;',
            'phy-names = "sgmii";',
        ):
            with self.subTest(token=token):
                self.assertIn(token, TRIAL)

    def test_clock_and_irq_contract(self):
        for token in ('CLK_TOP_SGMII_1_SEL', 'CLK_TOP_SGMII_SBUS_1_SEL',
                      'CLK_TOP_USXGMII_SBUS_0_SEL', 'CLK_TOP_USXGMII_SBUS_1_SEL',
                      '<&pio 50 IRQ_TYPE_LEVEL_LOW>', '<&pio 52 IRQ_TYPE_LEVEL_HIGH>'):
            self.assertIn(token, TRIAL)

    def test_do_not_copy_another_board_or_secrets(self):
        self.assertNotIn('reset-gpios', TRIAL)
        self.assertNotIn('fiberhome,lg6851f', TRIAL.lower())
        self.assertNotIn('root=/dev/mmcblk', TRIAL)
        self.assertNotRegex(TRIAL, r'(?i)\b(?:imei|ssid|psk|private.key)\s*=')
        self.assertNotRegex(TRIAL, r'(?m)\b(?:mac-address|local-mac-address)\s*=')

    def test_sgmii_reset_patch_and_integration_verifier(self):
        self.assertIn('-\tret = mt6990_sgmii_top_cycle(priv);', PHY_PATCH)
        self.assertIn('AIR6_NETSYS_SGMII1_DTC_PASS', CHECKER)
        self.assertIn('AIR6_SGMII_PHY_RESET_SOURCE_PATCH_PASS', CHECKER)
        self.assertIn('git apply --check', CHECKER)
        self.assertNotIn('dd if=', CHECKER)
        self.assertNotIn('mtd write', CHECKER)

if __name__ == '__main__':
    unittest.main()
