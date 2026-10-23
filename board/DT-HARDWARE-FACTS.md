# SBAT6D hardware facts used by the partial Device Tree

Status: partial implementation; not a bootable board tree.

## Source and identity

The hardware facts below were transcribed independently from a read-only
extraction of the B-unit `boot_b` FDT. The capture record identifies the
observation as the B-unit boot partition FDT and records RX-only UART capture
with zero transmitted UART bytes. The raw FDT and its unit-specific digest are
retained locally and are not published. Separate boot-artifact records tie the
same B unit to slot B and `boot_b`. The same unit later reached Linux 6.18.44
and established the MAC1/SGMII1/MT7531 path in a read-only volatile test; that
does not prove those nodes work from a cold boot.

No raw FDT, vendor DTS source, boot arguments, MAC address, calibration data,
or per-unit secret is included here.

## Implemented nodes

| Node/property | Recorded fact | Source/meaning | State in this branch |
|---|---|---|---|
| Root SoC compatible | `mediatek,mt6990` | B-unit boot_b FDT | Used as SoC fallback |
| Root platform compatible | `mediatek,evb6990_cpe_mt7990_emmc` | Exact compatible reported by the same FDT. It is retained as an observed firmware identifier; this does not relabel the retail product as a MediaTek evaluation board. | Added to the local root binding patch and board root |
| CPU nodes | Four `arm,cortex-a55` nodes with MPIDR values `0x000`, `0x100`, `0x200`, `0x300` | Same FDT | Added to `mt6990.dtsi`; frequency and cluster topology omitted |
| PSCI | `arm,psci-1.0`, `method = "smc"` | Same FDT | Added to `mt6990.dtsi` |
| GIC | `arm,gic-v3`; distributor `0x0c000000/0x40000`, redistributor `0x0c040000/0x200000`; maintenance PPI 9 | Same FDT | Added to `mt6990.dtsi` |
| Architected timer | `arm,armv8-timer`; PPIs 13, 14, 11, 10; recorded counter frequency 13 MHz | Same FDT | Added to `mt6990.dtsi`; runtime CNTFRQ consistency is unverified |

The IRQ type cells are rendered using the standard GIC encoding: PPI type 1
and level-high flag 4. Node structure and IRQ order follow the Linux 6.18.55
ARM GIC and architected timer bindings.

## Deliberately not implemented or enabled

### Memory and reserved memory

The extracted FDT contains two root-level memory descriptions with the same
base `0x80000000` and different lengths (`0x3e605000` and `0x1e800000`). The
records overlap and do not establish which range is usable RAM after LK's
runtime changes and reserved-memory processing. The Linux 5.4 and later Linux
6.18 observations do not provide a same-boot `/proc/iomem`/memblock map tied to
this exact FDT payload. No `memory` node or reserved-memory range is therefore
copied into the partial tree.

### Storage and peripherals

The FDT reports eMMC controller `mediatek,mt6990-mmc` at `0x11230000` with
interrupt 260 and an 8-bit bus. Its clocks, power domain and pinctrl refer to
vendor providers for which Linux 6.18.55 has no verified MT6990 implementation
in this workstream. It is not yet added as an enabled node.

The observed PCIe roots are `0x11280000`, `0x11288000`, and `0x11290000`; the
Ethernet path is MAC1/SGMII1/MT7531 CPU port 5. Existing reports establish
some addresses and runtime behavior, but not a complete same-FDT resolution
of provider IDs, PHY/PCS links, clocks, resets, regulators, GPIOs and power
domains. These devices remain out of the enabled tree. Their reported runtime
success does not establish persistent initialization from this DTS.

## Build and binding state

The source is intended to compile as a research DTB. The root binding patch
adds only the two observed root compatibles. No subsystem binding or driver
implementation is claimed for MT6990 clocks, pinctrl, power domains, MMC,
PCIe, SGMII/PHY, Ethernet or DSA. `dtbs_check` and device boot validation are
separate required gates and have not passed for this partial tree.
