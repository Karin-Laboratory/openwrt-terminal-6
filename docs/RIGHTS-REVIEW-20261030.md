# Source rights and redistribution audit queue (2026-10-30)

**Issue #2, ongoing review. This document does not grant copyright, contributor authorization, secure disclosure clearance, or firmware redistribution permission.**

## Verified inventory facts

- `config/source-catalog.json` currently contains **44** Git-blob identified source/test/build entries, all carrying `rights_review=pending`. The catalog validator checks file identities, declared license/origin labels and allowed paths, **not** permission from copyright holders.
- The clean Public repository is already visible. GitHub-hosted CI has passed the source-only tests and reachable-history scanner, but this is narrower than complete publication/right-to-redistribute and sensitive artifact reviews.
- Full firmware, signing, vendor radio/EEPROM material, LK recovery implementation and installable images are **outside** the current supported source-only distribution.

## Inventory by declared origin/license (not legal conclusions)

| Declared origin / SPDX | Files | Example paths | Legal review state |
| --- | ---: | --- | --- |
| linux-v6.18-derived / GPL-2.0-only | 2 | `patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch`, `patches/rfc/0002-mediatek-serialize-reset-requeue.patch` | pending; retain evidence |
| modified-gpl-parent-derived / GPL-2.0-only | 2 | `patches/mt6990/0001-preserve-initial-med-dma.patch`, `patches/mt6990/0002-air6-avoid-sgmii-top-cycle.patch` | pending; retain evidence |
| research-transformer / GPL-2.0-only | 1 | `scripts/research/sba6d_stage10_clean_patch.py` | pending; retain evidence |
| independent-original / MIT | 36 | `tools/boot/slot_observation.py`, `tools/boot/ab_fallback_hypotheses.py` … | pending; retain evidence |
| research-board-overlay / GPL-2.0-only | 1 | `board/mt6990-air-terminal-6-sgmii1-experimental.dtso` | pending; retain evidence |
| independent-original / GPL-2.0-only | 2 | `board/mt6990-air-terminal-6.dts`, `board/mt6990-air-terminal-6-ethernet-test.dts` | pending; retain evidence |

The listed labels are claims to verify, not a substitute for signed contribution authorization or a copyright audit. Every new and modified code file must retain a catalog identity and a **pending** review status until independently cleared.

## Concrete review queue and acceptance evidence

| Priority | Class | Evidence to collect | Completion criterion |
| --- | --- | --- | --- |
| P0 | Linux v6.18-derived RFCs | Exact upstream commit/file, author/copyright attributions, patch diff; SPDX versus actual upstream license | Source text and obligations documented, no inherited signatures forged |
| P0 | Research-derived MT6990 kernel/PHY/Stage10 code | Precisely identify original parent and contributor rights, distinguish public licensed changes from restricted vendor SDK | Each redistributed line has an admissible source, attribution and independent approval |
| P0 | Board DTS and experimental overlay | Independently observed wiring records; upstream SoC DTSI license, no copied OEM FDT or third-party LG6851F board properties | Per-node provenance and compatible license established |
| P1 | Build and donor acquisition | Verify commit/blob pinning, exclude binary-bearing trees, no LG6851F image packaging | Legally sourced text-only inputs and complete audit trail |
| P1 | Independent host tests and tooling | Confirm actual project authorship and MIT notices; trace any embedded GPL-derived code | File-by-file rights review recorded, no blanket MIT claim |
| P1 | GitHub governance | Verify branch rules, security reporting, runner permissions, Actions logs/artifacts, Issue/PR discussions and past external distribution | Manual checks documented with dates and responsible reviewer; no sensitive details publicly dumped |

## Required reviewer record (for each file)

Record privately or in a rights-cleared PR: `path`, catalog Git blob, declared origin, original upstream URL and revision, copyright holder, SPDX obligations, contributor authorization evidence, redistributability decision, review date, reviewer and remaining questions. Only then change `rights_review` from `pending` to `approved`. Do not mass-approve entries based on labels or CI success.

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
