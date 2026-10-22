# Release readiness / 公開準備状況

Updated: 2026-10-23. This is an **evidence-based source-publication status**, not an installation approval.

## What can be shared now

- Original project documentation and sanitized *reported* hardware findings, subject to per-file attribution and review.
- Synthetic, **disabled** SGMII1 Device Tree examples and offline verification tooling.
- Public CI definitions, which are attempts to validate these sources, **not evidence of a passing kernel build**.
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
| Reproducible build | `BUILDING.md` | NOT PASSED |
| Installable image and recovery | `INSTALL.md`, `RECOVERY.md` | NOT PASSED |

## Release decision

**Documentation/source research: candidate only. Installable binary: NO-GO.**
Do not label an Actions run PASS until its exact workflow, commit SHA and final job status have been checked. A green documentation check does not validate kernel boot, network operation or secure recovery.

Before a tagged documentation release: verify the final Actions run logs, manually review **all commits** for accidentally published material, record each imported file's origin/license, inspect public issue templates and confirm no private files appear in releases or artifacts. Do not rewrite published history without deliberate coordination.

日本語: **ソース研究資料の公開準備中、導入可能なファームの公開は不可**。CIの成功、履歴全体の権利・機密監査、第三者による再現性確認を混同しません。
