# Public AP-first development: non-blocking handoff (2026-11-03)

Scope: [#74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74), kernel [#20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), userspace [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21), integration [#4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4). This file coordinates source-only, hardware-free work; it is **not** approval for signing, flashing, private assets, radio firmware, release or device experiments.

## Anti-stall rule: WAIT_OWNER is not a terminal state

At the start of each autonomous or human development session:
1. Inspect main HEAD, all open PRs, the latest Actions status, and #74/#20/#21/#4. Record exact commit IDs and links. Never infer a CI PASS merely from an older run on a different SHA.
2. If an active writer owns a file set, **do not edit, rebase, merge, or push to their branch**. Make progress in a disjoint workstream instead, or prepare a reproducible failure report with precise next commands.
3. If no material code, build, or test evidence has appeared for **three hours**, write one concise blocker receipt in the owning issue: last successful SHA, active PR, blocked dependency, CI failure (if any), and ONE concrete action. Avoid repeated identical comments; check the most recent receipt first.
4. Pick the highest-priority *unowned* item below. Prefer actual compilation and functional verification to generic guards, dashboards or more policy documents. New changes go to a fresh narrow branch/PR with hosted CI and explicit PASS/NOT_TESTED evidence.
5. When all relevant changes are owned, report `BLOCKED_BY_ACTIVE_WRITER` with the exact ownership boundary and request the writer's status. Do not manufacture commits to make the activity graph look busy.
6. Merge only after the PR's current head has passing required CI and review/rights gates. No merge of pending/failed CI.

## Immediate parallel work queue

| Order | Owner issue | Material deliverable | Independence / exit evidence |
| --- | --- | --- | --- |
| 1 | #20 | NETSYS/TOPCK/reset/genpd/PCS1 components compiled into the **same pinned native ARM64 kernel Image** with DTB and reproducible hashes | Work outside PR #118's package/rootfs files; CI builds actual objects; report missing sources precisely |
| 2 | #21 | Distinct SBAT6 OpenWrt device profile, coherent kernel/DTB/rootfs staging manifest and native build | Keep separate from PR #118's `wpad-basic-mbedtls` packaging; include package/ABI checks |
| 3 | #4 | Offline end-to-end assembly smoke tying exact Image/DTB/initramfs/rootfs identities together | Non-installable output only, no hardware boot or signed image claim |
| 4 | #21/#4 | After PR #118 passes and merges: confirm native staged wpad and safe no-autostart defaults | Run on *merged head*; no duplicate implementation |

## PR #118 boundary

[PR #118](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/118) owns the native `wpad-basic-mbedtls` package and unprovisioned service startup gates. Do not close, replace, force-update or merge it just because it is old. Determine current CI status on its latest SHA, identify first failing job if any, and hand that evidence to its writer. If it is PASS and ready, request review; if not, keep its isolated scope.

## Standard evidence receipt

- UTC/JST inspection time; main SHA; active PR #/HEAD SHA and actual current-head CI status.
- What **changed during this run**: commit/PR/CI URL and reproducible artifact identity, or `NO_CHANGE`.
- Blocker and owner; next smallest independent engineering action and linked issue.
- Explicitly distinguish historical 6.18.44 hardware AP success, current native QEMU/userland checks, and unverified Air6 cold boot / wireless operation.

**Completion goal:** a coherent reproducible *unsigned, noninstallable* SBAT6-specific Image + DTB + userspace/AP build, then separately authorized hardware acceptance. A green documentation or source-only check is not hardware evidence.
