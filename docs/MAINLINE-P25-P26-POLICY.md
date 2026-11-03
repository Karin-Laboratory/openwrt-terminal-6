# Mainline execution policy: redistributable unsigned p25 + p26 (2026-11-04)

This is the **current maintainer priority** for public mainline work and automated 12-minute development runs. It supersedes previous AP-first / source-only milestone *ordering*, not historical evidence or the separate public installation/release safety policy.

## Deliverables

1. **p25 / boot_a:** complete, unsigned, pre-signing boot image, built from lawfully redistributable inputs. Signing and any device-specific trust material remain outside this public repository.
2. **p26 / rootfs_a:** complete OpenWrt rootfs image, built from lawfully redistributable inputs.
3. **Reproducibility:** pinned source revisions, configuration, patches, packaging steps, component/license notices, and useful verification receipts sufficient for an independent build. Prefer actual image build and inspectable outputs over additional synthetic-only scaffolding.

These are engineering artifacts, **not an announcement of signed, safe-to-flash public firmware**. Do not claim boot success, legal clearance, or safe recovery without matching evidence.

## Implementation strategy

- **Backport first.** Inspect already successful private research builds and their recorded sources, hashes, configurations, UART/boot evidence and tests. Reuse the smallest working *implementation* from those successes, preserving attribution and licensing. Successful binaries are evidence, not automatically permissible public source inputs. For each published backport, write one PR origin line: upstream URL and revision (or independently observed/self-authored), license/SPDX and unresolved third-party concerns. A donor repo's visibility and AI-generated output alone do not prove rights.
- **No duplicate invention.** Before starting work, inspect current main, recent PRs and relevant private build records. Avoid rebuilding solved pieces or competing with another active lane.
- **Make the next artifact real.** Complete missing kernel/DTB/image packing for p25 and OpenWrt packages/rootfs for p26. Prioritize code, config, build scripts and tests that directly close image-build blockers. Use reviewable PRs and run the relevant tests; do not leave an actionable task as a research memo by default.
- **Feature freeze for mainline.** Do not independently pursue new 5G NR, MLO, 6 GHz or unrelated functionality. Take a proven, necessary change from experimental work only when needed for p25/p26 or existing boot/management functionality. Experimental lanes may continue separately.
- **Reverse engineering from observations is allowed.** UART/kernel logs, register or MMIO observations, hardware topology, behavior and interface experiments may inform independently written DTS, drivers, configurations and tools. Technical facts may be reused; do not copy restricted expressive source text, proprietary binaries, calibration or keys. Reverse engineering must respect applicable copyright, contractual and other legal restrictions.
- **Normal OpenWrt-style licensing.** Keep applicable copyright notices, SPDX, GPL source/offer and other package-license obligations, and verify any ambiguous proprietary component before redistribution. No bespoke legal dossier or per-file approval ritual is required *before normal code development, local build or testing*. The source-catalog `rights_review=pending` flags and `--public-source` / `--public-build` gates are audit/release checks, **not blockers for implementing, testing or privately building unsigned images**. Never label a component approved without supporting evidence.
- **Avoid overscoping.** Preserve working code; keep provenance notes concise and actionable. No mass refactors, unnecessary policy machinery or reimplementation for its own sake.

## Minimal publication boundary (not a development gate)

- Work, private builds, isolated public-CI compilation and tests may proceed **without completing the entire rights inventory**. Public commits and PRs already disclose source; before pushing a particular change, verify the rights of **that published material**. If uncertain, keep that material private and continue another unblocked task.
- Public CI may build unsigned p25/p26 and intermediate binaries **ephemerally**, but must not expose build outputs through Actions artifacts, Releases, shared caches or registry uploads. The static workflow checker blocks common mechanisms, not all possible disclosure paths.
- When distributing an image, provide required GPL corresponding source or valid offers, applicable notices and other component license materials. An unsigned image still triggers these obligations. This is a **distribution decision**, never a prerequisite to local implementation or testing.
- Do not publish signing keys, OEM signature-verification bypass or circumvention instructions, private signing infrastructure or device-unique data. The pre-signing p25 objective does not require these.
- For Japan-targeted images, retain appropriate JP regulatory settings and exclude radio calibration data. Software settings alone do not establish RF authorization; check certification, permitted use and applicable carrier/ownership/warranty conditions **before transmitting** from modified equipment. No new 6 GHz/NR work is a completion prerequisite.

## Next-work selection for automated development

At every existing scheduled trigger, if public mainline is the chosen workstream:
1. Read this policy and current main/PR/build evidence.
2. Choose the highest-impact **unblocked** p25 or p26 blocker, preferably independently editable.
3. Backport or implement, validate, and put the change on an existing appropriate PR/branch or open a focused PR. Report concrete files, test evidence and the next blocker.
4. If rights or provenance are uncertain, isolate the component and use a known licensed alternative or observation-based independent implementation. Continue other unblocked engineering; do not stop the whole project to finish the inventory.
5. Keep signing keys, proprietary dumps, device identifiers and install/flash procedures out of the public tree.

**Done means:** reproducible complete unsigned p25 and complete p26 produced from redistributable inputs, with build records and normal OSS license compliance. Independent rights/security review and general-public flashable release approval remain separate steps.
