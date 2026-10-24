# Release readiness / 公開準備状況

## Verified MT6990 generic rootfs build (2026-10-24)

**PASS: GitHub Actions [#40091561598](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40091561598), source commit [af6cb6ddc67b335c7c7da024eedae54f5dfb51b0](https://github.com/Karin-Laboratory/openwrt-terminal-6/commit/af6cb6ddc67b335c7c7da024eedae54f5dfb51b0).** Workflow `Experimental MT6990 generic target build` reports successful pinned OpenWrt checkout, patch application, AArch64 toolchain, Linux 6.18.55 kernel/MediaTek Ethernet compile, research DTB/schema stage and package/rootfs staging. Reported squashfs SHA-256: `10a3ed9981dd6ed9f078a9a9c6feb40ba5f0f20e436dd27dc7778c812af850a6`; this checksum has not been independently recalculated from a downloaded artifact in this documentation update.

**Scope:** experimental **generic** MT6990 target and rootfs staging only. This is **not** a verified SBAT6D bootable image, installable partition image, board-complete DTS, runtime network bring-up, recoverable flashing procedure, or independent clean-room rebuild. RAM/reserved-memory and clock/reset/power-domain providers remain unresolved; disabled peripheral nodes remain research placeholders. These constraints override outdated statements further below that the generic OpenWrt build has never passed.


Updated: 2026-10-23. This is an **evidence-based source-publication status**, not an installation approval.

## What can be shared now

- Original project documentation and sanitized *reported* hardware findings, subject to per-file attribution and review.
- Synthetic, **disabled** SGMII1 Device Tree examples and offline verification tooling.
- Public Linux v6.18 MediaTek Ethernet RFC1/RFC2 patches with verified ARM64 driver-object compilation, **not evidence of a complete kernel build**.
- A contribution process for source patches and redacted logs.

## Explicitly not ready

- No supported installation image, verified flashing procedure, guaranteed A/B fallback or recovery instructions.
- No complete OpenWrt source/patch manifest with an independently passing end-to-end build.
- No permission established to redistribute the private archive, OEM SDK-derived driver tables, extracted firmware, calibration data, certificates or signing keys.
- No independently verified persistent Ethernet and Wi-Fi bring-up on unrelated devices; 5G modem remains unsupported.

## Current evidence and blockers

| Gate | Evidence | Status / action |
| --- | --- | --- |
| Documentation-only publication | README, BUILDING, INSTALL, RECOVERY, SECURITY, LICENSES | Prepared, subject to audit |
| Current and reachable-history screening | `scripts/check-publication.py`, `scripts/check-publication-history.py` | Publication safety gate PASS at `cc938e99` (run #39841379271). Heuristics do not replace manual history/path/license review |
| Public safety gate | `.github/workflows/publication-gate.yml` | **PASS** on commit `cc938e99ea569e45ca6f8e400b568800b3e03a2a`, push run [#39841379271](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39841379271), static-audit SUCCESS, 2026-10-22 UTC |
| Offline DTS fixture tests | `.github/workflows/public-source-checks.yml` | Separate workflow PASS not yet verified; publication-gate DTS and phandle steps PASS in run #39841379271 |
| Public donor PHY object | `.github/workflows/mt6990-phy-compile-probe.yml` | Experimental probe; no verified PASS; not the privately adapted Test25 driver |
| Code provenance | `docs/SOURCE-AUDIT.md`, `LICENSES/README.md` | Hold unreviewed imports, especially SDK-derived code |
| Reproducible Linux v6.18 Ethernet object | [Public verification](docs/PUBLIC-SOURCE-VERIFICATION.md) | **PASS**: [three-state ARM64 build #39877158871](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158871); [sequential apply #39877158897](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158897) |
| Full upstream Linux v6.18 ARM64 Image with built-in MediaTek Ethernet | [run #39885153830](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39885153830) | **PASS** on commit `1d8949d` (47m45s); `CONFIG_NET_MEDIATEK_SOC=y`; Image SHA-256 `a99b89d680700e1cad4927d27238eaf0a9882b21968ac8bbb274a79b7aee6128`. Not an SBAT6D image |
| Complete OpenWrt image build | `BUILDING.md` | NOT PASSED |
| Installable image and recovery | `INSTALL.md`, `RECOVERY.md` | NOT PASSED |

## Release decision

**Public source RFC and reproduction instructions: available. Complete board port and installable binary: NO-GO.**
Do not label an Actions run PASS until its exact workflow, commit SHA and final job status have been checked. A green documentation check does not validate kernel boot, network operation or secure recovery.

Before a tagged documentation release: verify the final Actions run logs, manually review **all commits** for accidentally published material, record each imported file's origin/license, inspect public issue templates and confirm no private files appear in releases or artifacts. Do not rewrite published history without deliberate coordination.

日本語: **ソース研究資料の公開準備中、導入可能なファームの公開は不可**。CIの成功、履歴全体の権利・機密監査、第三者による再現性確認を混同しません。
