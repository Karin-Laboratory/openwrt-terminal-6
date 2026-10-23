# Air Terminal 6 board bring-up

`sbat6d-incomplete.dts` is an independently authored, deliberately
non-bootable research DTS. It includes `mt6990.dtsi`, which now records the
B-unit FDT's four Cortex-A55 CPU nodes, PSCI SMC conduit, GICv3 registers and
maintenance interrupt, and architected timer PPIs. `DT-HARDWARE-FACTS.md`
traces each value to the local read-only FDT capture and explains why the
memory map and peripheral nodes remain absent. These additions make this a
partial SoC/board tree, not a completed or bootable SBAT6D DTS.

`patches/0001-arm-dt-mediatek-add-mt6990-root-compatible.patch` adds the two
root compatibles observed in that FDT to Linux's MediaTek root binding. The
firmware reports an EVB-named compatibility string; this does not establish
that the retail SBAT6D is a MediaTek evaluation board. The modified binding
and this partial target DTB pass targeted Linux 6.18.55 schema validation.

`air-terminal-6.json` captures **observed** CPU5 / MAC1 / SGMII1 / MT7531 and MT7990 identifiers from the developer tests. It deliberately is **not a Device Tree** or an image recipe. The donor's 172 kB LG6851F DTS is explicitly derived from the donor's original boot image and must not be renamed, copied, or treated as evidence of Air Terminal 6's compatible topology.

Do not merge the donor's `Device/fiberhome_lg6851f` into a purported Air Terminal 6 target. The donor's `target/linux/mediatek/image/mt6990.mk` unconditionally defines LG6851F-specific Android boot packaging and a board DTS. A separate target requires a fully validated Air Terminal 6 DTS and explicit removal of vendor signing/package assumptions.

**Next engineering inputs:** 1) authoritative LK-adjusted usable RAM and reserved-memory map, 2) MT6990 clock/reset/genpd/pinctrl provider data plus redistributable driver support, 3) same-FDT eMMC/PCIe/Ethernet dependency resolution, 4) supported MT6990 subsystem bindings and drivers, 5) successful `dtbs_check`, 6) a separately approved cold-boot test plan.

This folder is publicly safe factual metadata; it contains no OEM DTS extraction, firmware, unique EEPROM, vendor keys or installation command.
