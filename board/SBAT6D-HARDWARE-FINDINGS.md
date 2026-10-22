# SBAT6A/SBA6D: experimentally observed hardware topology

Date: 2026-10-22. These are independently reported measurement findings, **not** copies of OEM DTS source, firmware, per-device calibration or signing material. The detailed private Test24/25 evidence has not yet been independently reproduced from the raw logs in this public repository.

## Ethernet observed on development unit (Test24)

| Observation | Result | Confidence |
| --- | --- | --- |
| Linux kernel | 6.18.44 | Test24 device report |
| Network master | `eth1`, Ethernet `mac@1` | Live observation |
| MAC → PCS | MAC1 → SGMII1 | Live observation |
| Digital SGMII1 register base | `0x11305000` | Live observation |
| Analog SGMII1 PHY base | `0x11e60000` | Live observation |
| Shared SGMII PLL base | `0x10014000` | Test24 bring-up observation; provider phandle unknown |
| Switch | MT7531, CPU port 5 | Live observation |
| User-facing DSA port | switch user port 1, Linux `lan2` | Live observation |
| Physical peer | Direct RJ45 connection to Raspberry Pi 2 | Test24 setup |
| Observed peer link | 100 Mb/s | Peer link observation, **not** 2.5GbE external link verification |
| Connectivity | Two-way ping, SSH and 4 MiB copy around 30 Mb/s | Test24, ephemeral initialization |

The donor's PCS may use a forced **2.5Gb/s internal CPU-side link**. That is not evidence of 2.5Gb/s speed at the RJ45 connector.

**Persistence limitation:** The Test24 physical link used volatile/runtime initialization. Cold-boot driver autoinitialization is **not yet verified**. The adaptation must not power-cycle a shared TOP domain or reset the shared PLL without demonstrating safe ownership and concurrency.

## Runtime device-tree properties reported from live observation

| Node or consumer | Reported properties / role | What is still missing |
| --- | --- | --- |
| `/sgmiisys@11305000` | `mediatek,colgin-sgmiisys_1` and `syscon`; no `phys` / `phy-names` at measurement | Driver-compatible, PHY consumer attachment and verified provider |
| `/sgmiiphy@11E60000` | `mediatek,colgin-sgmiisys_phy_1` and `syscon`; no direct power-domain reference at measurement | PHY binding, ID, PLL + SPM references and domain |
| Ethernet `mediatek,sgmiisys` | Two numeric references `0x6d`, `0x6e` | Resolve against **same** FDT source and verify ordering |
| Ethernet clock references | Observed provider number `0x24`; clock IDs `0x2e..0x33` | Resolve provider with `#clock-cells` in the same FDT |
| SGMII_TOP0/1 domains | On in one runtime snapshot | Ownership, genpd mapping, cold-boot and reset behavior |

**Crucial qualification:** Phandle numbers are local identifiers of an FDT and may change between static boot-DTB, LK-modified runtime FDT and rebuilds. Numbers copied from a separate FDT must never be used as fixed Linux DTS labels.

## Wi-Fi, modem and other limitations

- PCI endpoints `14c3:7990` and `14c3:7991` have been observed for the MT7990 family. 2.4/5 GHz client connectivity was tested with volatile configuration. A 6 GHz WPA3 AP started, but external 6 GHz client connectivity and full Wi-Fi 7 EHT/MLO are unverified.
- Do not distribute individual EEPROM/calibration. Firmware and board data must have independently reviewed redistribution rights.
- 5G modem bring-up is incomplete. PCIe enumeration evidence is not a working modem driver or datapath.
- A/B fallback and safe third-party installation remain unverified.

## From measurements to source

1. In the **private** environment, extract the original static DTB or runtime FDT; verify their identity, hash and provenance separately.
2. Resolve numeric handles, `#clock-cells`, `#power-domain-cells`, SGMII PHY / PLL / SPM mapping and MMIO ownership against that same FDT.
3. Write an **independently authored** SBA6D DTS or minimal overlay referencing actual provider labels, not synthetic addresses or copied fixed handles.
4. Validate with `dtc`, the 6.18.44 kernel device-tree bindings and `dtbs_check`, and then test source-only compilation.
5. Only after separately reviewing driver origin and recovering from failures should the project consider persistent live bring-up.

Research references: private `docs/ethernet/MT6990-TEST25-PERSISTENT-ETHERNET-PLAN.ja.md` and `docs/research/MT6990-TEST24-LIVE-CPU5-ETHERNET-SUCCESS.ja.md` on `Karin-Laboratory/SBAT6A-Offline-Archive`. These are evidence pointers, not distributable proprietary contents.

## Publication policy

**Publish:** hardware facts, independently verified observations, original diagrams/tables, negative findings, source diffs whose copyrights/licenses have been cleared, and derived reference mappings after removing identifiers.

**Do not mirror:** vendor DTB/DTS source text, OEM binaries, signing keys, original EEPROM/calibration blobs, MAC/IMEI/serial numbers, or unreviewed SDK code. Publishing a fact about a device is not identical to redistributing its vendor source. Significant copied register tables or code require origin/licensing review.
