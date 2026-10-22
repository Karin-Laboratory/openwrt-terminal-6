# Porting source map / 移植元追跡

Inventory date: 2026-10-22. Branch names below were discovered in the **private** `Karin-Laboratory/SBAT6A-Offline-Archive` repository. A branch name is **not** evidence of working, redistributable code.

| Topic | Private branch | Source file review | Public migration |
| --- | --- | --- | --- |
| Core OpenWrt MT6990 port | `feat/openwrt-mt6990-port` | PENDING | NONE |
| Minimal Ethernet bring-up | `feat/mt6990-openwrt-ethernet-minimal` | PENDING | NONE |
| Ethernet MAC compile changes | `feat/sbat6d-ethernet-mac-compile-20261021` | PENDING | NONE |
| Persistent Ethernet test | `research/mt6990-test25-persistent-ethernet-build` | PENDING | NONE |
| LAN/Wi-Fi integration | `research/sbat6d-test25-lan-wifi-integration-20261022` | PENDING | NONE |
| Signed LAN/Wi-Fi image research | `research/sbat6d-test25-signed-lan-wifi-root` | PENDING | BLOCK binaries/keys |
| Wi-Fi live investigation | `research/sbat6d-wifi-live-20261022` | PENDING | NONE |
| 5G modem investigation | `research/sbat6d-modem-live-20261022` | PENDING | NONE |
| Modem readiness | `research/mt6990-modem618-readiness-20261021` | PENDING | NONE |

## Required extraction sequence

1. Obtain **read-only file listings** and branch head SHA for each source branch.
2. Identify only authored text code, build configuration, DTS/DTSI, compatible driver diffs, and scripts. Exclude private artifacts and original vendor dumps.
3. Record source commit, file path, author, license, provenance and a digest of every candidate in [SOURCE-AUDIT.md](SOURCE-AUDIT.md).
4. Cross-check copied/modified source against OpenWrt and Linux license obligations, including applicable GPL corresponding-source requirements.
5. Import reviewed changes as fresh, minimal commits. **Do not push, clone/mirror, or graft private repository history to the public repository.**
6. Add pinned upstream source, toolchain requirements and testable build recipe. Verify on a clean runner without any hidden private files or signing credentials.
7. Release installable images only after [publication gates](../PUBLICATION-CHECKLIST.md) pass.

## Current limitation

The GitHub connector exposed branch names and the private repository README but did not provide a reliable file tree listing for non-default branches in this review. No source code has therefore been copied, and no claims of source or license approval are made.

日本語: ブランチ名を公開向け移植候補として記録した段階です。ファイル単位で由来・権利・機密を監査するまで公開側へコピーしません。
