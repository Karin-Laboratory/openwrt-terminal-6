# Source rights and redistribution audit queue (2026-10-30)

> **Current engineering scope (2026-11-04):** The [p25/p26 mainline policy](MAINLINE-P25-P26-POLICY.md) permits implementation, proven backports, local tests and ephemeral unsigned image builds without finishing this entire 95-entry inventory. Each **publicly committed** source contribution still needs a defensible origin/license, and distributed binaries require component-specific compliance. Pending inventory status is **not a development stop-work gate**.


**Issue #2, ongoing review. This document does not grant copyright, contributor authorization, secure disclosure clearance, or firmware redistribution permission.**

## Verified inventory facts (catalog refreshed 2026-11-05)

- `config/source-catalog.json` currently contains **95** Git-blob identified source/test/build entries, all carrying `rights_review=pending`. The catalog validator checks file identities, declared license/origin labels and allowed paths, **not** permission from copyright holders.
- The clean Public repository is already visible. GitHub-hosted CI has passed the source-only tests and reachable-history scanner, but this is narrower than complete publication/right-to-redistribute and sensitive artifact reviews.
- **Public distribution remains source-only**; unsigned p25/p26 image construction in private or ephemeral CI is the current goal. Signed/installable releases, vendor radio/EEPROM materials, signing and device operations remain outside routine public distribution.

## Inventory by declared origin/license (not legal conclusions)

<!-- source-catalog-inventory: inputs=95; pending=95 -->

The summary is a **2026-11-05 source-catalog snapshot**. Changes to catalog entries must update this breakdown and pass the source-only inventory consistency test. Counts represent declared entries, not permission to redistribute.

| Declared origin / SPDX | Files | Example paths | Legal review state |
| --- | ---: | --- | --- |
| linux-v6.18-derived / GPL-2.0-only | 2 | `patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch` | pending; verify Linux upstream provenance |
| modified-gpl-parent-derived / GPL-2.0-only | 3 | `patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch`; GPL-derived PHY fixes | pending; check exact parent and licensing |
| research-transformer / GPL-2.0-only | 1 | `scripts/research/sba6d_stage10_clean_patch.py` | pending; distinguish transform from original |
| independent-original / MIT | 84 | `tools/boot/slot_observation.py`; source build/tests | pending; verify actual authorship |
| research-board-overlay / GPL-2.0-only | 1 | `board/mt6990-air-terminal-6-sgmii1-experimental.dtso` | pending; check wiring evidence |
| independent-original / GPL-2.0-only | 4 | `board/mt6990-air-terminal-6.dts`, ethernet test DTS | pending; verify authorship |
| **Total** | **95** | Catalog entries; additional `missing_dependencies` are not source files | **95 pending** |

The labels are not a copyright ruling. New/modified source retains a catalog identity and **pending** status until supported by evidence, but pending does not prevent development or isolated builds. Public backports carry a short PR origin URL/revision (or self-authored observation basis), license and any unresolved concerns.

## Concrete review queue and acceptance evidence

| Priority | Class | Evidence to collect | Completion criterion |
| --- | --- | --- | --- |
| P0 | Linux v6.18-derived RFCs | Exact upstream commit/file, author/copyright attributions, patch diff; SPDX versus actual upstream license | Source text and obligations documented, no inherited signatures forged |
| P0 | Research-derived MT6990 kernel/PHY/Stage10 code | Precisely identify original parent and contributor rights, distinguish public licensed changes from restricted vendor SDK | Each redistributed line has an admissible source, attribution and independent approval |
| P0 | Board DTS and experimental overlay | Independently observed wiring records; upstream SoC DTSI license, no copied OEM FDT or third-party LG6851F board properties | Per-node provenance and compatible license established |
| P1 | Build and donor acquisition | Verify commit/blob pinning, exclude binary-bearing trees, no LG6851F image packaging | Legally sourced text-only inputs and complete audit trail |
| P1 | Independent host tests and tooling | Confirm actual project authorship and MIT notices; trace any embedded GPL-derived code | File-by-file rights review recorded, no blanket MIT claim |
| P1 | GitHub governance | Verify branch rules, security reporting, runner permissions, Actions logs/artifacts, Issue/PR discussions and past external distribution | Manual checks documented with dates and responsible reviewer; no sensitive details publicly dumped |

## Minimal per-change provenance; distribution review separately

During normal development, a **one-line PR origin/revision/license note** is sufficient; do not mass-approve `rights_review` from labels or CI. Before distributing specific source or binaries, resolve significant third-party permission questions and satisfy applicable GPL source and notice duties. A fuller private record (rights holder, license, permission evidence, reviewer and date) is useful for **disputed or unclear components**, not a standing 73-file precondition to developing firmware.

## Hard boundaries for future implementation

1. All new upstream-relevant code remains reviewable in small PRs against a pinned matching source. No unlicensed SDK headers, decompiled board FDTs, modem/NV blobs, keys, identifiers or private device logs in public history.
2. Source-only pass = syntax/compile/tests only; `dtbs_check`, build reproducibility, actual hardware boot, fallback and permission to redistribute are independent gates.
3. If a source origin cannot be proven, record it as blocked and redesign independently or obtain consent. Do **not** erase attribution to force approval.
4. Confidential security concerns travel via a private disclosure channel, not public Issues/Actions log output.

## Related engineering tracks

- [Issue #20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20): rights-cleared MT6990/board DTS, Ethernet PHY/PCS/PLL, matching ARM64 compile and binding validation.
- [Issue #21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21): distinct noninstallable OpenWrt userspace build.
- [Issue #22](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22): legally sourced modem runtime and independently testable transport.
- [Issue #4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4): eventual integration; no release until device and rescue criteria are met.
