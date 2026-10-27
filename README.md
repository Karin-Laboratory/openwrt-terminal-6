# OpenWrt for SoftBank Air Terminal 6

Independent research toward OpenWrt support for the SoftBank Air Terminal 6 (SBAT6 series / MediaTek MT6990).

> **Source-only experimental project. No downloadable or supported firmware, installation instructions, signature keys, or confirmed safe recovery procedure are provided. Do not flash images based on this repository.**

## Demonstrated development milestones

- A development device booted Linux 6.18.44 with OpenWrt userspace; Ethernet and 2.4/5 GHz networking were reported functional in limited tests. A 6 GHz access point started, but external client association, Wi-Fi 7 EHT/MLO and stable reboot persistence were not established.
- **LTE IPv4 data traffic on OpenWrt succeeded:** Stage 9B required manual DMA restoration; Stage 10 retained MED DMA state through the initial Ethernet reset and subsequently passed ping, DNS and certificate-validated HTTPS.
- **Not demonstrated:** 5G NR data, modem IPv6, unattended cold-boot repeatability, a clean third-party firmware rebuild, safe A/B fallback, or production security.

Read [technical status](docs/STATUS.md), [source provenance](docs/PROVENANCE.md) and [publication gates](docs/RELEASE-GATES.md). The original research and binary evidence are retained separately in non-public archives; they are not imported into this Git history.

## Contents

- `patches/`: source-only RFCs and the experimental Stage 10 DMA preservation change. No generic kernel support or flashable artifacts implied.
- `scripts/` and `tests/`: hardware-free transformation and regression tests.
- `examples/`: independent host-side recovery state model.
- `tools/`: synthetic modem and A/B models, offline SHA-256 build-input identity checks (not signing), and conservative publication checks.

## Collaboration and security

This repository will only include rights-cleared, individually reviewed, non-sensitive source and general research findings. Do not post firmware blobs, credential data, subscriber identities, radio calibration, private signing keys, exploit details, or device-specific raw logs.

See [security policy](SECURITY.md), [contribution guidelines](CONTRIBUTING.md) and [file-level licensing notes](docs/PROVENANCE.md). GPL-2.0 kernel-derived materials and MIT-licensed independent examples have separate license texts in [LICENSES](LICENSES/).

This is an independent community project, not an official SoftBank or OpenWrt release.
