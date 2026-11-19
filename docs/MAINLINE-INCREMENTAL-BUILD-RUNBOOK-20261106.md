# p25/p26 build acceleration: mandatory next-run procedure (2026-11-06)

Scope: PUBLIC mainline only. Applies to every 12-minute agent run that chooses p25/p26 work and every manual image build. This is an **execution checklist**, not permission to relax acceptance gates or to publish binaries.

## Measured baseline (successful GitHub-hosted native-package jobs)

| Run | Native package build duration | Result |
| --- | --- | --- |
| [41956490208](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41956490208) | 60m55s | SUCCESS |
| [41962616981](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41962616981) | 61m04s | SUCCESS |
| [41971766735](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/41971766735) | 90m50s | SUCCESS |

Observed mean ~70m56s. These timings measure the **native compile job**, not completed p25/p26 manufacture. The historical package/install → 128 MiB packer → independent verifier integration was tracked on [PR #127](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/127). For current work, inspect [PR #216](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/216) for image-manufacturing evidence and [PR #218](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/218) for cross-workspace receipt comparison. A same-workspace PASS does not establish independent reproducibility; verify current PR HEADs and actual retained bytes before reuse.

## Mandatory prebuild decision: reuse before rebuilding

1. Identify the exact current PR HEAD and any other active writers; identify last **successful** execution by run ID + exact HEAD SHA + toolchain/config/package/feed/DTB digests. Never combine success from unrelated runs or PR branches.
2. Classify the delta: (A) docs/tests only; (B) p26 userspace/package/config; (C) p25 Image/DTB/header; (D) kernel ABI or Wi-Fi modules; (E) unknown/unsafe. Emit `REBUILD_SCOPE`, `REUSE_PROOF`, and `CACHE_DECISION` in the PR log **before** invoking any long compile.
3. If A: host tests only. If B: reuse verified unchanged kernel/DTB and build only impacted packages, then p26 pack + independent verification; update p25 only if its CPIO/marker embeds the new p26 digest. If C: reuse verified p26 bytes; only rebuild impacted Image/DTB and p25 pack/readback. If D: check exact `Module.symvers`, compiler, .config and kernel release before allowing module reuse. If E or no verified bytes: full required layer build, explaining why reuse was unsafe.
4. Reuse only **exact, locally retained or owner-private independently verified bytes** with matching source/build provenance. A historical CI SUCCESS, logs, receipt, or SHA alone is **not a reusable binary**. Never synthesize success from an unavailable artifact.
5. Prefer same-run/same-workspace incremental build and immutable inputs. Retain trusted workspace outputs only where a controlled, authorized, local/self-hosted path exists and the source rights/security boundary permits it. **Do not upload firmware, rootfs, kernel image, signing data, or intermediate binaries to public Actions artifacts, shared caches, Releases, registries or third-party stores.** Public GitHub-hosted runners are ephemeral: do not claim cross-run binary reuse there.
6. For OpenWrt, attempt targeted `package/<path>/compile` and `package/install` only where the source/build graph and actual package dependency closure support it. Reuse toolchain and already-built packages from the **same live workspace**. Never skip necessary `target/linux/compile` solely because a previous run had a green result. Investigate failures at the first failing command, not by rerunning the full workflow.
7. Build real outputs as soon as prerequisites allow. For p26 select the current verified producer (check PR #216 and its exact HEAD rather than assuming the historical PR #127 branch is current) and run separate `verify_p26_independent.py`; preserve numeric UID/GID, symlinks, xattrs/capabilities and fail closed on mismatch. For p25 use a proven publicly lawful unsigned boot-v2 packer with full independent section and 32 MiB readback; never import private OEM blobs or signer.
8. Record `START_UTC`, `END_UTC`, `ELAPSED_SECONDS`, `REBUILD_SCOPE`, reused input SHA256, rebuilt output SHA256, build environment and status. Report either `IMAGE_ACCEPTED` with actual independently verified full-file SHA + exact size, or `BLOCKED` with the first concrete failure. Compare with the ~61–91 min historic baseline and report measured savings; do not invent them.

## Independent two-workspace acceptance (not satisfied by a same-job PASS)

1. Pin **one exact source commit** for both attempts. Record the clean workspace identifiers, toolchain/container digest, feed lock identities, build configuration, environment controls (including timestamps and locale), and all external input digests. Neither workspace may consume the other's build output or a shared binary cache.
2. In workspace A, manufacture unsigned P25 and P26 from source, verify each full file independently, and retain a local/private evidence receipt containing the exact source commit, sizes, SHA-256 values, and explicit unsigned status. Repeat the complete source build independently in workspace B; do not copy A's images or receipts into B as build inputs.
3. Verify **both** outputs independently in **each** workspace before comparison. Compare the two receipts with PR #218's comparator and separately compare the actual P25 and P26 full-file SHA-256 digests. Receipt equality alone is not proof of independent execution or artifact retention.
4. Accept reproducibility only when source and input identities match, both complete independent builds and readbacks pass, P25 is exactly 33,554,432 bytes, P26 is exactly 134,217,728 bytes, both remain unsigned, and each pair's full-file hashes match across A and B. On any mismatch, retain safe diagnostic metadata privately and report the first divergent layer rather than declaring PASS.
5. Do not publish firmware binaries or sensitive build paths in public CI artifacts, caches, releases, or logs. If isolated independent workspaces or retained verified bytes are unavailable, report `BLOCKED_INDEPENDENT_REPRODUCTION` and the missing prerequisite, even if same-workspace CI succeeds.

## Next execution order

**First** inspect the latest PR #216 manufacturing evidence and CI at its exact HEAD, identify the first remaining blocker to independently reproducing both images in two separate workspaces, and run the existing PR #218 receipt comparator on actual independently manufactured outputs. Do not mistake a receipt-only comparison or a same-workspace repeat for an independent build. **In parallel without file collision**, inspect existing p25 Image/DTB/boot-v2 provenance and assemble the unsigned 32 MiB p25 from licensable source. Optimization must not delay either real image and is not a new feature milestone.

The cron **schedule, trigger count, task assignment and priority** do not change. This document is read by the policy's mandatory task selection steps on each future public-mainline cycle. A policy instruction cannot force a future agent or runtime to run; compliance is auditable through the required PR receipt fields.
