# Technical status

Research snapshot: 2026-10-27. This project does not currently provide an installable device firmware or a supported OpenWrt target.

| Component | Observed in historical experiments | Available here | Remaining work |
| --- | --- | --- | --- |
| A/B boot control | Development-device slot selection reported | Strict, read-only, synthetic metadata observation model (no device IO) | LK retry/fallback conditions and independently proven rescue |
| Signed boot | Experimental accepted boot images reported | No signing code, SDK copy, test keys or signed payloads | Review input formats, legal sources and safe packaging privately |
| Linux kernel | Linux 6.18.44 boot observed | Source-only Ethernet RFC and Stage 10 delta | Fully rights-cleared independently reproduced kernel, SoC DTS and driver dependencies |
| OpenWrt userspace | procd and shell operated on development device | Fixed four-text-file source inspection script; no vendor binary checkout; synthetic host-side tools | Distinct SBAT6 build profile, pinned feeds, rootfs, packages and full clean build |
| Ethernet | Device link and packet tests succeeded | Upstream-review RFCs; Stage10 DMA delta; disabled-only SGMII1 overlay with pinned standalone dtc v1.7.2 syntax/roundtrip validation | Cold-boot init, complete board DTS, dtbs_check, upstream applicability and regression testing |
| Wi-Fi 2.4 / 5 GHz | Connectivity reported | No radio firmware, EEPROM or calibration | Open-source/redistribution audit, persistent configuration |
| Wi-Fi 6 GHz | Access point started | No radio binaries | Client association, EHT/MLO and regulatory validation |
| Modem LTE IPv4 | **Stage 9B/10 OpenWrt packet traffic succeeded** | Stage10 source-only patch, deterministic transformation and offline tests | Full public-build recovery and legally redistributable runtime |
| Modem 5G NR | **Not verified** | No NR implementation claim | Registration and end-to-end NR packet evidence |
| Modem IPv6 | **Not verified** | No IPv6 claim | IPv6 PDU/session and traffic tests |

## Observed LTE packet success

On 2026-10-25, Stage 9B restored the initial DMA configuration manually and achieved bidirectional IPv4 data. Stage 10 preserved MED-related DMA registers around the initial Ethernet reset, then recorded ping, DNS resolution and HTTPS 200 with TLS certificate verification without using the manual restoration in that replay.

These experiments used a retained, modified MT6990 vendor-capable Linux/OpenWrt source baseline and separate private runtime/provisioning assets. Historical file SHA-256 comparisons link the modified source and actually booted image. The current public candidate is **not** a standalone reproduction of that firmware and does not include the original confidential binaries, full kernel configuration or signing inputs.

The Stage10 change depends on precise MMIO assumptions from that research baseline; it must not be treated as a generic MediaTek kernel patch or safe deployable fix.

Source attribution and evidence boundaries: [PROVENANCE.md](PROVENANCE.md).
