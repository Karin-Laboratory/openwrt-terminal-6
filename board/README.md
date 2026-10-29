# Air6 board Device Tree source and evidence

**Status: independently authored board DTS candidate, offline source only.** `mt6990-air-terminal-6.dts` is a compile-time integration candidate, **not** a validated full board hardware definition, bootable DTB, signed payload or firmware image. Untested peripherals remain disabled.

## Independently reported hardware observations

- MT6990 development unit with Ethernet MAC1 / `eth1` and SGMII1 path toward an MT7531 switch (CPU port 5, observed DSA `lan2`).
- Digital SGMII1 system `0x11305000`, analog PHY `0x11e60000`, observed shared PLL region `0x10014000`. These are general SoC register observations, **not** per-device secrets or proof of kernel clock/reset-provider correctness.
- Development testing showed a 100 Mb/s physical peer link on a Raspberry Pi 2 and packet transfer after volatile configuration. This **does not** prove a 2.5GbE physical port, permanent board wiring or automatic cold-boot network initialization.
- Wi-Fi reports distinguished 2.4/5 GHz functional traffic, 6 GHz AP initialization, and unverified outside 6 GHz client association/EHT/MLO.
- Modem Stage9B/10 historical LTE IPv4 data SUCCESS was recovered later than the original board ledger. NR and IPv6 remain UNVERIFIED.

For the currently verified board-specific evidence, missing providers and independent full-DTS reconstruction conditions, see [Air6 DTS reconstruction (2026-10-29)](DTS-RECONSTRUCTION-20261029.md). A new independently authored [Air6 board DTS source candidate](mt6990-air-terminal-6.dts) now exists. It depends on the separately pinned GPL-identified MT6990 SoC DTSI and cannot yet be described as complete/boot-validated. [Source-only syntax verifier](../scripts/verify-air6-board-dtc.sh).

## Independently authored board DTS candidate

- [`mt6990-air-terminal-6.dts`](mt6990-air-terminal-6.dts): independently written Air6 board-specific topology, including MAC1 → SGMII1 / MDIO31 MT7531 CPU5 and the observed user port1, UART, MMC numbering aliases and explicit disabled peripheral gates. It deliberately has no memory map, OEM calibration, bootargs, signing or firmware artifacts. All non-proven Ethernet, USB, MMC and PCIe consumers stay disabled.
- `bash scripts/verify-air6-board-dtc.sh` performs a pinned source-only SoC/DTC compile and DTB roundtrip, **without distributing the output**. The SoC baseline is the GPL/MIT-identified 969 patch at donor commit `a40df9a`, not the LG6851F board `.dts`. See the [reconstruction ledger](DTS-RECONSTRUCTION-20261029.md).

## Safely imported files

- `mt6990-air-terminal-6-sgmii1-experimental.dtso`: source-only GPL-2.0 overlay with **both target fragments disabled**. Copied byte-for-byte from the preserved Private v1 source tree. It records a possible PHY consumer link without guessing clock, reset, PLL or power-domain providers.
- `air-terminal-6.json`: sanitized source-derived hardware inventory from v1, updated here to reflect later Stage10 **LTE IPv4** evidence while maintaining explicit NR/IPv6 exclusions. This is an observation record, not a machine-authoritative firmware configuration.
- `tools/board/verify_sgmii_overlay.py` and its tests: independent lexical sanity checks, including fail-closed assertions that both experimental fragments stay disabled and no per-device MAC, EEPROM or firmware content is embedded.

These files contain **no OEM decompiled DTS**, no proprietary kernel binaries, signed partition payloads, factory radio calibration, modem NV/provisioning, bootloader security proof or installation commands.

## Reproducible syntax-only dtc check

`bash scripts/verify-disabled-sgmii-dtc.sh` checks the independent safety model, downloads pinned Linux v6.18 into a temporary directory, builds the host `scripts_dtc` binary without sudo, compiles this overlay and checks both fragments remain disabled after DTB roundtrip. Private v2 isolated [standalone dtc source build #40475280436](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40475280436) emitted `STANDALONE_DTC_V1_7_2_DISABLED_SGMII_PASS` after a full overlay compile/roundtrip. The earlier full Linux v6.18 dtc proof #40473252747 also succeeded; reproducing that via a large clone proved unreliable. No DTBO/image is distributed; no clock/power provider was validated.

## Required before real kernel DTS integration

1. Independently establish a rights-cleared full MT6990 base SoC DTS and correct Linux Device Tree binding schemas.
2. Resolve all clocks, resets, pinctrl and power domains, check PHY/PCS ownership and avoid toggling shared PLL/SPM domains under other consumers.
3. Use `dtc` (syntactic check), `dtbs_check` (binding check), and a real ARM64 kernel build with reproducible sources.
4. Verify boot-state recovery without depending on uncertain A/B failover, then assess persistent Ethernet and DSA setup on a development device with independent recovery.
5. Confirm license provenance of the board overlay and future device tree before submitting upstream.

**A passing overlay lexical test does not permit enabling either node.**
