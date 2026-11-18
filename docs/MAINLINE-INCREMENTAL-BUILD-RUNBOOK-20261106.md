# p25/p26 build acceleration: mandatory next-run procedure (2026-11-06)

Scope: PUBLIC mainline only. Applies to every 12-minute agent run that chooses p25/p26 work and every manual image build. This is an **execution checklist**, not permission to relax acceptance gates or to publish binaries.

## Measured baseline (successful GitHub-hosted native-package jobs)

| Run | Native package build duration | Result |
| --- | --- | --- |
| [41956490208](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41956490208) | 60m55s | SUCCESS |
| [41962616981](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41962616981) | 61m04s | SUCCESS |
| [41971766735](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41971766735) | 90m50s | SUCCESS |

Observed mean ~70m56s. These timings measure the **native compile job**, not completed p25/p26 manufacture. The integration of package/install → 128 MiB packer → independent verifier is on [PR #127](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/127), and must only be marked complete after exact-head CI proof.

## Mandatory prebuild decision: reuse before rebuilding

1. Identify the exact current PR HEAD and any other active writers; identify last **successful** execution by run ID + exact HEAD SHA + toolchain/config/package/feed/DTB digests. Never combine success from unrelated runs or PR branches.
2. Classify the delta: (A) docs/tests only; (B) p26 userspace/package/config; (C) p25 Image/DTB/header; (D) kernel ABI or Wi-Fi modules; (E) unknown/unsafe. Emit `REBUILD_SCOPE`, `REUSE_PROOF`, and `CACHE_DECISION` in the PR log **before** invoking any long compile.
3. If A: host tests only. If B: reuse verified unchanged kernel/DTB and build only impacted packages, then p26 pack + independent verification; update p25 only if its CPIO/marker embeds the new p26 digest. If C: reuse verified p26 bytes; only rebuild impacted Image/DTB and p25 pack/readback. If D: check exact `Module.symvers`, compiler, .config and kernel release before allowing module reuse. If E or no verified bytes: full required layer build, explaining why reuse was unsafe.
4. Reuse only **exact, locally retained or owner-private independently verified bytes** with matching source/build provenance. A historical CI SUCCESS, logs, receipt, or SHA alone is **not a reusable binary**. Never synthesize success from an unavailable artifact.
5. Prefer same-run/same-workspace incremental build and immutable inputs. Retain trusted workspace outputs only where a controlled, authorized, local/self-hosted path exists and the source rights/security boundary permits it. **Do not upload firmware, rootfs, kernel image, signing data, or intermediate binaries to public Actions artifacts, shared caches, Releases, registries or third-party stores.** Public GitHub-hosted runners are ephemeral: do not claim cross-run binary reuse there.
6. For OpenWrt, attempt targeted `package/<path>/compile` and `package/install` only where the source/build graph and actual package dependency closure support it. Reuse toolchain and already-built packages from the **same live workspace**. Never skip necessary `target/linux/compile` solely because a previous run had a green result. Investigate failures at the first failing command, not by rerunning the full workflow.
7. Build real outputs as soon as prerequisites allow. For p26 use the PR #127 producer and separate `verify_p26_independent.py`; preserve numeric UID/GID, symlinks, xattrs/capabilities and fail closed on mismatch. For p25 use a proven publicly lawful unsigned boot-v2 packer with full independent section and 32 MiB readback; never import private OEM blobs or signer.
8. Record `START_UTC`, `END_UTC`, `ELAPSED_SECONDS`, `REBUILD_SCOPE`, reused input SHA256, rebuilt output SHA256, build environment and status. Report either `IMAGE_ACCEPTED` with actual independently verified full-file SHA + exact size, or `BLOCKED` with the first concrete failure. Compare with the ~61–91 min historic baseline and report measured savings; do not invent them.

## Next execution order (updated 2026-11-18)

**First** verify the exact current HEAD and CI of [PR #216](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/216), rather than assuming the historical 2026-11-17 successful run #43938848355 at `86d875801e420ce970fdb62e5942b490dec21252` applies to later commits. That run produced same-workspace unsigned P25 (33,554,432 bytes) and P26 (134,217,728 bytes) with independent readback; it did **not** prove independent cross-workspace reproducibility, and no reusable binary was retained. PR #127 is historical and is not the default next-work target.

**Next** run host tests for the receipt comparator on [PR #218](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/218). Then independently manufacture the complete pair in two clean, separate workspaces from identical pinned public source/config/toolchain inputs, recording each workspace's commit, dependency/toolchain digests, build timestamps, output sizes, full-file SHA-256, and independent readback. Compare both P25 and P26 identities and provenance without treating two copies of one receipt or the same underlying build as independent. See [PR #219](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/219) for the proposed execution checklist. A comparator PASS alone does not prove separate builds.

**Separately** classify the existing `check_publication.py --history` findings; do not disable the scanner, rewrite public history casually, or misreport the historical publication failure as a P25/P26 image-build failure. Avoid binary uploads, signing, flashing and general distribution. Optimization must not delay real independent image evidence.

The cron **schedule, trigger count, task assignment and priority** do not change. This document is read by the policy's mandatory task selection steps on each future public-mainline cycle. A policy instruction cannot force a future agent or runtime to run; compliance is auditable through the required PR receipt fields.
