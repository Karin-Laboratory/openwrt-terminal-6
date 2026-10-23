# SBAT6D hardware facts used by the partial Device Tree

Status: partial implementation; not a bootable board tree.

## Source and identity

The hardware facts below were transcribed independently from the B-unit
`boot_b` FDT record collected on 2026-10-22 (Test20). Its paired read-only
capture identifies slot B, rootfs `mmcblk0p39`, boot partition `mmcblk0p38`,
and RX-only UART collection with zero transmitted UART bytes. The raw FDT and
its unit-specific digest are retained locally and are not published. A later
Linux 6.18.44 read-only observation established the MAC1/SGMII1/MT7531 path;
that does not prove those nodes work from a cold boot.

No raw FDT, vendor DTS source, boot arguments, MAC address, calibration data,
or per-unit secret is included here.

The Test20 UART boot log is a separate source from the static `boot_b` FDT and
the later slot-B Linux snapshot: its command line records slot A/rootfs
`mmcblk0p26`. It reports LK's DRAM base/size as `0x80000000`/`0x80000000`,
logs that it sets the FDT memory `reg` property from mblock information, and
reports successful appending of reserved-memory information before jumping
to Linux. This is LK-side evidence from that boot, not a post-LK FDT or Linux
memory map readback for the `boot_b` snapshot.

## Implemented nodes

| Node/property | Recorded fact | Source/meaning | State in this branch |
|---|---|---|---|
| Root SoC compatible | `mediatek,mt6990` | B-unit boot_b FDT | Used as SoC fallback |
| Root platform compatible | `mediatek,evb6990_cpe_mt7990_emmc` | Exact compatible reported by the same FDT. It is retained as an observed firmware identifier; this does not relabel the retail product as a MediaTek evaluation board. | Added to the local root binding patch and board root |
| CPU nodes | Four `arm,cortex-a55` nodes with MPIDR values `0x000`, `0x100`, `0x200`, `0x300` | Same FDT | Added to `mt6990.dtsi`; frequency and cluster topology omitted |
| PSCI | `arm,psci-1.0`, `method = "smc"` | Same FDT | Added to `mt6990.dtsi` |
| GIC | `arm,gic-v3`; distributor `0x0c000000/0x40000`, redistributor `0x0c040000/0x200000`; maintenance PPI 9 | Same FDT | Added to `mt6990.dtsi` |
| Architected timer | `arm,armv8-timer`; PPIs 13, 14, 11, 10; recorded counter frequency 13 MHz | Same FDT | Added to `mt6990.dtsi`; runtime CNTFRQ consistency is unverified |

## Additional boot_b FDT facts represented as disabled nodes

The same read-only B-unit `boot_b` FDT decompilation is paired with a live
read-only record showing `bootslot=b`, rootfs partition `mmcblk0p39`, and the
boot partition `mmcblk0p38` (`PARTNAME=boot_b`). No raw FDT bytes, full DTS,
per-unit hash, MAC address, GPIO initialization table, pinmux table, or
calibration data are published. The public DTS independently records only a
small set of node facts and sets every peripheral in
`mt6990-observed-peripherals.dtsi` to `status = "disabled"`.

