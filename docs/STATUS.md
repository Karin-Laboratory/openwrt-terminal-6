# Technical status

Hardware research snapshot: 2026-10-27; public source/CI follow-up: 2026-10-30. This project does not currently provide an installable device firmware or a supported OpenWrt target.

| Component | Observed in historical experiments | Available here | Remaining work |
| --- | --- | --- | --- |
| A/B boot control | Development-device slot selection reported | Strict, read-only, synthetic metadata observation model (no device IO) | LK retry/fallback conditions and independently proven rescue |
| Signed boot | Experimental accepted boot images reported | No signing code, SDK copy, test keys or signed payloads | Review input formats, legal sources and safe packaging privately |
| Linux kernel | Linux 6.18.44 boot observed | Source-only Ethernet RFC and Stage 10 delta | Fully rights-cleared independently reproduced kernel, SoC DTS and driver dependencies |
| OpenWrt userspace | procd and shell operated on development device | Fixed four-text-file donor inspection, feed locks, and source-equivalent ARM64 BusyBox smoke PASS; no vendor binary checkout | Distinct SBAT6 build profile, pinned feeds, rootfs, packages and full clean build |
| Ethernet | Device link and packet tests succeeded | Upstream-review RFCs, Stage10 DMA delta, independently authored but incomplete base Air6 DTS and separate opt-in NETSYS/SGMII1/PHY candidate; pinned DTC round-trip PASS | Full matching-kernel build, binding `dtbs_check`, device cold-boot/PHY/DSA link verification and safe recovery |
| Wi-Fi 2.4 / 5 GHz | Connectivity reported | No radio firmware, EEPROM or calibration | Open-source/redistribution audit, persistent configuration |
| Wi-Fi 6 GHz | Access point started | No radio binaries | Client association, EHT/MLO and regulatory validation |
| Modem LTE IPv4 | **Stage 9B/10 OpenWrt packet traffic succeeded** | Stage10 source-only patch, deterministic transformation and offline tests | Full public-build recovery and legally redistributable runtime |
| Modem 5G NR | **Not verified** | No NR implementation claim | Registration and end-to-end NR packet evidence |
| Modem IPv6 | **Not verified** | No IPv6 claim | IPv6 PDU/session and traffic tests |

## Observed LTE packet success

On 2026-10-25, Stage 9B restored the initial DMA configuration manually and achieved bidirectional IPv4 data. Stage 10 preserved MED-related DMA registers around the initial Ethernet reset, then recorded ping, DNS resolution and HTTPS 200 with TLS certificate verification without using the manual restoration in that replay.

These experiments used a retained, modified MT6990 vendor-capable Linux/OpenWrt source baseline and separate private runtime/provisioning assets. Historical file SHA-256 comparisons link the modified source and actually booted image. The current public repository is **not** a standalone reproduction of that firmware and does not include the original confidential binaries, full kernel configuration or signing inputs.

The Stage10 change depends on precise MMIO assumptions from that research baseline; it must not be treated as a generic MediaTek kernel patch or safe deployable fix.

Source attribution and evidence boundaries: [PROVENANCE.md](PROVENANCE.md).

## Public source-only CI checkpoint (2026-10-30)

- [Hosted PR run #40984659074](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40984659074) and [main push run #40984791183](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40984791183) both completed SUCCESS with recorded steps: Python/synthetic tests, FE C checks both with/without `-DNDEBUG`, Ethernet RFC preflight, disabled SGMII and Air6 DTS syntax/roundtrip, feeds lock, source catalog, workflow policy and reachable-history scanner. This resolves the original no-step hosted-CI execution failure ([Issue #3](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/3)).
- The earlier clean-repository trusted-runner runs [#40442794789](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40442794789) and [#40443522118](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40443522118) are **cancelled**, not compilation PASS. GitHub Actions currently reports zero queued and zero in-progress runs at this checkpoint.
- These host-only checks do **not** constitute independent license review, vendor disclosure review, audit of all Actions logs/comments/settings, a complete MT6990 kernel/OpenWrt target build, modem runtime, DT binding verification or safe firmware installation. Continue [publication/security Issue #2](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/2) and implementation Issues [#4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4), [#20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21) and [#22](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22).
