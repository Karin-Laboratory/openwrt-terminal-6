> **Historical record notice (2026-10-31):** This document describes migration and CI observations **as of 2026-10-27**. Phrases such as “Private”, “hosted CI blocked”, and “30” entries below are historical, not present-day status or repository visibility. For current CI/source scope use [STATUS](STATUS.md), [AP-first #74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74), and the machine-readable [catalog](../config/source-catalog.json). Do not use this migration narrative as the active inventory. See [external-audit triage](EXTERNAL-AUDIT-TRIAGE-20261031.md).

# Clean-history source migration audit

Date: 2026-10-27. Destination: the new Private repository at the canonical project URL.

## Migration method

- Initialized a **new, empty repository**; never cloned/merged/rebased the archived Git history into it.
- Individually fetched and screened the following **15** rights-review candidates; compared their old/new file contents after upload.
- Existing upstream-derived Linux patches preserve their GPL-2.0-only origin; independent host-only code carries the applicable MIT identifier. An added SPDX comment on some Python files is the only intentional change versus archived file content.
- Authored the README, security policy, release gates, technical status, sanitized LTE evidence, and hosted-only CI **from scratch**. They do not copy private raw logs.

## Imported and compared source

| Scope | Files | Integrity check |
| --- | --- | --- |
| GPL kernel source deltas | `patches/rfc/0001-*.patch`, `0002-*.patch`, `patches/mt6990/0001-*.patch` | byte-exact, same Git blob SHA |
| Stage10 deterministic source transform | `scripts/research/sba6d_stage10_clean_patch.py` | original behavior unchanged; SPDX identity added with executable shebang preserved |
| Stage10 fake MMIO and transform tests | `tests/test_sba6d_stage10_clean_patch.py`, `tests/test_stage10_mmio_model.py` | original behavior unchanged; SPDX header prepended |
| Independent FE recovery model | 4 files under `examples/fe-recovery/` | byte-exact |
| Synthetic modem lifecycle | `tools/modem/transport_model.py`, `tools/modem/test_transport_model.py` | byte-exact |
| Source and hash validators | `scripts/apply-public-rfc-series.sh`, `tools/check_mediatek_rfc_series.py`, `tools/modem/verify_stage10_provenance.py` | byte-exact or SPDX-only |

## Excluded intentionally

- Old archive Git history and all raw device/OEM/vendor binaries.
- Signing keys, example key files, boot partitions and signed firmware images.
- Retained Stage10 exact kernel.config (contains an environment-specific build input and developer boot policy); only a private-original SHA digest appears in the sanitized evidence JSON.
- Home runner identities and old workflows that reference private build paths, credentials, provisioned devices, system package installation or device flashing.
- Private device identifiers, SIM/NV/calibration, internal endpoints and unredacted logs.
- Confidentially coordinated vendor security details, exploit sequences and test-key evidence.

## Content review of initial public-candidate files

29 individually retrieved file contents were reviewed using redaction-oriented pattern screening of credential strings, signing key headers, IPv4 private endpoints, full internal paths and developer boot config. **No matches in that limited file set.**

This review does **NOT** claim a completed local all-ref CLI scan or authoritative assessment of GitHub PR/Issue discussions, Actions logs, branch protections, fork/old URL exposure, vendor security disclosure status or redistribution rights. The clean-repository history scan must execute successfully, and those other gates still need explicit evaluation.

## Milestones kept separate

- OpenWrt **LTE IPv4** Stage9B/10 is a verified historical experimental result with source/image SHA attribution.
- Full standalone public-source firmware build, 5G NR, IPv6, automatic A/B recovery and EHT/MLO are NOT verified.
- Public **source** visibility requires security/license/CI governance checks; public **firmware** distribution additionally requires safe credentials, signing provenance, recovery validation and radio/runtime redistribution clearance.

This manifest is intended to be a reproducible review inventory, not a security certificate or permission to change visibility.

## First clean-repository hosted CI observation

The new-repository pull-request-triggered runs [40438279734](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40438279734) and [40438430837](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40438430837) reported **failure**, but both job records contained **no executed steps**; the first job log fetch returned a not-found object. **Neither test success nor a source-code test failure can be concluded from this run.** Private hosted-runner usage limits are a plausible environmental cause, not an established diagnosis. A real host-test and all-ref scanner PASS is still required before Public approval.

## Subsequent security hardening (2026-10-27)

- History checker now scans each path/blob pair from every locally available reachable commit, including deleted paths, symbolic links, commit metadata and annotated tags; it rejects shallow history. New synthetic regression cases cover those failure modes.
- Source-only workflow policy checker blocks self-hosted runner declarations, unsafe privileged pull-request events, write-scoped GITHUB_TOKEN, secret expressions and mutable third-party Actions references. This complements, but does not replace, GitHub repository settings review.
- The Stage10 deterministic source transformer embeds kernel-oriented C code; its source license is conservatively marked GPL-2.0-only instead of treating that embedded code as exclusively MIT. The separate original host-only tests retain their own license status, subject to contributor rights verification.
- The source provenance check over new GitHub issue/PR bodies and accessible commit messages did not find the reviewed high-risk patterns. This was not a scan of every revision's tree, inaccessible CI logs or personal commit-author privacy settings.

**Hosted workflow status remains blocked before tests execute.** These source changes do not constitute a new full CI PASS or Public release approval.

## Additional offline board evidence selection

Three source/test files for a disabled-only SGMII1 Device Tree overlay and static checks were added in a later reviewed migration step. The factual board JSON was adapted to distinguish historical LTE IPv4 success from unverified NR and IPv6. The v1 Git history, extracted vendor device trees and live hardware logs remain excluded. Total cataloged source/test/build/overlay files is now 30, with individual rights review still pending.