| Block | Facts in the same FDT / matching runtime record | Source representation and limit |
|---|---|---|
| RAM | Two root memory descriptions share base `0x80000000`, with lengths `0x3e605000` and `0x1e800000`. The FDT also has fixed `no-map` WOC-CPU ranges at `0xa1be0000/0x40000`, `0xa1c20000/0x40000`, `0xa1c60000/0x40000`, and `0xa30a0000/0xf00000`; GPS reservation is dynamic (`size=0x60000`, `alignment=0x10000`, allocation window `0x40000000/0x80000000`). | No memory or reserved-memory nodes are emitted. The same-base length conflict does not establish Linux-usable RAM; fixed ranges are recorded but not reserved by this research DTS. |
| LK memory preparation | In a separate Test20 slot-A boot log, LK reports base `0x80000000`, total DRAM size `0x80000000`, sets a memory `reg` property from mblock information, and appends reserved-memory data before Linux entry. | This does not identify which duplicate node was changed or prove the final FDT contents, reservation coverage, or Linux-usable range for the captured slot-B FDT. No memory node is enabled from this evidence alone. |
| Clock/power providers | Fixed 26 MHz clock; clock-index providers `/syscon@10000000` (`mediatek,mt6990-topckgen`), `/syscon@11036000` (`mediatek,mt6990-pericfg_ao`), `/syscon@1200c000` (`mediatek,mt6990-vlpcfg`), `/syscon@12013000` (`mediatek,mt6990-vlp_cksys`); power provider `/power-controller@12001000` (`mediatek,mt6990-scpsys`, one domain cell). | Provider nodes are included with `status = "disabled"`; the clock index values are transcribed from consumers, not upstream clock binding IDs. No provider driver is implemented or enabled. |
| Pinctrl/GPIO provider | `/pinctrl@10004000`, compatible `mediatek,mt69xx-pinctrl`; ten named 0x1000 resource windows; GPIO and interrupt controller cell counts are 2. | A disabled observation node records only resource windows, names, and provider cell counts. Proprietary GPIO initialization tables, pinmux states, phandle values, and the EINT provider link are omitted. No matching upstream MT6990 pinctrl driver/binding is available in this Linux tree. |
| UART0 | `/serial@11002000`, compatible `mediatek,mt6873-uart` / `mediatek,mt6577-uart`, `0x11002000/0x1000`, GIC SPI 232; boot command line names `ttyS0` at 115200. Baud clock is the fixed 26 MHz source; bus clock is `/syscon@11036000`, ID `0`. | Disabled observation node includes both clock references. The Linux 6.18.55 UART binding did not list the observed first compatible, although the driver match table accepts the generic second compatible. A minimal binding enum patch adds the observed string so the recorded two-string compatible tuple can be schema-validated; this does not add a driver match or establish UART operation. The node remains disabled. DMA and pinctrl are omitted. |
| eMMC | `/mmc@11230000`, compatible `mediatek,mt6990-mmc`, resources `0x11230000/0x1000` and `0x11f00000/0x1000`, GIC SPI 260, 8-bit, non-removable. Four named clocks refer to `/syscon@11036000` IDs `0x18`, `0x19`, `0x1b`, `0x1a`; power domain provider `/power-controller@12001000`, ID `0x06`; pinctrl states point into `/pinctrl@10004000`. | Disabled node includes observed clocks and power-domain reference to disabled observation providers. Pinctrl and driver implementation remain absent. Linux 6.18.55 lacks a verified MT6990 MMC binding/provider integration in this workstream. |
| PCIe domain 0 | Controller `0x11280000/0x2000`, GIC SPI 288, bus 0–255, I/O window `0x30000000/0x10000000`; PHY `0x11310000/0x10000`, firmware-compatible `mediatek,mt6980-pcie-phy`, PHY ID 0. | Disabled controller and PHY node preserve the observed direct PHY link. FDT clock IDs use `/syscon@11036000` (`0x45`), `/syscon@1200c000` (`0`–`6`) and `/syscon@12013000` (`0x10`); power-domain provider domain `0x0f`. These clock/power references are now encoded to disabled providers. |
| PCIe domain 1 | Controller `0x11288000/0x2000`, GIC SPI 278, bus 0–255, I/O window `0x40000000/0x04000000`; PHY `0x11e00000/0x10000`, firmware-compatible `mediatek,mt6980-pcie-phy`, PHY ID 1. | Disabled controller and PHY node. FDT records power domain `0x0d`; clocks from `/syscon@11036000` IDs `0x2f`–`0x33`, `/syscon@10000000` IDs `0x18` and `0x3d`. |
| PCIe domain 2 | Controller `0x11290000/0x2000`, GIC SPI 279, bus 0–255, I/O window `0x44000000/0x04000000`; PHY `0x11e20000/0x10000`, firmware-compatible `mediatek,mt6980-pcie-phy`, PHY ID 2. | Disabled controller and PHY node. FDT records power domain `0x0e`; clocks from `/syscon@11036000` IDs `0x34`–`0x38`, `/syscon@10000000` IDs `0x18` and `0x3d`. |
| Ethernet syscon/reset | ETHSYS `0x15000000/0x1000` reports `#clock-cells = 1`, `#reset-cells = 1`; child `ti,syscon-reset` reports one seven-cell `ti,reset-bits` entry: `<0x34 0x04 0x34 0x04 0x34 0x04 0x28>`. | Provider and child reset controller are disabled. Linux 6.18.55 contains the generic `reset-ti-syscon` driver and its text binding. The record does not establish which Ethernet/SGMII consumer uses reset index 0, so no `resets` consumer reference is added. |
| Ethernet | NETSYS `0x15100000/0x20000`, nested Ethernet `0x15100000/0x30000`; MAC nodes 0 and 1 report `2500base-x`. A live interface-to-OF-node observation maps `eth0` to `mac@1`; separate live tests map MAC1 to SGMII1 and switch MT7531 CPU port 5. SGMII1 is `0x11305000/0x1000`, analog PHY1 `0x11e60000/0x10000`, shared PLL `0x10014000/0x1000`. | NETSYS/Ethernet clock and power references are recorded on disabled nodes. The firmware FDT also contains proprietary SGMII/PHY/PLL relationship properties; those are documented as observations but omitted from the research DTS because their values are not standard phandle-arrays and there is no upstream consumer binding. Consumer reset selection, interrupt wiring, provider/consumer driver support, and a mainline DSA description remain incomplete. Runtime link success is not cold-boot support. |

