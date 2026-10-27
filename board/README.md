# Experimental SGMII1 Ethernet board evidence

**Status: OFFLINE EVIDENCE ONLY. This directory is not a board DTS, installable DTB, flash image, signed payload or proof of cold-boot bring-up.**

## Independently reported hardware observations

- MT6990 development unit with Ethernet MAC1 / `eth1` and SGMII1 path toward an MT7531 switch (CPU port 5, observed DSA `lan2`).
- Digital SGMII1 system `0x11305000`, analog PHY `0x11e60000`, observed shared PLL region `0x10014000`. These are general SoC register observations, **not** per-device secrets or proof of kernel clock/reset-provider correctness.
- Development testing showed a 100 Mb/s physical peer link on a Raspberry Pi 2 and packet transfer after volatile configuration. This **does not** prove a 2.5GbE physical port, permanent board wiring or automatic cold-boot network initialization.
- Wi-Fi reports distinguished 2.4/5 GHz functional traffic, 6 GHz AP initialization, and unverified outside 6 GHz client association/EHT/MLO.
- Modem Stage9B/10 historical LTE IPv4 data SUCCESS was recovered later than the original board ledger. NR and IPv6 remain UNVERIFIED.

## Safely imported files

- `mt6990-air-terminal-6-sgmii1-experimental.dtso`: source-only GPL-2.0 overlay with **both target fragments disabled**. Copied byte-for-byte from the preserved Private v1 source tree. It records a possible PHY consumer link without guessing clock, reset, PLL or power-domain providers.
- `air-terminal-6.json`: sanitized source-derived hardware inventory from v1, updated here to reflect later Stage10 **LTE IPv4** evidence while maintaining explicit NR/IPv6 exclusions. This is an observation record, not a machine-authoritative firmware configuration.
- `tools/board/verify_sgmii_overlay.py` and its tests: independent lexical sanity checks, including fail-closed assertions that both experimental fragments stay disabled and no per-device MAC, EEPROM or firmware content is embedded.

These files contain **no OEM decompiled DTS**, no proprietary kernel binaries, signed partition payloads, factory radio calibration, modem NV/provisioning, bootloader security proof or installation commands.

## Required before real kernel DTS integration

1. Independently establish a rights-cleared full MT6990 base SoC DTS and correct Linux Device Tree binding schemas.
2. Resolve all clocks, resets, pinctrl and power domains, check PHY/PCS ownership and avoid toggling shared PLL/SPM domains under other consumers.
3. Use `dtc` (syntactic check), `dtbs_check` (binding check), and a real ARM64 kernel build with reproducible sources.
4. Verify boot-state recovery without depending on uncertain A/B failover, then assess persistent Ethernet and DSA setup on a development device with independent recovery.
5. Confirm license provenance of the board overlay and future device tree before submitting upstream.

**A passing overlay lexical test does not permit enabling either node.**
