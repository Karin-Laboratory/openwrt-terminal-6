# SDK-derived code provenance and exact line map (2026-10-22)

**Status: source audit, NOT redistribution approval.** The historical Test25 PHY source is held in the private archive, and is deliberately NOT copied here. Line numbers are 1-based and inclusive for the specifically pinned files below; they must be recalculated if a source revision changes.

## Source A: publicly accessible donor adaptation (confirmed exact file)

Repository: `13179415360/openwrt-mt6990-lg6851f`
Revision: `a40df9a5afb46716dea799acea69f17480df4d82`
Path: `target/linux/mediatek/files-6.18/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c`
Git blob SHA-1: `598f9c8d0a905bf6e293157d2fd475fef54bfacd`
License header (line 1): `SPDX-License-Identifier: GPL-2.0-only`
Reference: https://github.com/13179415360/openwrt-mt6990-lg6851f/blob/a40df9a5afb46716dea799acea69f17480df4d82/target/linux/mediatek/files-6.18/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c

## Source B: private project candidate (not published)

Repository: `Karin-Laboratory/SBAT6A-Offline-Archive` (private)
Branch inspected: `research/mt6990-test25-persistent-ethernet-build`
Path: `openwrt-port/test25/phy-mtk-mt6990-sgmii-sba6d.c`
Git blob SHA-1: `ccbe3fc4d60f598b1bcedd2ffe1baa807fd7ffda`
License header (line 1): `SPDX-License-Identifier: GPL-2.0-only`

Both files were retrieved at the above refs. A direct comparison found a Test25-specific modification to the reset/power-cycle handling, so Source B must **not** be described as byte-identical to Source A.

## Precisely identified SDK-related sections

| Function / purpose | Source A line range | Source B line range | Relationship |
| --- | --- | --- | --- |
| SGMII_TOP MTCMOS off/on ordering | 42 onward (function; exact ending requires confirmation) | 42-87 (estimate; verify before quoting) | Comment calls it exact SDK ordering; direct SDK line origin unverified |
| Shared PLL enable and Gen2 configuration | 106-175 | 106-175 | Includes explicit SDK attribution and register programming |
| SDK `mtk_sgmii_phy_gen2()` register sequence | **127-166** | **127-166** | The referenced key code span, with ordered read-modify-write, writes, and delays |
| SDK force-mode PLL enabling | 177 onward | 177 onward | Function comments cite `mtk_sgmii_setup_mode_force()`; end line not certified |
| PHY reset / power cycling | Approximately 200-221 | Approximately 200-220 | Different logic; candidate disables TOP power cycling |
| License declaration | 1 | 1 | License header is evidence of a declaration, not a complete origin audit |

**Do not interpret the above as a claim that an original MediaTek SDK file's line numbers have been located.** The confirmed 127-166 range is in the *public donor-adapted PHY file* and private candidate, **not yet the original SDK**.

## Original MediaTek SDK upstream reference (needs final mapping)

Linux's upstream `phy-mtk-xfi-tphy.c` documents its setup logic as based on five functions from MediaTek's GPL-licensed publicly available SDK and links to MediaTek's `mtk_sgmii.c` and `mtk_eth_soc.c`:

- MediaTek source path: `21.02/files/target/linux/mediatek/files-5.4/drivers/net/ethernet/mediatek/mtk_sgmii.c`
- MediaTek Gitiles revision: `b72d6cba92bf9e29fb035c03052fa1e86664a25b`
- Reference URL: https://git01.mediatek.com/plugins/gitiles/openwrt/feeds/mtk-openwrt-feeds/+/b72d6cba92bf9e29fb035c03052fa1e86664a25b/21.02/files/target/linux/mediatek/files-5.4/drivers/net/ethernet/mediatek/mtk_sgmii.c

**Original SDK's exact corresponding function and line intervals have not yet been inspected**, particularly for the MT6990-specific Gen2 analog register table; the general `mtk_sgmii.c` reference alone does not prove its presence there. The MediaTek SDK version/branch carrying the MT6990 table must be separately identified before asserting exact correspondence.

## Decision and user-acquisition workflow

1. Keep the donor-adapted PHY and SDK-derived register table **out of this repository** until the original SDK source, its rights, and complete attribution chain have been mapped.
2. If the SDK redistribution grant cannot be demonstrated, provide upstream URL, immutable revision, file path, precise inclusive line intervals, checksum, and independent user-download instructions, without embedding restricted material in our releases.
3. User acquisition is not automatically legal merely because a URL is public: verify SDK terms and the conditions of use and redistribution.
4. Keep any downstream patches reviewable and GPL-compliant, retaining author notices and complete corresponding source obligations.
5. Release images only when third-party licensing, legal build dependencies and safety/recovery gates all pass.

日本語: 「SDKのどの行か」は、今のところ**ドナー変換済みPHYの127〜166行**まで確定。純正MediaTek SDKの原本の行番号とは混同しません。原本同定が終わるまで、該当実装の再配布は保留します。