FDT numeric phandle values are not published as reusable IDs. In this one FDT,
the clock-provider phandles resolve to the paths listed above; the published
references use provider path and consumer clock ID instead. Clock IDs are
firmware-observed indices, not upstream clock-binding definitions. The
`mediatek,mt6980-pcie-phy` string is reproduced as the firmware's compatible
claim; this project does not infer that the MT6990 PCIe PHY is silicon-identical
to MT6980 or enable that driver.

The IRQ type cells are rendered using the standard GIC encoding: PPI type 1
and level-high flag 4. Node structure and IRQ order follow the Linux 6.18.55
ARM GIC and architected timer bindings.

## Deliberately not implemented or enabled

### Memory and reserved memory

The extracted `boot_b` FDT contains two root-level memory descriptions with
the same base `0x80000000` and different lengths (`0x3e605000` and
`0x1e800000`). A separate Test20 slot-A LK log reports 2 GiB total DRAM and an
LK update of a memory `reg` property plus reserved-memory append before Linux
entry. It does not capture the resulting FDT, identify which duplicate node
was changed, or provide the matching Linux `/proc/iomem`, `/proc/meminfo`, and
memblock state. The later slot-B Linux snapshot also lacks those memory
readbacks. The LK log therefore narrows the source of the discrepancy but
does not establish the usable or reserved ranges for this board DTS. No
`memory` or `reserved-memory` node is enabled from the current evidence.

### Storage and peripherals

The eMMC controller and three PCIe hosts now appear in a separate observation
include with `status = "disabled"`. Their known register windows, interrupts,
domain indices and eMMC bus width are recorded above; unverified clock, reset,
power-domain, pinctrl and provider implementation is not activated.

Ethernet MAC0/1, NETSYS, SGMII1, its analog PHY, UxPHYs and shared PLL appear
only as disabled observation nodes. The 6.18.55 Linux tree has no verified
MT6990 Ethernet/SGMII provider stack here; proprietary firmware phandle lists
are omitted from the DTS because their encoding is not a standard
phandle-array and no upstream consumer binding exists. Their observed endpoint
mapping stays in the fact table, and no generic `phys` link or driver behavior
is inferred. The MT7531 port-5 mapping is preserved as a measured fact, not
asserted as a validated mainline DSA topology.

## Build and binding state

The source is intended to compile as a research DTB. The root binding patch
adds only the two observed root compatibles. No subsystem binding or driver
implementation is claimed for MT6990 clocks, pinctrl, power domains, MMC,
PCIe, SGMII/PHY, Ethernet or DSA. `dtbs_check` and device boot validation are
separate required gates and have not passed for this partial tree.
