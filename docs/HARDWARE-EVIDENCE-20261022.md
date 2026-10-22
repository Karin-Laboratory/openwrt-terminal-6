# Hardware evidence and release boundaries (2026-10-22)

This summary is written from private development notes, without copying UART logs, factory calibration, firmware images, or per-device credentials. **Reports are from one developer-owned test unit, not third-party reproduction.**

## Ethernet

- Development notes describe a Linux 6.18.44 live experiment on the path CPU5 -> MAC1 -> SGMII1 -> MT7531.
- A Test25 candidate PHY source file exists privately at `openwrt-port/test25/phy-mtk-mt6990-sgmii-sba6d.c`, on branch `research/mt6990-test25-persistent-ethernet-build`.
- The private Test25 README explicitly states the staged candidate was **not compiled, signed, deployed or tested** when written. Live Test24 success must not be presented as successful persistent Test25 integration.
- That candidate cites an SDK-specific analog initialization sequence and a donor source revision. Treat origin/derivative licensing and attribution as **HOLD** pending upstream/source inspection; **do not import the candidate unchanged**.
- Persistent boot-time Ethernet configuration, repeated cold boots and independently reproducible build remain outstanding.

## Wireless

From the 2026-10-22 private Wi-Fi live bring-up record:

| Capability | Developer evidence | Still unverified |
| --- | --- | --- |
| PCIe enumeration | MT7990 endpoints, mt7996e and HIF bindings | Repeatability on other units |
| Firmware probe | ROM patch/WM/DSP/WA initialized | All blob licenses, redistributability |
| 2.4 GHz | AP enabled, station association/RSN handshake | Broad client coverage, stability, throughput |
| 5 GHz | AP enabled, DHCP and client-to-device ping | Reboot persistence, throughput, long-term stability |
| 6 GHz | WPA3-SAE / PMF AP enabled on 5975 MHz | Client scan, association, DHCP, traffic |
| EHT/MLO/320 MHz | No supporting test evidence | All |
| EEPROM/calibration | Per-device EEPROM was used in RAM | Legally supportable per-device acquisition at installation time |
| Reboot persistence | Changes were RAM-only | Cold boot configuration and release image |

Wi-Fi operation requires proprietary firmware and per-device board data whose redistribution permissions must be established independently. No EEPROM or extracted firmware data are released here. JP regulatory settings were followed in the developer report, but **do not assume deployment worldwide**.

## 5G modem

Not working under the public port; topology, drivers, firmware dependencies, and legal redistribution remain to be validated.

## Release decision

- Public documentation and original diagnostic tools: allowed after inspection.
- Historical debug logs and vendor-derived materials: not automatically releasable.
- Kernel, PCIe, MAC, SGMII and Wi-Fi patches: **HOLD for individual licensing/provenance review**.
- Signed installable image and device-unique data: **BLOCKED**.

The safe release target is an entirely source-based build whose **output remains non-installable** until independent device safety gates are passed.
