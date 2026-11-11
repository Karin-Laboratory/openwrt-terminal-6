# OpenWrt for SoftBank Air Terminal 6

Public-source community development for the SoftBank Air Terminal 6 (SBAT6 series / MediaTek MT6990), with unsigned p25/p26 engineering builds as the current goal.

> **2026-11-02 Alpha 3 RC1 Developer Preview:** [Read the Alpha 3 source and technical-status announcement](docs/ALPHA3-RC1-20261102.md). This shares research milestones and collaboration guidance, **not a publicly downloadable, installable or C-device-boot-verified RC1 firmware**. For testing interest, see [Discussions #50](https://github.com/Karin-Laboratory/openwrt-terminal-6/discussions/50).

> **Public distribution remains source-only today. Local and ephemeral unsigned p25/p26 builds are engineering work, not downloadable or supported firmware. No signing keys, install instructions, or confirmed safe recovery procedure are supplied. Do not flash images based on this repository.**

## Current mainline priority (2026-11-04)

**Build complete, redistributable unsigned p25 (boot_a) and p26 (rootfs_a) from auditable OpenWrt-compatible source inputs.** Reuse implementation and build knowledge from already boot-successful research builds wherever legally reusable; independently written code based on device observations and ordinary upstream GPL/MIT reuse are welcome. Focus this public mainline on backporting, source/licensing cleanup, and reproducible image construction, **not new feature exploration**. File-level review flags are not a prerequisite for implementing or testing; actual public binary distribution has its own compliance checks.

**Automated contributors / 12-minute runs:** read [the current mainline execution policy](docs/MAINLINE-P25-P26-POLICY.md) first. This supersedes older AP-first task ordering; signing and public flashable releases remain separate.

**Publication boundary:** public PRs contain shareable source only; public CI may compile images ephemerally but must not upload generated binaries to artifacts, caches, Releases or registries. Include one origin/revision/license line for each backport; the full pending inventory does not stop development. Modifying Wi-Fi/cellular operation can affect Japanese radio certification, carrier agreements and warranty; verify permissible use before RF transmission.

## Demonstrated development milestones

- A development device booted Linux 6.18.44 with OpenWrt userspace; Ethernet and 2.4/5 GHz networking were reported functional in limited tests. A 6 GHz access point started, but external client association, Wi-Fi 7 EHT/MLO and stable reboot persistence were not established.
- **LTE IPv4 data traffic on OpenWrt succeeded:** Stage 9B required manual DMA restoration; Stage 10 retained MED DMA state through the initial Ethernet reset and subsequently passed ping, DNS and certificate-validated HTTPS.
- **Not demonstrated:** 5G NR data, modem IPv6, unattended cold-boot repeatability, a clean third-party firmware rebuild, safe A/B fallback, or production security.

The [NETSYS + SGMII1 opt-in Ethernet candidate](docs/NETSYS-SGMII1-BOOT-CANDIDATE.md) adds real PHY/PCS/clock/provider and DSA integration source without enabling the default board image. It remains **source-only and untested on hardware**.

Read the [board DTS reconstruction evidence](board/DTS-RECONSTRUCTION-20261029.md) for the independently observed Air6 topology, missing dependencies and full-DTS completion criteria. An [independently authored board DTS candidate](board/mt6990-air-terminal-6.dts) is available, but a **complete, boot-verified board DTS remains unavailable**.

Read the [engineering integration status](docs/ENGINEERING-STATUS-20261027.md), [technical status](docs/STATUS.md), [source provenance](docs/PROVENANCE.md) and [publication gates](docs/RELEASE-GATES.md). The original research and binary evidence are retained separately in non-public archives; they are not imported into this Git history.

**Stock GNSS research (separate from OpenWrt):** A privately owned Air Terminal 6 running the stock OS produced a 3D fix and 4,609 navigation-message delivery events across two tests; SBAS/L1Sb and L1S reception remain **unverified**. See the [sanitized GNSS investigation (Japanese, English summary)](docs/GNSS-RESEARCH-20261112.ja.md). This does **not** establish GNSS support in the public OpenWrt build.

## Start here

This is a **public source development repository with unsigned image-build work underway**, not a firmware download page. Browse [technical status](docs/STATUS.md) to distinguish what worked on a research unit from what is reproducible from this tree. Review [roadmap](docs/ROADMAP.md) for next engineering milestones and [build contract](docs/BUILD-CONTRACT.md) for offline checks. Report bugs or propose small source improvements via Issues and PRs, following [CONTRIBUTING.md](CONTRIBUTING.md).

**What you can do today:** inspect the code, patches and the new [independently authored Air6 DTS source candidate](board/mt6990-air-terminal-6.dts), run host-side syntax tests, review provenance and discuss upstream integration. The DTS is **not** a complete or verified Air6 board definition; unvalidated hardware consumers are disabled. **What you cannot do from this repository:** build a complete supported SBAT6 firmware or safely flash a device.

## Where to look

| Your interest | Start with |
| --- | --- |
| What has been tested on hardware? | [Technical status](docs/STATUS.md) |
| What work is needed for upstream OpenWrt? | [Roadmap](docs/ROADMAP.md) and [engineering integration](docs/ENGINEERING-STATUS-20261027.md) |
| Can I reproduce a check without hardware? | [Source build contract](docs/BUILD-CONTRACT.md) and [tests](tests/) |
| Where did the source come from? | [Source provenance and license notes](docs/PROVENANCE.md) |
| How do I help? | [Contribution guide](CONTRIBUTING.md) |
| Is there a flashable release? | [Publication and firmware gates](docs/RELEASE-GATES.md) (no installable release) |

## Contents

- `patches/`: source-only RFCs and the experimental Stage 10 DMA preservation change. No generic kernel support or flashable artifacts implied.
- `scripts/` and `tests/`: hardware-free transformation and regression tests.
- `examples/`: independent host-side recovery state model.
- `tools/`: synthetic modem and A/B models, offline SHA-256 build-input identity checks (not signing), and conservative publication checks.

## Collaboration and security

This repository is public for source review. Per-file third-party rights checks and broader security reviews are ongoing; publication is not a claim that all release gates passed. Contributions must contain only materials contributors are authorized to share. Do not post firmware blobs, credential data, subscriber identities, radio calibration, private signing keys, exploit details, or device-specific raw logs.

See [security policy](SECURITY.md), [contribution guidelines](CONTRIBUTING.md) and [file-level licensing notes](docs/PROVENANCE.md). GPL-2.0 kernel-derived materials and MIT-licensed independent examples have separate license texts in [LICENSES](LICENSES/).

This is an independent community project, not an official SoftBank or OpenWrt release.
