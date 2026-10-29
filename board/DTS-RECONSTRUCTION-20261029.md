# Air Terminal 6 Device Tree reconstruction: evidence and remaining dependencies

Date: 2026-10-29. Status: **independent full board DTS NOT YET AVAILABLE**.

This document consolidates non-sensitive, independently recorded hardware observations from the project's private research into a source-only upstream work item. It is **not** a generated vendor DTS, an installable board configuration, a DTB or a claim of autonomous cold-boot support. The existing [disabled-only SGMII1 example](mt6990-air-terminal-6-sgmii1-experimental.dtso) remains disabled.

## Source boundary

- In October 2026, offline private workflows extracted and syntax-round-tripped complete original A/B device trees from saved boot partitions. The output consisted of **vendor-derived FDT/DTS**, not an independently authored, reviewed Air6 DTS. No corresponding full DTS source was found in the checked GitHub research branches, and the historical extraction artifact is not available in the current accessible artifact listing.
- A complete donor board DTS exists for **FiberHome LG6851F**, pinned to [the shared MT6990 donor revision](../docs/OPENWRT-DONOR-SOURCE.md). It was generated from a *different product's* boot DTB and includes product-specific assignments. It cannot be relabelled as Air Terminal 6 or assumed correct.
- The project may reuse duly attributed, license-compatible upstream SoC support and independently establish Air6 board properties. Do not copy raw OEM decompilation, proprietary board calibration, partition images, certificates, or private keys to construct an apparently complete public file.

## Reconstructed observations, not a DTS

| Subsystem | Observed evidence | Remaining board-DTS task |
| --- | --- | --- |
| Ethernet path | Linux 6.18.44 device tests found MAC1 / eth1, SGMII1 / PCS1, MT7531 DSA CPU port 5 and user port 1 (`lan2`). A 100 Mb/s peer exchanged traffic after **volatile manual initialization**. | Verify complete clock, reset, genpd, PHY and MDIO bindings, cold-boot probe order, both external RJ45 assignments and other user ports. Fixed 2500base-x on the CPU side is not proof of 2.5Gbps external Ethernet. |
| Digital SGMII1 | Observed address 0x11305000; existing runtime path `/sgmiisys@11305000`. | Reconcile the driver-compatible, PHY consumer and actual clock references against the same DT; no guessed phandles. |
| Analog PHY1 / PLL | Observed PHY region 0x11e60000 and shared PLL region 0x10014000. | Establish a correct upstream binding/provider, power-domain ownership, reset behavior and safe shared PLL lifetime. |
| NETSYS | Historical FDT had `/netsys@15100000/ethernet@15100000` and both MAC child nodes. The nested child did not become the expected Linux 6.18 Ethernet platform device in one test. | Resolve parent-versus-child OF population, bootloader path assumptions, and resource ownership. A sibling-node rewrite was **offline/synthetic tested only**, not boot-proven. |
| NETSYS MMIO | Historical tree described NETSYS [0x15100000, 0x15120000) and Ethernet [0x15100000, 0x15130000), an overlapping 128 KiB region. | Resolve who requests the MMIO region at Linux probe time; do not blindly register duplicate owning drivers. |
| Wi-Fi PCIe | Endpoints 14c3:7990 / 14c3:7991 were observed. 2.4/5GHz client traffic was tested; a 6GHz AP was started, but external 6GHz association was not confirmed in this project. | Validate PCIe, reset and clocks; define an **independent per-device** factory-data acquisition path before driver probe. No EEPROM bytes, MACs or calibration files in public sources. |
| eMMC / other peripherals | Original FDT and Linux boot tests establish storage and some platform bring-up. | Independently audit MMC aliases and ordering, USB host and VBUS GPIO, thermal/fan, keys/LEDs and regulators. Do not import another board's pin mapping. |
| Cellular | Stage9B/10 historically achieved LTE IPv4 traffic on the research device. | Audit modem DMA/interrupts, memory regions, relevant SoC providers and private runtime dependencies separately; NR and IPv6 remain unverified. |
| A/B / chosen | The device uses distinct A/B boot and rootfs partitions; historical signed boot tests use per-slot images. | Avoid a hard-coded, donor-specific rootfs/bootargs assumption; independently establish LK and slot handoff requirements. |

## Minimum independently authored full-DTS gate

1. Establish a copyright/redistribution-audited MT6990 **SoC** DTSI and its actual Linux 6.18-compatible clock, pinctrl, interrupt, genpd, PHY, USB, MMC, thermal and other provider bindings. Distinguish missing providers from board wiring.
2. Author an Air6-specific board DTS (not the LG6851F donor, not a decompiled OEM DTS). Name it for the actual board revision only after verifying `model`, `compatible`, aliases and peripherals from independent evidence. Maintain provenance for each enabled node.
3. Verify Ethernet MMIO ownership, MAC1→SGMII1→MT7531 CPU5, MDIO switch address and true front-panel port mappings. Do not enable the existing experimental SGMII overlay by assumption.
4. Determine eMMC aliases, USB VBUS control, Wi-Fi PCIe and **per-unit** calibration provisioning, fan/thermal and front-panel controls from non-sensitive measurements; leave unsupported or unverified consumers disabled.
5. Run `dtc`, `dtbs_check`, and a pinned ARM64 kernel/DTB build against the actual matching source and binding versions. Compile success does not establish board equivalence.
6. Check that a standalone, redistributable board DTS passes the source catalog, rights review and no-secrets checks. Use device tests only under a separately reviewed recovery and boot-safety plan; log cold-boot, both Ethernet ports and radios independently.

**Completion criterion:** a published independently reviewed `*.dts` and applicable `*.dtsi` dependencies that compile against pinned, redistributable source, with per-node provenance and no fabricated clock/GPIO/PHY relationships. Until then, the public repo must continue to state `board_dts: NOT_YET_AVAILABLE`.

## Relation to peer implementations

Independent reports of working MT6990 router configurations are useful **comparison evidence**, not permission to copy a third party's DTS or to imply their runtime result applies to this code. Compare small patches with their author and their chosen license; request consent before importing non-public changes. An actual source diff and own-device test evidence are required before marking a feature reproduced.

## Internal research provenance (facts, not redistributed blobs)

- Private Test19: static and runtime NETSYS/Ethernet child enumeration observations.
- Private Test23: synthetic hierarchical FDT transformation and overlapping MMIO audit; **offline-only**.
- Private Test24/25: volatile Ethernet success and PHY/PCS/power sequencing investigation.
- Private Wi-Fi bring-up, 2026-10-22: per-device calibration source separation and 2.4/5 GHz connectivity observations.
- Public baseline: [board inventory](air-terminal-6.json), [board README](README.md), [engineering status](../docs/ENGINEERING-STATUS-20261027.md), and [source provenance](../docs/PROVENANCE.md).

No device operation, flash write, firmware signing or private data export is needed to maintain this ledger.
