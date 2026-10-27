# Additional prepublication review: branches, conversations, and build evidence

Date: 2026-10-27. This is **not** permission to make the repository Public or publish firmware.

## Scope directly checked using authenticated GitHub read access

- **13 new-repository branch tips** were enumerated. Their recursive tree results were all marked `truncated=false`. Across these tips, there were **537 path-to-blob references**, **49 unique path names**, and **82 unique Git blob SHA identities**.
- Each of the 82 unique blob contents was retrieved for targeted secret patterns. There were no matches for the inspected high-confidence private-key headers, GitHub-style tokens, private host network endpoints, host-specific absolute directories, or credential-assignment strings. The detector checks selected patterns only; it does not prove absence of all hidden or encoded data.
- **12 pull request** descriptions, **3 ordinary issue** descriptions, the available PR/Issue discussion timelines, and their corresponding fields were inspected. There were **0 PR discussion comments and 0 issue comments**, and no matches under those same high-confidence patterns.
- Earlier file-level checks established **27/27 cataloged source/test/build file blob identities** against the clean main tree. The source rights status remains PENDING for every entry.
- The GitHub Actions workflows in the new repository did not produce a hosted CI PASS. New-repository private self-hosted build jobs remained queued pending runner assignment. These are execution blockers rather than evidence that all tests pass.

## Actual source-equivalent ARM64 build result

A distinct **Private** archive branch was used only to exercise a retained, already-connected self-hosted runner, without changing the archived main branch.

- Run: [40443738043](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40443738043), conclusion **SUCCESS**.
- Trusted source identities were checked against the clean new repository before compilation:
  - RFC #1 Git blob: `3fc960a3ea7e5580fae46a463d95e619e8a0ecdf`
  - RFC #2 Git blob: `5514a6868ae03acca08c49a4b92c42da88c4ce5a`
- A pinned upstream Linux v6.18 source was used to compile ARM64 `mtk_eth_soc.o` for unchanged upstream baseline, RFC #1 alone, and RFC #1 + RFC #2. All three object builds and the static RFC validation passed. Log completion marker: `CLEAN_EQUIVALENT_UPSTREAM_ARM64_RFC_BUILD_PASS`.
- This is a **source-equivalent Ethernet object build on the v2 Private runner**, not a new-repo Actions PASS, full MT6990 Linux kernel build, OpenWrt rootfs, 5G NR, signed image or proven device cold boot.

Separate source-only follow-on jobs:

- [Generic Linux ARM64 Image smoke build](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40444627122) was started on the same Private isolated workflow branch; it is generic upstream Linux, **not** SBAT6 bootable firmware. The result must be confirmed independently.
- [Mirror of clean-repository synthetic tests](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40445484403) was submitted using 19 explicitly blob-pinned clean-source files on another Private test branch; no keys, private runtime or OEM images included. Its final test result must also be independently confirmed.

## Scope limitations that remain security gates

- Branch-tip trees are not a complete audit of every intermediate/deleted Git object or unreachable Git object.
- GitHub API discussion checks do not inspect private vendor disclosure materials, downloaded external ZIPs, all Actions logs, issue edits, fork copies, web caches or unpublished proprietary SDK input.
- No final independent contributor-rights or legal signoff has been conducted for the 27 candidate source files.
- GitHub branch/ruleset and Actions runner security settings on the new Private repository could not be inspected with administrative authority. A read of Private rulesets returned a plan/public-visibility restriction, and branch protection read was denied by integration permission.
- The home-runner workflow is guarded by **Private + trusted-main-push** and must be separately disabled or isolated before publication. Existing queued runs should also be examined before changing visibility.

**Disposition:** New clean repository and permanent v1/v2/research archives stay Private. Public **source-only** release could be reconsidered after complete all-history/code-rights/governance/disclosure verification. A **flashable firmware** release requires additional security and operational proof.
