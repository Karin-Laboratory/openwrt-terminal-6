# NETSYS + SGMII1: Air6 Ethernet cold-boot candidate (source-only)

2026-10-29. **Syntax/integration candidate. Not boot-tested, not installable firmware.**

## Inputs and status

- [Base board file](../board/mt6990-air-terminal-6.dts): deliberate **disabled** Ethernet, MMC, PCIe and USB gates.
- [Opt-in Ethernet variant](../board/mt6990-air-terminal-6-ethernet-test.dts): derives from the base and enables only the observed MAC1→SGMII1→MT7531 CPU5 path. It **does not** enable eMMC or Wi-Fi, contain an Air6 rootfs/DRAM map, or constitute a bootable OpenWrt distribution.
- [PHY reset delta](../patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch): applies to the exact pinned GPL donor PHY source, with no attempt to rediscover or toggle a live PM domain.
- [Source verifier](../scripts/verify-air6-board-dtc.sh): compiles both variants against a pinned MT6990 SoC DTSI and specific GPL/MT6990 clock and power binding headers, validates the opt-in parent/child topology after DTB roundtrip and checks PHY patch applicability. **No DTB or executable image is committed**.

## Why the structure matters

The 2026-10-21/22 private Test22 detected:
1. Original runtime path `/netsys@15100000/ethernet@15100000`, both nodes present.
2. Parent NETSYS platform device present, **unbound**. Neither `mediatek,mt6990-netsys` nor its legacy properties matched the Linux 6.18 default bus table; its Ethernet child was not automatically populated.
3. Manual `devm_of_platform_populate` registered an Ethernet child with no valid MEM resource, before MAC MMIO access. The historical runtime NETSYS lacked explicit `#address-cells` and `#size-cells`; `ranges` alone did not guarantee address translation.
4. A later diagnostic with an explicit translated resource established MAC netdev/MT7531 DSA user ports, but PHY/PCS/DMA were not yet initialized.
5. Test24's volatile PLL→PCS→Gen2 analog PHY initialization enabled **bidirectional IPv4 traffic** through **MAC1→CPU5→switch port1**, confirming this particular path (not all RJ45 ports or a permanent cold boot).

The opt-in variant keeps the **existing nested Ethernet path**, sets NETSYS's `simple-bus` fallback plus explicit 2/2 cell translation, and binds `sgmiisys1` to a real `mediatek,mt6990-sgmii-phy` provider with a syscon-referenced shared PLL and SGMII_TOP_1 genpd. It supplies known six SGMII selector clocks and the eight FE interrupt inputs from the pinned MT6990 bindings.

Unlike the Test23 synthetic/manual population methods, this candidate is intended to use the kernel's standard OF bus enumeration and resource translation. The default file remains unchanged and safe.

## Required matching driver stack

DTS alone cannot configure a SerDes. The target kernel must have **compatible, built and correctly registered**:

- The MT6990 NETSYS/FE driver, including correct DMA descriptors, interrupts and MT6990 MAC1 DMA routing.
- MT7531 DSA switch, MDIO access, CPU port5 special-tag handling and 2500base-x phylink/fixed-link support.
- MT6990 topckgen, SGMII TOP genpd and compatible LynxI PCS code, including its MT6990 force-2.5G path and **actual** SerDes `phys` consumption. Donor versions were not all interchangeable.
- MT6990 analog PHY driver and reset/PM contract. The reference driver at the pinned donor revision calls a destructive `mt6990_sgmii_top_cycle()` during `phy_reset()`, despite comments implying otherwise. The new patch removes that call and preserves the shared PLL and power-domain ownership. Its application alone is **not a compiled-kernel or runtime PASS**.
- A kernel configuration and image packaging path already known to boot the **actual Air6**. Do **not** replace the original Air6 active FDT with a different product's DTS, and do not use a vendor-key/signing shortcut as an assumption.

## Runtime validation gates, not yet performed

| Gate | Observation required | Failure investigation |
| --- | --- | --- |
| 1. Boot / FDT identity | Running FDT contains the candidate NETSYS `simple-bus` parent, PHY1, PLL syscon and correct MAC1/CPU5 relations | Bootloader rewriting DT / mismatched DTB |
| 2. OF and MMIO | `15100000.netsys` creates Ethernet child with valid `0x15100000–0x1512ffff` translated MEM resource. No second driver claims overlapping NETSYS MMIO | Missing bus cell translation / competing NETSYS owner |
| 3. Providers / probe | Clock, SGMII_TOP1 genpd, PHY provider and LynxI PCS all bind/defer correctly; no double genpd attach or unbalanced runtime-PM | Provider configuration, `-EPROBE_DEFER`, `-EEXIST` |
| 4. PHY/PCS initialization | Shared PLL stays on, PCS1 force-mode and analog1 Gen2 settings match Test24 readback **without TOP cycle** | Driver source mismatch / order / PHY reset |
| 5. DSA and MAC | MT7531 at MDIO31, CPU5/MAC1 link, port1 PHY, tagged frames and DMA counters | Switch reset/DSA tag/NETSYS TX hang |
| 6. IP and recovery | 3 cold boots, bidirectional ARP/ICMP/SSH and sustained traffic, no modem/management regression; safe recovery verified | Revert candidate, compare saved healthy image |

**No gate in this table has been executed with the new source as of 2026-10-29.** Do not mark the board as production-ready based on the automated DTC test.

## Safety / upstream boundaries

This work changes **GitHub source text only**. No code executed on Air6, no eMMC access, no LK/Preloader modifications, no secret or per-device EEPROM export, no image signing, no firmware artifact.

The two independently observed MAC/port mappings are hardware evidence. The parent-bus compatibility, reference PHY reset patch and provider coupling are engineering proposals. License review for every newly published source delta remains pending. The complete Air6 board DTS and general-purpose clean OpenWrt image are **not complete**.

Do not put the opt-in variant into a firmware recipe until matching SoC/PHY/PCS/DSA driver ABI and the safe fallback/test path have been reviewed. See [Issue #20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20).
