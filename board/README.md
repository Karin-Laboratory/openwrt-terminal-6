# Air Terminal 6 board bring-up

`sbat6d-incomplete.dts` is an independently authored, deliberately
non-bootable research DTS. It includes `mt6990.dtsi` for the B-unit FDT's
four Cortex-A55 nodes, PSCI SMC, GICv3 and architected timer. It also includes
`mt6990-observed-peripherals.dtsi`, which now records the observed UART0,
eMMC, three PCIe roots and PHYs, NETSYS/MAC0/MAC1 and SGMII1 resources. Those
peripheral nodes are all explicitly disabled because their provider/driver
dependencies are not implemented or verified in Linux 6.18.55. The two
conflicting RAM descriptions are documented but omitted. See
`DT-HARDWARE-FACTS.md` for same-FDT provider mapping and limits.

`patches/0001-arm-dt-mediatek-add-mt6990-root-compatible.patch` adds the two
root compatibles observed in that FDT to Linux's MediaTek root binding. The
firmware reports an EVB-named compatibility string; this does not establish
that the retail SBAT6D is a MediaTek evaluation board. The current DTS is an
observed, disabled inventory and not a complete driver-ready SoC/board tree.

`air-terminal-6.json` captures **observed** CPU5 / MAC1 / SGMII1 / MT7531 and MT7990 identifiers from the developer tests. It deliberately is **not a Device Tree** or an image recipe. The donor's 172 kB LG6851F DTS is explicitly derived from the donor's original boot image and must not be renamed, copied, or treated as evidence of Air Terminal 6's compatible topology.

The sanitized [2026-10-24 live observation](SBAT6D-LIVE-OBSERVATION-20261024.md) is from the physical B unit while it was running slot A on Linux 6.18.44. It documents overlapping runtime FDT memory nodes and Linux's usable-memory view; it is not B-slot memory evidence and does not resolve the board DTS reservation map.

Do not merge the donor's `Device/fiberhome_lg6851f` into a purported Air Terminal 6 target. The donor's `target/linux/mediatek/image/mt6990.mk` unconditionally defines LG6851F-specific Android boot packaging and a board DTS. A separate target requires a fully validated Air Terminal 6 DTS and explicit removal of vendor signing/package assumptions.

**Next engineering inputs:** 1) resolve the contradictory root memory map into an LK-adjusted usable/reserved map, 2) implement redistributable MT6990 clock/reset/genpd/pinctrl providers, 3) add reviewed MMC, PCIe, Ethernet/SGMII and switch bindings/drivers, 4) validate all disabled observation nodes with Linux 6.18.55 `dtbs_check`, 5) separately approved cold-boot tests.

This folder is publicly safe factual metadata; it contains no OEM DTS extraction, firmware, unique EEPROM, vendor keys or installation command.
