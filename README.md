# OpenWrt for SoftBank Air Terminal 6

Community-maintained experimental port of OpenWrt for the **SoftBank Air Terminal 6**.

> **Experimental / not ready for general installation.** A working developer unit is not proof that a third-party device can be flashed or recovered safely. Do not flash images without verifying exact hardware identity, partition layout, current boot slot, backup integrity and a tested recovery path.

[日本語](#日本語) · [Measured hardware findings](board/SBAT6D-HARDWARE-FINDINGS.md) · [Release readiness](RELEASE-READINESS.md) · [Build](BUILDING.md) · [Install safety](INSTALL.md) · [Recovery](RECOVERY.md) · [Verification](tests/README.md) · [Licensing](LICENSES/README.md) · [Contributing](CONTRIBUTING.md)

## Status

The following are **project development reports**, not independent third-party verification. A structured summary of observed Ethernet, FDT, Wi-Fi and modem evidence is now public in [SBAT6D hardware findings](board/SBAT6D-HARDWARE-FINDINGS.md). Raw logs, build inputs and independent reproducibility evidence have not yet been released here.

| Component | Reported state | Publication qualification |
| --- | --- | --- |
| Linux 6.18.44 boot | Observed on development unit | Exact log/commit/build recipe pending |
| OpenWrt userspace | Booted to shell | Image and repeatability validation pending |
| Wired Ethernet | Link/connectivity reported working | PHY/speed, interface mapping, testing pending |
| Wi-Fi (MT7990 / mt7996e) | 2.4/5 GHz WPA2 association and connectivity tested in RAM; 6 GHz WPA3-SAE AP enabled only | 6 GHz client, EHT/MLO, persistence, calibration provenance and firmware licensing pending |
| 5G modem | Not working yet | Driver/modem bring-up pending |
| Third-party installation | NOT VERIFIED | No public flash instructions yet |
| Recovery on arbitrary units | NOT VERIFIED | Do not assume A/B fallback works |

The strings `SBAT6A`, `SBA6D` and `SBAT6D` have appeared in research notes. Their relationship to official manufacturer model/revision identifiers is **not established**. Validate identifiers before applying patches or images.

## What this repository is for

1. Independently reproducible source-based builds.
2. Respect for original licenses and third-party rights.
3. Device safety, reversibility, and honest limitations.
4. Traceable evidence for each supported feature.
5. Minimal, reviewable patches suitable for upstream submission.

**There is currently no distributable installation image and no endorsed flash command here.** This repository starts with documentation and publication gates; source/patches will be added only after legal, provenance and technical review.

## Build and installation

Read [BUILDING.md](BUILDING.md) for the reproducibility contract and [INSTALL.md](INSTALL.md) before modifying any device. These documents intentionally do not claim that a complete reproducible build exists yet.

## Security and licensing

Original project-owned code is MIT-licensed where authorship/rights are confirmed ([LICENSE-MIT](LICENSE-MIT)); original documentation remains CC BY 4.0 ([LICENSE](LICENSE)). Third-party/Linux/OpenWrt/OEM-derived material is **not** relicensed. See [SECURITY.md](SECURITY.md), [LICENSES/README.md](LICENSES/README.md), and [PUBLICATION-CHECKLIST.md](PUBLICATION-CHECKLIST.md). Do not post device-specific identifiers, secrets, OEM images, signing materials or copyrighted vendor binaries in issues/PRs.

## 日本語

SoftBank Airターミナル6向けの**実験的なOpenWrt移植プロジェクト**です。開発機ではLinux 6.18.44、OpenWrtユーザーランド、有線LAN、2.4/5GHz無線LANの通信成功と6GHz AP起動の報告があります（EHT/MLOなどWi-Fi 7機能全体は未検証）が、第三者の機器への安全な導入と復旧は**未検証**です。5Gモデムも未対応です。

実機で観測したハードウェア構成とFDTの解析結果は[公開資料](board/SBAT6D-HARDWARE-FINDINGS.md)に整理しています。現時点では公開用の文書と審査基準を整備する段階であり、**配布可能なファームウェアイメージや推奨書込みコマンドはありません**。純正バイナリ、秘密鍵、署名素材は公開しません。再現手順は[BUILDING.md](BUILDING.md)、危険性は[INSTALL.md](INSTALL.md)と[RECOVERY.md](RECOVERY.md)を参照してください。

This is an independent community project, not an official SoftBank or OpenWrt release.
