# Trusted self-hosted source build boundary

This repository is now Public for **source** review. The dedicated [trusted self-hosted builder](../.github/workflows/trusted-selfhost-build.yml) performs source-only ARM64 compilation on **explicit maintainer workflow_dispatch on main while the repository is Private**, never on pull-request events or automatic main pushes. Its GitHub job-level condition checks the actual push event's `repository.private == true`; upon Public conversion the job must not execute. Already queued older runs must still be examined or cancelled before the transition.

## What this job is allowed to do

- Checkout **this repo main** using a pinned `actions/checkout` commit with `persist-credentials: false` and read-only `GITHUB_TOKEN`.
- Check source-catalog byte identities, strictly scan locally fetched Git history, evaluate workflow policy, and execute hardware-free Python/C regression tests.
- Download **official upstream Linux v6.18 source** from torvalds/linux; reject it unless the full tag target commit and the MediaTek Ethernet C/header blob identities equal their pinned reference values.
- Cross-compile the Linux MediaTek Ethernet object in a temporary disposable directory, for baseline, RFC 0001 and RFC 0001+0002. Record resulting object SHA-256 in the Actions job summary, not a redistributable image.

## Explicit prohibitions

- No `pull_request`, `pull_request_target`, `workflow_run` or external fork execution on the self-hosted job.
- No firmware signing, bootloader commands, `sysupgrade`, partition writes, SSH to devices, SDK/private runtime sourcing, secrets, credential material, artifact upload or public release actions.
- No `sudo` or automatic system dependency installation. The script tries installed `aarch64-linux-gnu-gcc` or `aarch64-openwrt-linux-musl-gcc`, and supports a runner-admin-supplied `SBAT6_TOOLCHAIN_BIN` location without committing private host paths. The OpenWrt toolchain may also need runner-local `STAGING_DIR`. A missing toolchain causes a clear failure; do not silently grant the runner privilege or copy host credentials.
- No user/home storage paths, device identifiers or live measurements embedded in tracked workflow YAML.

The standalone workflow is **byte-pinned** in `tools/security/check_workflows.py`; modifying it without updating the vetted identity fails CI policy. This is a guard against accidental changes, **not** a substitute for GitHub branch protection and runner isolation. To reduce the impact of malicious code in trusted-main commits, the runner should use a disposable VM/container without signing secrets, home-network routes, or persistent SSH credentials. Old successful runs on the v2 Private archive do not establish runner registration to this newly created repository. The first fresh-repo [run 40442794789](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40442794789) was queued at inspection; the job had not executed any steps. Use [this new repository's runner settings](https://github.com/Karin-Laboratory/openwrt-terminal-6/settings/actions/runners) to check assignment. Do not publish registration tokens or reassign an active legacy builder without an isolation review.

## Execution conditions and evidence

The workflow is triggered **only by an explicit maintainer manual dispatch against `main`**, not by pushes, scheduled events or outside PRs. This avoids indefinitely accumulating self-hosted jobs while the new repository has no authorized runner. It requests runner labels `self-hosted`, `linux`, `x64`, `sbat6-recovery`, consistent with the historical archived build workflow.

Run outcomes have three independent gates:

1. **Queue and assignment:** a self-hosted runner with matching labels must be authorized for this repository.
2. **Host tests and Linux object compilation:** the installed cross-compiler and known-good dependencies must be present and the tests must actually execute.
3. **Firmware reproducibility:** not provided. A successful kernel *object* build is not a full MT6990 kernel, OpenWrt rootfs, signed image or radio data implementation.

The source repository is already Public; retain the Private-only execution guard for trusted self-hosted jobs and continue security and rights reviews. The trusted-main runner workflow may need to be disabled or migrated to a separately isolated build project before publishing the repository; merely restricting the event does not by itself make a long-lived self-hosted runner safe against trusted-main compromises.

## Queued-run cutover warning (2026-10-27)

Prior auto-push workflow versions already created queued jobs before this trigger was changed. Historical queued runs do **not** disappear merely because the YAML now uses manual dispatch, and their payload may retain the earlier Private state. Inspect and cancel any legacy queued/running self-hosted jobs before assigning a new runner. The source repository has already become Public. GitHub integration did not provide permission to cancel those jobs directly. Do not publish while the queue is uncleared. The existing Private v2 runner continues source-equivalent testing using separate constrained branch workflows.
