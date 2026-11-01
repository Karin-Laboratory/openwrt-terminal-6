# Technical status

Hardware research snapshot: 2026-10-27; public source/CI evidence updated: **2026-11-01**. This repository still does **not** provide an installable Air6 device firmware or a fully validated OpenWrt device target.

| Component | Observed in historical experiments | Available here | Remaining work |
| --- | --- | --- | --- |
| A/B boot control | Development-device slot selection reported | Strict, read-only, synthetic metadata observation model (no device IO) | LK retry/fallback conditions and independently proven rescue |
| Signed boot | Experimental accepted boot images reported | No signing code, SDK copy, test keys or signed payloads | Review input formats, legal sources and safe packaging privately |
| Linux kernel | Linux 6.18.44 boot observed | Pinned Linux v6.18 ARM64 Image actually compiled with upstream Ethernet/DSA and selected source-pinned MT6990 SGMII PHY/IFRAO clock; Air6 DTB candidates in the same Kbuild tree; QEMU boots the **generic** virt guest | MT6990 NETSYS/TOPCK/genpd/reset/PCS1, complete Air6-kernel/DTB/rights review and hardware boot |
| OpenWrt userspace | procd and shell operated on development device | Real source-pinned musl-static AArch64 BusyBox, procd, ubus/ubusd, UCI, netifd and embedded initramfs; native AF_UNIX IPC/UCI smoke; **QEMU virt procd→netifd service registration and same PID stable for 1 s PASS** | Official full OpenWrt packages/base-files, QEMU network/bridge acceptance, Air6 boot, SSH provisioning, wpad/AP and complete SBAT6 target |
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

## Actual public ARM64 build and QEMU runtime evidence (2026-11-01)

<!-- source-catalog-inventory: inputs=72; pending=72 -->

The source catalog currently has **72 inputs**, all with **rights_review=pending**. The counts are checked against the machine-readable catalog by the host tests; passing those checks does **not** imply rights approval. See [rights review](RIGHTS-REVIEW-20261030.md).

| Run / PR | Observed PASS marker or step | What it establishes | Explicitly **not** proven |
| --- | --- | --- | --- |
| [#41244846282](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41244846282), [PR #101](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/101) | `SBAT6_NATIVE_MUSL_UBUSD_UBUS_LOCAL_IPC_RUNTIME_PASS` and local UCI smoke | Native static musl AF_UNIX ubus/ubusd IPC and UCI read of the loopback-only config | Boot-time netifd or real Ethernet |
| [#41257538056](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41257538056), [PR #103](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/103) | `SBAT6_PROCD_NETIFD_REGISTERED` | Real Linux Image in isolated QEMU virt reached procd-mediated netifd service registration | Stable netifd process or Air6 board boot |
| [#41262230348](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41262230348), [PR #104](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/104) | `SBAT6_QEMU_VIRT_PROCD_NETIFD_PROCESS_RUNTIME_PASS` | Same guest PID remained present after one second | ubus interface state or network traffic |
| [#41266444777](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41266444777), [PR #105](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/105) | `MT6990_SGMII_PLL_ERROR_PROPAGATION_KBUILD_PASS` | Source-pinned PLL write error handling compiled in real ARM64 Image | Real PHY error injection or Ethernet link |
| [#41273574138](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41273574138), [PR #106](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/106) | `SBAT6_QEMU_VIRT_PROCD_NETIFD_BRIDGE_RUNTIME_PASS` | **PR candidate**, completed successful ARM64+QEMU CI: netifd constructed isolated empty Linux bridge `br-sbat6` | PR not yet merged at this snapshot; no NIC, L2 traffic, Air6 or AP |
| [#41273611920](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41273611920), [PR #107](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/107) | `PUBLIC_MT6990_REAL_OPENWRT_DEFCONFIG_PASS` | **PR candidate**, real pinned upstream OpenWrt `make defconfig` selected native MT6990 source-only subtarget | PR not yet merged at this snapshot; no Device profile, packages, rootfs, kernel/AP or installation |

The QEMU test uses a generic ARM64 `virt` machine with no external NIC and no device passthrough. Its success must never be presented as Air6 hardware Ethernet/Wi-Fi or an installable firmware. Source/rights review remains pending. Development gates: [#74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74), [#20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21). Next: [OpenWrt buildroot and isolated AP test gates](AP-FIRST-NEXT-GATES-20261101.md) and [first-boot SSH security](AP-FIRST-SSH-PROVISIONING.md).

## Historical public source-only CI checkpoint (2026-10-30)

- [Hosted PR run #40984659074](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40984659074) and [main push run #40984791183](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40984791183) both completed SUCCESS with recorded steps: Python/synthetic tests, FE C checks both with/without `-DNDEBUG`, Ethernet RFC preflight, disabled SGMII and Air6 DTS syntax/roundtrip, feeds lock, source catalog, workflow policy and reachable-history scanner. This resolves the original no-step hosted-CI execution failure ([Issue #3](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/3)).
- The earlier clean-repository trusted-runner runs [#40442794789](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40442794789) and [#40443522118](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40443522118) are **cancelled**, not compilation PASS. GitHub Actions currently reports zero queued and zero in-progress runs at this checkpoint.
- These host-only checks do **not** constitute independent license review, vendor disclosure review, audit of all Actions logs/comments/settings, a complete MT6990 kernel/OpenWrt target build, modem runtime, DT binding verification or safe firmware installation. Continue [publication/security Issue #2](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/2) and implementation Issues [#4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4), [#20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21) and [#22](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22).
