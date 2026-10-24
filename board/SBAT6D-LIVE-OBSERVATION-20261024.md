# SBAT6D read-only runtime observation — 2026-10-24

## Scope and identity

This was a read-only SSH observation of the physical B unit through its
existing Raspberry Pi gateway. SSH host-key checking remained strict and used
an already stored Test27-specific host-key pin and the existing B-unit key.
The observed root model was `MediaTek evb6990_cpe_mt7990_emmc`.

The unit was running **slot A**, Linux **6.18.44**. This is an A-slot runtime
snapshot from the physical B unit; it is not evidence of the current B-slot
FDT or B-slot Linux memory map. No reboot, slot change, write, service change,
or modem operation was performed. No raw FDT, complete command line, MAC,
serial, host key, or credential is included here.

## RAM observations

The live FDT reported two overlapping root memory descriptions, both starting
at `0x80000000`:

| FDT node | start | size | interpretation |
|---|---:|---:|---|
| `/memory` | `0x80000000` | `0x80000000` (2 GiB) | Nominal physical window `[0x80000000, 0x100000000)` |
| `/memory@80000000` | `0x80000000` | `0x1e800000` (488 MiB) | Overlapping, shorter duplicate; inconsistent with the first node |

Linux `/proc/iomem` showed discontiguous `System RAM` ranges within the nominal
2 GiB window, with reserved holes and reserved subranges. `/proc/meminfo`
reported `MemTotal: 1758560 kB` (about 1.68 GiB). `MemTotal` is Linux-usable
memory, not a measurement of installed physical capacity. The live mapping is
consistent with Linux using substantially more memory than the shorter
duplicate FDT node describes, but the duplicate nodes make this FDT unsuitable
as the sole basis for a clean board DTS.

The FDT also contained fixed reservations associated with secure/ATF state,
modem/CCCI, MedMCU, SSPM/MCUPM, WOC/consys, diagnostics, boot metadata and
pstore, plus a dynamic GPS reservation (384 KiB, 64 KiB alignment). Their
individual addresses and raw properties are intentionally omitted. The
Linux memory map confirms that reservations are materially affecting the
usable map; it does not establish that every firmware reservation is required
or safe to copy into the public board DTS.

### RAM conclusion

- **Confirmed for this slot-A boot:** the live FDT contains the two ranges
  above; Linux reports 1,758,560 kB usable and discontiguous RAM/reservations.
- **Not confirmed:** the final B-slot FDT, the exact physical DIMM/DRAM
  topology independently of firmware, and a complete non-overlapping
  reserved-memory map suitable for Linux 6.18.55 DTS.
- **DTS decision:** leave `memory` and `reserved-memory` out of the partial
  DTS. Do not select either FDT range or copy the vendor reservation list yet.

## Runtime driver evidence

Read-only platform-device binding inspection found:

| Function | observed binding |
|---|---|
| UART0 (`11002000`) | `mt6577-uart` |
| eMMC (`11230000`) | `mtk-msdc` |
| PCIe domains 0 and 1 (`11280000`, `11288000`) | `mtk-pcie-gen3` |
| PCIe domain 2 (`11290000`) | no driver bound |
| NETSYS (`15100000`) | `test23_netsys_fixedlink` |
| SGMII system and analog PHY (`11305000`, `11e60000`) | no driver bound |

These bindings describe this Linux 6.18.44 A-slot test boot. The experimental
NETSYS binding is not evidence of upstream Ethernet support. The observation
does not establish clock/reset/genpd IDs or a complete consumer initialization
sequence. Existing clock-provider indices and disabled provider nodes remain
firmware observations documented in `DT-HARDWARE-FACTS.md`; no provider was
enabled as a result of this test.

## Collection and reproducibility

The session recorded, without modifying the device:

- kernel release and the `bootslot` token from `/proc/cmdline`;
- selected `/proc/meminfo` counters and `/proc/iomem`;
- the `reg` properties of root memory and reserved-memory nodes;
- platform-device `driver` symlinks.

The FDT `reg` bytes were decoded locally as big-endian cells. The source FDT
was not committed. Because the device was on slot A, a future B-slot capture
must repeat these reads in one B-slot boot and pair them with the same boot's
slot/root partition and kernel identity before updating B-slot conclusions.
