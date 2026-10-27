# Trusted self-hosted source build boundary

This repository is being prepared for public **source** review. The dedicated [trusted self-hosted builder](../.github/workflows/trusted-selfhost-build.yml) performs source-only ARM64 compilation on **trusted main push**, never on pull-request events.

## What this job is allowed to do

- Checkout **this repo main** using a pinned `actions/checkout` commit with `persist-credentials: false` and read-only `GITHUB_TOKEN`.
- Check source-catalog byte identities, strictly scan locally fetched Git history, evaluate workflow policy, and execute hardware-free Python/C regression tests.
- Download **official upstream Linux v6.18 source** from torvalds/linux; reject it unless the full tag target commit and the MediaTek Ethernet C/header blob identities equal their pinned reference values.
- Cross-compile the Linux MediaTek Ethernet object in a temporary disposable directory, for baseline, RFC 0001 and RFC 0001+0002. Record resulting object SHA-256 in the Actions job summary, not a redistributable image.

## Explicit prohibitions

- No `pull_request`, `pull_request_target`, `workflow_run` or external fork execution on the self-hosted job.
- No firmware signing, bootloader commands, `sysupgrade`, partition writes, SSH to devices, SDK/private runtime sourcing, secrets, credential material, artifact upload or public release actions.
- No `sudo` or automatic system dependency installation. A missing toolchain causes a clear failure; do not silently grant the runner privilege or copy host credentials.
- No user/home storage paths, device identifiers or live measurements embedded in tracked workflow YAML.

The standalone workflow is **byte-pinned** in `tools/security/check_workflows.py`; modifying it without updating the vetted identity fails CI policy. This is a guard against accidental changes, **not** a substitute for GitHub branch protection and runner isolation. To reduce the impact of malicious code in trusted-main commits, the runner should use a disposable VM/container without signing secrets, home-network routes, or persistent SSH credentials. Old successful runs on the v2 Private archive do not establish runner registration to this newly created repository.

## Execution conditions and evidence

The workflow is triggered only by a trusted commit to `main` changing its YAML or source/test inputs. It requests runner labels `self-hosted`, `linux`, `x64`, `sbat6-recovery`, consistent with the historical archived build workflow.

Run outcomes have three independent gates:

1. **Queue and assignment:** a self-hosted runner with matching labels must be authorized for this repository.
2. **Host tests and Linux object compilation:** the installed cross-compiler and known-good dependencies must be present and the tests must actually execute.
3. **Firmware reproducibility:** not provided. A successful kernel *object* build is not a full MT6990 kernel, OpenWrt rootfs, signed image or radio data implementation.

Keep the source repository Private until full rights and security checks pass. The trusted-main runner workflow may need to be disabled or migrated to a separately isolated build project before publishing the repository; merely restricting the event does not by itself make a long-lived self-hosted runner safe against trusted-main compromises.
