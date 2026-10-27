#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Clean MT6990 first-boot FE reset MED register preservation patch.

Apply to an exact, disposable, UNINSTRUMENTED Test37-A kernel source tree.
Capture current-boot MED_V2 register values before first destructive FE reset
and restore after, without reallocating or modifying DMA descriptor memory.
Runtime/secondary FE reset restoration is NOT implemented by this patch.
"""
import argparse
import hashlib
from pathlib import Path

ETH = "drivers/net/ethernet/mediatek/mtk_eth_soc.c"
DP = "drivers/misc/mediatek/eccci/hif/ccci_hif_dpmaif.c"
MED = "drivers/misc/mediatek/medmcu/rv33/medmcu_helper.c"
ETH_SHA = "b9f948b4585dca74be3192136acd672ad35f36d24a5798e56c8c88687c52e195"
DP_SHA = "6b9a636b781ee32de1cfa4b7d1538407e16de62881268d699895038393be365a"
MED_SHA = "c7937c999e60257a5472ee410721b7bf6a956388967c9e5c51d659bee3a3c5e3"

HELPER = r'''/* MT6990: Ethernet FE reset clears MED-owned DMA configuration.
 * Keep this boot's own configured ring pointers; never adopt another device's
 * addresses or reallocate descriptors. Initial FE reset only.
 */
struct sbat6d_med_boot_regs {
	u32 fdma_base, fdma_count, fdma_calc, fdma_ctrl, cdmm_ctrl;
	u32 rx0_base, rx0_count, rx0_calc, rx1_base, rx1_count, rx1_calc;
	u32 rx_group, rx_mask, rx_sdl, rx_pref;
	u32 tx_base, tx_count, tx_ctx, tx_pref;
	u32 fdma_mask, fdma_global, mdma_global;
	bool restore;
};

static bool sbat6d_med_boot_restored;

static void sbat6d_med_boot_capture(struct mtk_eth *eth,
				    struct sbat6d_med_boot_regs *s)
{
	if (!MTK_HAS_CAPS(eth->soc->caps, MTK_SOC_MT6990) ||
	    READ_ONCE(sbat6d_med_boot_restored))
		return;
	s->fdma_base = mtk_r32(eth, 0x5900);
	s->fdma_count = mtk_r32(eth, 0x5904);
	s->fdma_calc = mtk_r32(eth, 0x5908);
	s->fdma_ctrl = mtk_r32(eth, 0x0124);
	s->cdmm_ctrl = mtk_r32(eth, 0x1644); /* native CDMM_EG_CRTL */
	s->rx0_base = mtk_r32(eth, 0x5500);
	s->rx0_count = mtk_r32(eth, 0x5504);
	s->rx0_calc = mtk_r32(eth, 0x5508);
	s->rx1_base = mtk_r32(eth, 0x5510);
	s->rx1_count = mtk_r32(eth, 0x5514);
	s->rx1_calc = mtk_r32(eth, 0x5518);
	s->rx_group = mtk_r32(eth, 0x5650);
	s->rx_mask = mtk_r32(eth, 0x5628);
	s->rx_sdl = mtk_r32(eth, 0x5670);
	s->rx_pref = mtk_r32(eth, 0x56dc);
	s->tx_base = mtk_r32(eth, 0x5400);
	s->tx_count = mtk_r32(eth, 0x5404);
	s->tx_ctx = mtk_r32(eth, 0x5408);
	s->tx_pref = mtk_r32(eth, 0x56d0);
	s->fdma_mask = mtk_r32(eth, 0x5a28);
	s->fdma_global = mtk_r32(eth, 0x5a04);
	s->mdma_global = mtk_r32(eth, 0x5604);
	s->restore = s->fdma_base && s->fdma_count == 0x70e4 &&
		s->rx0_base && s->rx0_count == 4200 &&
		s->rx1_base && s->rx1_count == 4200 &&
		s->tx_base && s->tx_count == 12150 &&
		s->rx_mask == 0x30000 && s->rx_group == 0x30000 &&
		s->fdma_mask == 0x80000000 &&
		s->fdma_global == 0x40002004 &&
		s->mdma_global == 0x10804825 &&
		(s->cdmm_ctrl & 6) == 6;
}

static void sbat6d_med_boot_restore(struct mtk_eth *eth,
				    const struct sbat6d_med_boot_regs *s)
{
	if (!s->restore)
		return;
	if (mtk_r32(eth, 0x5500) || mtk_r32(eth, 0x5400) ||
	    mtk_r32(eth, 0x5900))
		return;
	mtk_w32(eth, s->fdma_base, 0x5900);
	mtk_w32(eth, s->fdma_count, 0x5904);
	mtk_w32(eth, s->fdma_calc, 0x5908);
	mtk_w32(eth, s->fdma_ctrl, 0x0124);
	mtk_w32(eth, s->cdmm_ctrl, 0x1644);
	mtk_w32(eth, s->rx0_base, 0x5500);
	mtk_w32(eth, s->rx0_count, 0x5504);
	mtk_w32(eth, s->rx0_calc, 0x5508);
	mtk_w32(eth, s->rx1_base, 0x5510);
	mtk_w32(eth, s->rx1_count, 0x5514);
	mtk_w32(eth, s->rx1_calc, 0x5518);
	mtk_w32(eth, 0x30000, 0x5608);
	mtk_w32(eth, s->rx_group, 0x5650);
	mtk_w32(eth, s->rx_mask, 0x5628);
	mtk_w32(eth, s->rx_sdl, 0x5670);
	mtk_w32(eth, s->rx_pref, 0x56dc);
	mtk_w32(eth, s->tx_base, 0x5400);
	mtk_w32(eth, s->tx_count, 0x5404);
	mtk_w32(eth, s->tx_ctx, 0x5408);
	mtk_w32(eth, 1, 0x5608);
	mtk_w32(eth, s->tx_pref, 0x56d0);
	mtk_w32(eth, s->fdma_mask, 0x5a28);
	wmb();
	mtk_w32(eth, s->fdma_global, 0x5a04);
	mtk_w32(eth, s->mdma_global, 0x5604);
	if (mtk_r32(eth, 0x5500) == s->rx0_base &&
	    mtk_r32(eth, 0x5510) == s->rx1_base &&
	    mtk_r32(eth, 0x5900) == s->fdma_base &&
	    mtk_r32(eth, 0x5628) == s->rx_mask)
		WRITE_ONCE(sbat6d_med_boot_restored, true);
	else
		dev_warn(eth->dev, "MT6990 MED boot ring restore readback failed\n");
}

'''

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def once(text, needle, replacement, label):
    count = text.count(needle)
    if count != 1:
        raise ValueError(f"{label}: expected one anchor, found {count}")
    return text.replace(needle, replacement, 1)

def transform(blob: bytes, expected_sha: str = ETH_SHA) -> bytes:
    if sha(blob) != expected_sha:
        raise ValueError("exact Test37-A Ethernet source required")
    text = blob.decode()
    anchor = "static void mtk_hw_reset(struct mtk_eth *eth)\n{\n\tu32 val;"
    text = once(text, anchor, HELPER + anchor.replace(
        "\tu32 val;", "\tu32 val;\n\tstruct sbat6d_med_boot_regs boot = { 0 };"),
        "boot restore helper")
    anchor = "\tif (mtk_is_netsys_v2_or_greater(eth))\n\t\tregmap_write(eth->ethsys, ETHSYS_FE_RST_CHK_IDLE_EN, 0);"
    text = once(text, anchor,
        "\tsbat6d_med_boot_capture(eth, &boot);\n" + anchor,
        "capture before reset")
    anchor = "\tethsys_reset(eth, RSTCTRL_ETH | RSTCTRL_FE | val);"
    text = once(text, anchor, anchor +
        "\n\tsbat6d_med_boot_restore(eth, &boot);", "restore after reset")
    if any(tag in text for tag in ("[S7-RX]", "[S8-MDMA]", "[S8-FE]")):
        raise ValueError("diagnostic markers must not enter clean build")
    return text.encode()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kernel-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.kernel_root
    if (root / ".stage10-clean-disposable").read_text().strip() != "STAGE10_DISPOSABLE":
        raise SystemExit("expected disposable source")
    for rel, expected in ((ETH, ETH_SHA), (DP, DP_SHA), (MED, MED_SHA)):
        if sha((root / rel).read_bytes()) != expected:
            raise SystemExit("source identity mismatch: " + rel)
    args.output.write_bytes(transform((root / ETH).read_bytes()))
    print("STAGE10_CLEAN_PATCH_READY")
    print("STAGE10_NO_STAGE7_OR_STAGE8_DIAGNOSTICS")

if __name__ == "__main__":
    main()
