# Air Terminal 6 board bring-up

`sbat6d-incomplete.dts` is now a standalone, independently authored **syntax
scaffold** that records only the observed MT6990 compatible and product model.
It is deliberately missing boot-critical nodes and is not a working board DTS.
It compiles with `dtc`; this does not establish Linux binding compliance or
bootability.

`air-terminal-6.json` captures **observed** CPU5 / MAC1 / SGMII1 / MT7531 and MT7990 identifiers from the developer tests. It deliberately is **not a Device Tree** or an image recipe. The donor's 172 kB LG6851F DTS is explicitly derived from the donor's original boot image and must not be renamed, copied, or treated as evidence of Air Terminal 6's compatible topology.

Do not merge the donor's `Device/fiberhome_lg6851f` into a purported Air Terminal 6 target. The donor's `target/linux/mediatek/image/mt6990.mk` unconditionally defines LG6851F-specific Android boot packaging and a board DTS. A separate target requires a fully validated Air Terminal 6 DTS and explicit removal of vendor signing/package assumptions.

**Next engineering inputs:** 1) decompiled, provenance-reviewed Air Terminal 6 running FDT, 2) matching baseline kernel source tree and successful-image hashes, 3) PHY/PCS licensing and adaptation, 4) compile-only DTS validation (`dtc`/`dtbs_check`), 5) cold-boot test plan with dedicated device approval.

This folder is publicly safe factual metadata; it contains no OEM DTS extraction, firmware, unique EEPROM, vendor keys or installation command.
