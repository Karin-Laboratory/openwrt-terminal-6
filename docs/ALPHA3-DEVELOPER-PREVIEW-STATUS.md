# Alpha 3 Developer Preview: evidence and participation status / 技術状態と参加入口

**2026-11-03 · Source-only, experimental. Not a firmware release.**  
**2026年11月3日 · ソース公開による開発者向けプレビュー。一般向けファームウェア配布ではありません。**

This page is the **single Wave 2 status source of truth**. The original [RC1 announcement](ALPHA3-RC1-20261102.md) is a dated historical snapshot, not a continuously updated claim. Read the [contributor entry kit](ALPHA3-CONTRIBUTOR-START.md) to participate without hardware.

このページを第2波の**技術状態の正本**とします。既存の[RC1告知](ALPHA3-RC1-20261102.md)は当時の記録として残します。参加方法は[日英ガイド](ALPHA3-CONTRIBUTOR-START.md)へ。

## Four separate evidence levels / 実証の4階層

| Level | What exists / 確認できたこと | Does **not** prove / 証明しないこと |
| --- | --- | --- |
| **1 · Historical B hardware / 過去のB号機** | Linux **6.18.44** boot, Ethernet/SSH and 2.4/5 GHz Wi-Fi in limited development-device tests; Stage **9B/10 LTE IPv4** ping/DNS/validated HTTPS from a separately retained research stack | Reproducible build from public main; Alpha 3 C-unit success; 5G NR or IPv6 |
| **2 · Authentic C offline/private / 真正Cオフライン** | Owner-private source checks, Android boot image assembly/readback and signature-related research for RC1; C-specific FDT investigations | RC1 C-device Linux/procd successful boot; public redistributability or safe installation |
| **3 · Public QEMU/build / 公開ソースのQEMU・ビルド** | Generic ARM64 guest service tests; native MT6990 OpenWrt source/build progress; isolated QEMU procd PID1 and netifd/ubus/empty bridge milestones documented in existing PRs | Air6-specific hardware startup, PHY link, Wi-Fi association, installable p25/p26 |
| **4 · Authentic C hardware integration / 真正C実機統合** | **Not achieved for Alpha 3 RC1**: no confirmed Linux/procd handoff on authentic C | No claim that Level 1, 2 or 3 completes Level 4 |

**Never add these levels together into one end-to-end success.** A QEMU service result is not an MT6990 Ethernet device result. Successful offline signing/readback is not a C-device Linux boot.

**絶対に階層を合算しないこと。** QEMU成功と実機起動成功は別です。署名・readbackの成立も実機Linux起動を証明しません。

## Public engineering snapshot / 公開開発の現地点

The public repository currently contains/source-tracks Linux 6.18 kernel and Air6 DTS work, including historical **6.18.44** experiments and later **6.18.60** native-build development. Kernel versions refer to distinct experiments; a private 6.18.44 hardware run is not proof that a later public 6.18.60 build boots a C unit.

- **Native OpenWrt / QEMU:** [PR #115](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/115) merged source work on procd-embedded ARM64 QEMU; [PR #116](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/116) merged procd→netifd→bridge verification work. Generic ARM64 QEMU, not physical Air6. Verify individual linked Actions before claiming a particular current commit PASS.
- **wpad/WPA2/WPA3:** [Draft PR #118](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/118) integrates daemon build into an **unprovisioned** source-only rootfs. Draft ≠ an observed hardware AP or verified WPA3 client connection.
- **SGMII1/NETSYS/Ethernet:** [Issues #20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20) and [PR #120–#124](https://github.com/Karin-Laboratory/openwrt-terminal-6/pulls) cover opt-in DTS, provider/PHY/PLL, kernel/CI acceptance. These are open source validation steps, **not** a proved C-device Ethernet link.
- **Userspace and reproducible builds:** [Issues #21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21), [#4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4); the [build contract](BUILD-CONTRACT.md) documents source identity and remaining rights gates. Full public firmware reproduction is incomplete.
- **Historical AP and LTE:** Level 1 reported 2.4/5 GHz Wi-Fi and Stage10 LTE IPv4. A currently repeatable public-source-based device build has not been demonstrated. LTE source topic: [Issue #22](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22).
- **Not verified:** 5G NR data, modem IPv6, 6 GHz client association, Wi-Fi 7 EHT/MLO, EasyMesh, unattended C cold boot, C LAN/SSH/AP, safe universally documented recovery.

For changing engineering results and verified CI, follow the linked PRs and Actions; their **actual log and commit** outrank old descriptions. This page identifies scope, not a live CI monitor. Existing [technical status](STATUS.md), [roadmap](ROADMAP.md), [AP-first Issue #74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74), [rights/provenance](PROVENANCE.md) remain the detailed technical sources.

## What can people do now? / 今すぐ参加できること

| Track | Now / 今 | Hardware required? |
| --- | --- | --- |
| **A · Read-only reviewer** | Review public DTS, kernel patches, userspace, test/build recipes; submit specific observations | **No / 不要** |
| **B · QEMU / CI contributor** | Reproduce or improve documented hardware-free tests; add a focused source-only patch | **No / 不要** |
| **C · Hardware owner** | Discuss supported SoC observations and sanitized **existing** logs/configuration, with consent and provenance | **No new physical operation is requested** |

See [getting started / 参加ガイド](ALPHA3-CONTRIBUTOR-START.md); **you need neither root access nor a signed image to help**. No contributor should post or run flashing, signing, bypass, slot-change or rescue commands on the strength of this preview.

## Release gates / 公開段階

| Stage | Criteria / 条件 | Now |
| --- | --- | --- |
| **Developer Preview** | Public source, evidence categories, documentation and safe contribution routes | **Available now / 実施可能** |
| **Limited Hardware Alpha** | Independently verified device-specific image, actual boot and recovery evidence, rights/security assessment and **separate distribution approval** | **Not authorized / 未承認** |
| **Public Beta** | Repeatable physical cold boot, LAN, 2.4/5 GHz Wi-Fi, reboot, settings persistence and recovery; distribution rights and security reviewed | **Not ready / 未達** |

NR, IPv6, 6 GHz and EasyMesh **are not mandatory Alpha 3 gates**; they belong in subsequent feature tracks, potentially Alpha 4+. See [publication gates](RELEASE-GATES.md).

No flashable binary, no universal installation procedure, no private root method, no signing keys or secret runtime are included. C hardware first boot is **not verified**. Independent project; not an official SoftBank or OpenWrt release.
