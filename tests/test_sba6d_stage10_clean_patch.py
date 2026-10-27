# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import unittest
import hashlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("stage10_clean_patch",ROOT/"scripts/research/sba6d_stage10_clean_patch.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SOURCE=(
    b"static void mtk_hw_reset(struct mtk_eth *eth)\n{\n\tu32 val;\n"
    b"\tif (mtk_is_netsys_v2_or_greater(eth))\n"
    b"\t\tregmap_write(eth->ethsys, ETHSYS_FE_RST_CHK_IDLE_EN, 0);\n"
    b"\tethsys_reset(eth, RSTCTRL_ETH | RSTCTRL_FE | val);\n"
)

def patched():
    return mod.transform(SOURCE,expected_sha=hashlib.sha256(SOURCE).hexdigest()).decode()

class Stage10CleanTests(unittest.TestCase):
    def test_fixed_source_pins(self):
        self.assertEqual(len(mod.ETH_SHA),64)
        self.assertEqual(len(mod.DP_SHA),64)
        self.assertEqual(len(mod.MED_SHA),64)
    def test_wrong_source_rejected(self):
        with self.assertRaisesRegex(ValueError,"exact Test37-A"):
            mod.transform(b"wrong source")
    def test_capture_before_reset_restore_after(self):
        x=patched()
        self.assertLess(x.index("sbat6d_med_boot_capture(eth, &boot)"),
                        x.index("ethsys_reset(eth, RSTCTRL_ETH"))
        self.assertLess(x.index("ethsys_reset(eth, RSTCTRL_ETH"),
                        x.index("sbat6d_med_boot_restore(eth, &boot)"))
    def test_native_cdmm_offset(self):
        x=patched()
        self.assertIn("0x1644",x)
        self.assertNotIn("0x1664",x)
    def test_does_not_reallocate_dma_descriptors(self):
        x=patched()
        self.assertNotIn("dma_map_single",x)
        self.assertNotIn("kmalloc_array",x)
        self.assertNotIn("netdev_alloc_frag",x)
        self.assertIn("s->rx0_base",x)
        self.assertIn("s->fdma_base",x)
    def test_no_s7_s8_debug_and_no_double_injection(self):
        x=patched()
        for token in ("[S7-RX]","[S8-MDMA]","[S8-FE]"):
            self.assertNotIn(token,x)
        self.assertEqual(x.count("sbat6d_med_boot_restore(eth, &boot)"),1)
        with self.assertRaises(ValueError):
            mod.transform(SOURCE+SOURCE,expected_sha=hashlib.sha256(SOURCE+SOURCE).hexdigest())

if __name__=="__main__":
    unittest.main()
