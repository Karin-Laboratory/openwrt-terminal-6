# Mainline evidence and build-workflow discovery index (2026-11-05)

This **public, source-only locator** is the fast starting point for the current unsigned p25/p26 goal. It is not a production manifest, flash guide, public binary archive, signer index or claim of successful hardware boot from this repository. For active priorities, [read the current policy first](MAINLINE-P25-P26-POLICY.md).

## One entrypoint, three authorities (no copied histories)

- **Navigation and triage: this document, PR [#129](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/129).** Start here to locate work. Current manual [work ledger](WORK-LEDGER-20261105.json) tracks owners, blockers and return conditions; the [failure-mode dictionary](FAILURE-MODES-20261105.ja.md) maps errors to the minimal correction.
- **Historical runs and minimal replay: PR [#128](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/128).** The fixed [648-run snapshot](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/docs/p25-p26-reuse-workflow-audit-20261105/docs/evidence/WORKFLOW-RUNS-SNAPSHOT-20261105.json) and [Japanese replay guide](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/docs/p25-p26-reuse-workflow-audit-20261105/docs/MAINLINE-WORKFLOW-GOLDEN-REPLAY-20261105.ja.md) remain the **sole source** for that historical analysis; do not copy the data into PR #129.
- **Private originals and Alpha3 history: owner-controlled, access-restricted archive.** Its own separately maintained index is discoverable only with owner access; this public repository does not expose repository locators, raw evidence, owner-only binaries, private paths or security-sensitive content.

These are **separate, unmerged PR branches** at the time of writing; links to a branch do not establish the file is on main. Do not update automation/cron based on the dated ledger without reviewing newer runs.

## Find the right evidence without rebuilding solved work

| Question | Go to | Evidence and limitations |
| --- | --- | --- |
| **What are the exact deliverables and operating rules?** | [mainline p25/p26 policy](MAINLINE-P25-P26-POLICY.md), [build contract](BUILD-CONTRACT.md) | p25 boot_a unsigned 32 MiB; p26 rootfs_a 128 MiB from redistributable inputs, with independent receipts. Signing and deployment are distinct. |
| **What is public reproducibility status?** | [technical status](STATUS.md), [engineering integration](ENGINEERING-STATUS-20261027.md), [roadmap](ROADMAP.md) | Historic board and QEMU achievements must not be conflated with complete p25/p26 images. |
| **Where is the real p26 packer and its handoff?** | [Draft PR #127](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/127), [p26 manufacture document on PR branch](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/work/p26-rootfs-unsigned-packer-20261104/docs/P26-ROOTFS-MANUFACTURE.md), [packer source](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/work/p26-rootfs-unsigned-packer-20261104/tools/build/pack_p26_rootfs.py), [independent verifier candidate](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/work/p26-rootfs-unsigned-packer-20261104/tools/build/verify_p26_independent.py) | These are **unmerged Draft** PR files, not necessarily on main. Host/synthetic checks and native package compilation do not establish a real p26 image. |
| **Where is the source-built OpenWrt userspace/rootfs job?** | [native MT6990 build workflow](../.github/workflows/mt6990-native-subtarget.yml), [native subtarget design](MT6990-NATIVE-OPENWRT-SUBTARGET.md), [wpad/rootfs PR #118](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/118) | Require source checkout, package/install, manifest, archive and packer from the **same exact run/commit**; do not join successful checks from unrelated PR branches. |
| **How is the MT6990 board/kernel/DTB candidate tracked?** | [Air6 board DTS](../board/mt6990-air-terminal-6.dts), [DTS reconstruction](../board/DTS-RECONSTRUCTION-20261029.md), [NETSYS/SGMII1 candidate](NETSYS-SGMII1-BOOT-CANDIDATE.md), [build contract](BUILD-CONTRACT.md) | Hardware-observation-based source candidates and kernel/build checks are not a complete boot-v2 p25 or verified C-specific boot handoff. |
| **Where are source/license/readiness rules?** | [provenance](PROVENANCE.md), [release gates](RELEASE-GATES.md), [source catalog](../config/source-catalog.json) | Development gates and external binary distribution are separate. Public source must have rights and attribution; no private binary/secret is an acceptable input. |
| **Where is the public research status and contributor entry?** | [project README](../README.md), [contributing](../CONTRIBUTING.md) | Hardware successes in research are historical observations, not guaranteed by this public source tree. |

## Preserve distinct evidence classes

1. **DEVICE_OBSERVATION:** A specifically identified research device, date, UART/SSH/network record and physical output. The public README summarizes research milestones; raw, device-specific logs and image dumps are held **outside this repository**.
2. **OWNER_PRIVATE_BYTES_WITH_READBACK:** A previously produced image with SHA256 and a separate readback receipt. This is *comparative technical evidence* and may guide independently authored source; it does **not** become a licensable, redistributable public build input. The owner-private archive has its own access-restricted index.
3. **PUBLIC_NATIVE_BUILD:** Exact source commit + workflow SHA + job ID + package manifest + output. OpenWrt package compilation alone is not an installed final rootfs.
4. **PUBLIC_PACKED_IMAGE:** Locally/offline produced full 32 MiB or 128 MiB output, pinned ingredients, full-file digest, independent verifier and rights inventory. **No complete public p25/p26 is established by the cited Draft PR results as of this index date.**
5. **SOURCE_OR_SYNTHETIC_QA:** A test runner or synthetic SquashFS fixture. Never promote to hardware, image-manufacture or independent artifact PASS.

## Smallest next workflow, not a new full rewrite

| Track | Existing inputs to inspect first | Acceptance proof to add | Current result |
| --- | --- | --- | --- |
| **p26** | Source-pinned native OpenWrt package/install, PR #118 actual source checkout, PR #127 packer + verifier | One actual source-built rootfs and package manifest → real unsigned 128 MiB p26 → independent unsquashfs content/UID/GID/mode/symlink/xattr and zero-pad/full-SHA readback | **P26_BUILD=BLOCKED** pending actual merged-input artifact and independent evidence |
| **p25** | Existing Linux Image/DTS/boot-v2 design, current board/NETSYS backports and build contracts | One lawfully source-built unsigned 32 MiB p25, boot-v2 layout validation, fixed input SHA, second-process full readback | **P25_BUILD=BLOCKED**; do not treat kernel-only or DTB-only output as p25 |
| **No-change baseline** | Immutable existing receipt/source identities | Read-only comparison, skip rebuilding matching bytes; build only the changed layer | Historical success is a reuse guide, not proof of public artifact completion |

**For every 12-minute automated development run:** inspect current main, relevant open PR heads, successful *and failed* Actions for the same HEAD, source receipts and pre-existing successful implementations. Select one currently unblocked difference. Preserve existing producers, avoid duplicate pipelines, emit a concrete code/test change when possible, and record the new commit/run/SHA or one explicit blocking input. See [the authoritative priority/stop conditions](MAINLINE-P25-P26-POLICY.md).

## Link to an exact historical state

Pin the **commit SHA and workflow path that produced evidence** rather than a moving branch or a PR title. When a source file is only in an open PR, link both the PR and its branch file. A SUCCESS for a CI job means only what that job explicitly verified; an incomplete or skipped job cannot be counted as complete. Record missing/unverified receipts as missing, never fabricate a digest or source locator.

**Security boundary:** This index must remain suitable for public Git history. No OEM images, raw UART dumps, per-device calibration, PSK, restricted signing information, private runner paths, private artifacts, bypass instructions or device-unique identifiers. Do not publish firmware through ordinary CI artifacts, caches, releases or registries. No flash, slot or device operations are authorized by documentation changes.
