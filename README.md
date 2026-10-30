# OpenWrt for SoftBank Air Terminal 6

Public, source-only community research toward OpenWrt support for the SoftBank Air Terminal 6 (SBAT6 series / MediaTek MT6990).

> **Source-only experimental project. No downloadable or supported firmware, installation instructions, signature keys, or confirmed safe recovery procedure are provided. Do not flash images based on this repository.**

## Demonstrated development milestones

- A development device booted Linux 6.18.44 with OpenWrt userspace; Ethernet and 2.4/5 GHz networking were reported functional in limited tests. A 6 GHz access point started, but external client association, Wi-Fi 7 EHT/MLO and stable reboot persistence were not established.
- **LTE IPv4 data traffic on OpenWrt succeeded:** Stage 9B required manual DMA restoration; Stage 10 retained MED DMA state through the initial Ethernet reset and subsequently passed ping, DNS and certificate-validated HTTPS.
- **Not demonstrated:** 5G NR data, modem IPv6, unattended cold-boot repeatability, a clean third-party firmware rebuild, safe A/B fallback, or production security.

The [NETSYS + SGMII1 opt-in Ethernet candidate](docs/NETSYS-SGMII1-BOOT-CANDIDATE.md) adds real PHY/PCS/clock/provider and DSA integration source without enabling the default board image. It remains **source-only and untested on hardware**.

Read the [board DTS reconstruction evidence](board/DTS-RECONSTRUCTION-20261029.md) for the independently observed Air6 topology, missing dependencies and full-DTS completion criteria. An [independently authored board DTS candidate](board/mt6990-air-terminal-6.dts) is available, but a **complete, boot-verified board DTS remains unavailable**.

Read the [engineering integration status](docs/ENGINEERING-STATUS-20261027.md), [technical status](docs/STATUS.md), [source provenance](docs/PROVENANCE.md) and [publication gates](docs/RELEASE-GATES.md). The original research and binary evidence are retained separately in non-public archives; they are not imported into this Git history.

## Start here

This is a **public development repository**, not a firmware download page. Browse [technical status](docs/STATUS.md) to distinguish what worked on a research unit from what is reproducible from this tree. Review [roadmap](docs/ROADMAP.md) for next engineering milestones and [build contract](docs/BUILD-CONTRACT.md) for offline checks. Report bugs or propose small source improvements via Issues and PRs, following [CONTRIBUTING.md](CONTRIBUTING.md).

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
