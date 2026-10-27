# Source origin, licenses and evidence boundaries

This repository was constructed in a **new Git history** by selecting individual source files rather than cloning or rebasing the private research archive. Rights review remains ongoing after the repository became Public; publication is not independent approval of third-party redistribution rights.

## New board research source attribution

The experimental disabled-only SGMII1 overlay is sourced byte-for-byte from `Karin-Laboratory/archive-openwrt-terminal-6-v1` at `board/mt6990-air-terminal-6-sgmii1-experimental.dtso` and keeps its GPL-2.0-only SPDX notice. The generalized board JSON was independently adapted from the v1 factual inventory, only to reflect later verified LTE IPv4 versus still-unproven NR/IPv6. No vendor-decompiled DTS, EEPROM, bootloader image or private firmware source was imported. File-by-file contributor rights remain pending.

## Source classes

| Files | Origin | Terms and caveats |
| --- | --- | --- |
| `patches/rfc/*.patch` | Proposed changes against upstream Linux v6.18 MediaTek Ethernet driver | **GPL-2.0-only** kernel derivative; preserve original kernel copyright and upstream source attribution. No implied upstream acceptance or completed Signed-off-by |
| `patches/mt6990/*.patch` | Research-derived minimal Stage10 Ethernet/MED DMA delta against an exact modified parent kernel | **GPL-2.0-only** parent; exact parent is NOT the generic Linux v6.18 tree; neither parent source nor vendor binaries supplied |
| `scripts/research/sba6d_stage10_clean_patch.py` | Project-authored transformation embedding Linux-related driver helper C code | Conservatively marked **GPL-2.0-only**; exact kernel patch and generated kernel source remain GPL-derived, not MIT | 
| `tests/test_sba6d_stage10_clean_patch.py` | Standalone, project-authored transformer unit test | SPDX MIT (independent test only) |
| `tests/test_stage10_mmio_model.py` | Project-authored host-only fake-MMIO regression harness | SPDX MIT; does not touch devices |
| `examples/fe-recovery/*` | Project-authored independent C state machine and tests | SPDX MIT where indicated; **not** a complete kernel driver |
| `tools/modem/*` | Project-authored synthetic modem model and source verifier | SPDX MIT where indicated; not CCCI/MIPC wire implementation |
| `tools/check_mediatek_rfc_series.py` and `scripts/apply-public-rfc-series.sh` | Project-authored source validation helpers | SPDX MIT where indicated; build tooling only |
| Documentation | Independent project summaries from research experiments | Not vendor dumps, source binaries, firmware or confidential test records |

MIT license text is available under [`LICENSES/MIT.txt`](../LICENSES/MIT.txt). The original Linux v6.18 GPL-2.0 license copy, byte-for-byte from [`torvalds/linux` LICENSES/preferred/GPL-2.0](https://github.com/torvalds/linux/blob/v6.18/LICENSES/preferred/GPL-2.0), is retained in [`LICENSES/GPL-2.0`](../LICENSES/GPL-2.0) (upstream Git blob `ea8e93dc44bc462a2be34e484432cf2b9ec88527`). GPL-2.0-only Linux patch derivatives **and the transformer embedding driver helper code** remain under Linux GPL terms. This is intentionally **not** a blanket MIT license for the whole repository.

## Independent reproduction status

The Stage10 research fix has a pinned source identity and a deterministic transformation check, together with a hardware-free C MMIO test. Prior retained-builder checking confirmed an ARM64 Ethernet object compile and matching source/image hashes. The original proprietary/third-party kernel baseline, firmware and provisioning data are NOT part of this repo. The available checks prove neither an independent full firmware build nor NR data operation.

For a future fully reproducible upstream port, publish a rights-cleared kernel/SoC tree, device-tree bindings, OpenWrt feeds/build config and redistributable runtime dependencies. Preserve attribution for every imported component and never manufacture a third-party contributor sign-off.

## Never import

Signing materials or sample key copies, OEM firmware and calibration, chip-unique provisioning, SIM/subscriber details, private device/network endpoints, historical signed partitions, unaudited build outputs, or confidential vulnerability evidence. Their archival retention does not make them redistributable.

## Source/test catalog coverage (2026-10-27)

The [source catalog](../config/source-catalog.json) records version-pinned identities for covered source, test, shell, Makefile, and board paths; the initial 27-path snapshot has subsequently expanded, each with exact Git blob identity. The catalog validator rejects unregistered new code. All entries retain `rights_review=pending`, intentionally preventing source identity from being mistaken for legal clearance. See [build contract](BUILD-CONTRACT.md).

## Pinned MT6990 donor source boundary

The new independent script `scripts/fetch-pinned-openwrt-donor.sh` refers to a public, exact-version source checkout, not a vendor binary mirror. Its reference implementation is derived from the original project's source-only acquisition pattern, but was independently rewritten for this clean repo. The donor carries LG6851F image/rootfs assumptions and must not be treated as a redistributable or flashable SBAT6 target. Details: [OpenWrt donor source review](OPENWRT-DONOR-SOURCE.md). New script/test file rights review remains pending.

### Donor source safety correction (2026-10-27)

The donor contains Wi-Fi EEPROM/firmware binary paths and a multi-megabyte communications firmware image of unclear independent reuse/redistribution rights. The source-inspection script was restricted to four independently blob-pinned text files and now **never checks out the donor tree**. All binary-bearing paths remain excluded. Full OpenWrt source acquisition and build require a separate, explicitly vetted rights-safe process.
