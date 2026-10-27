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
| Stage10 deterministic source transform | `scripts/research/sba6d_stage10_clean_patch.py` | original behavior unchanged; SPDX header prepended |
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

The new-repository pull-request-triggered run [40438279734](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40438279734) reported **failure**, but its job metadata contained **no executed steps**, and fetching the job log returned a not-found object. **Neither test success nor a source-code test failure can be concluded from this run.** Private hosted-runner usage limits are a plausible environmental cause, not an established diagnosis. A real host-test and all-ref scanner PASS is still required before Public approval.
