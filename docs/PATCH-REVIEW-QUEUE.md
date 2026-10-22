# Patch review queue

This queue identifies concrete private development files to review, not files approved for publication.

| Order | Private file / branch | Review outcome and required action |
| --- | --- | --- |
| 1 | `openwrt-port/test25/phy-mtk-mt6990-sgmii-sba6d.c` on `research/mt6990-test25-persistent-ethernet-build` | **HOLD**. GPL-2.0-only SPDX header observed, but file describes SDK-derived initialization and donor origin; locate authorship, upstream patch lineage, notices and complete corresponding source before redistribution. It is a candidate, not proven boot code. |
| 2 | `scripts/research/test25_static_candidate_gate.sh` on same branch | **HOLD**. Read-only static checks for DTB and boot image, but refers to a privately signed artifact. Extract the public-safe source/DT validation subset after review; never publish private image/keys. |
| 3 | `docs/wifi/SBA6D-WIFI-RAM-BRINGUP-20261022.ja.md` on `research/sbat6d-wifi-live-20261022` | **HOLD source note**. Summarized findings publicly in HARDWARE-EVIDENCE; original includes private paths, laboratory topology and calibration handling. |
| 4 | MT6990 board DTS, OpenWrt target configuration, kernel patch series | **NOT LOCATED as verified release set**. Identify immutable source revision from successful Linux/OpenWrt boot build; don't infer it from research branch names. |
| 5 | Wi-Fi EEPROM and proprietary firmware | **BLOCK**. Do not copy; document legitimate device-local acquisition or compatible distributable firmware only after rights review. |

## Required provenance gates

For each source patch: original creator, source revision, upstream work and modifications, license notices, exact applied context, corresponding-source obligations, independent compilation, and evidence that it belongs to the successful image. A present SPDX line alone does **not** settle ownership or redistribution rights.

Do not move research code from the private git history into the public repository by mirroring.
