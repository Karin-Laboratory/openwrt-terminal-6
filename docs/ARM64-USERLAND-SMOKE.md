# Isolated ARM64 BusyBox source compile smoke

**Research scope: one upstream userland executable built from public source; not an OpenWrt rootfs, Linux kernel, signed image or deployable SBAT6 firmware.**

## Reproducibility inputs

- Public [BusyBox](https://github.com/mirror/busybox) version **1.36.1** at exact commit `1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4` (tag `1_36_1`).
- Expected upstream `Makefile` Git blob `fa8cb761443388730372eaf260e7ca1a0235bc43`.
- Only independently authored [build script](../scripts/build-arm64-busybox-smoke.sh) and [security tests](../tests/test_busybox_source_smoke.py) are retained in this new repo. BusyBox upstream sources/binaries are **not** redistributed.
- Runner must have an already installed non-root AArch64 cross-compiler; e.g., `aarch64-openwrt-linux-musl-gcc`. No package installation is performed inside the test.
- BusyBox 1.36.1's optional legacy `tc` applet needs old CBQ Linux UAPI definitions that the current cross-toolchain Linux headers no longer provide. To avoid modifying host headers or vendor/kernel sources, this intentionally limited smoke configuration disables **only** `CONFIG_TC`; it is not an OpenWrt package configuration.
- Cross compilation is performed entirely in a temporary disposable directory, and the emitted ELF is examined without execution. A reported SHA-256 is a build-result identity, not an authenticated release signature.

## What success means

An ARM64 BusyBox ELF can be cross compiled from independently pinned source using the retained test compiler. This proves a small part of the userland toolchain path. It does **not** prove:
- the kernel/userspace ABI, package feed compatibility, netifd/procd, startup policy or actual root filesystem;
- board-specific DT/flash layout, a secure first-login policy, A/B rollback or signing rights;
- Ethernet cold boot, Wi-Fi 7 EHT/MLO, LTE reproduction or 5G NR support.

**Licensing:** BusyBox is GPL-2.0-only; a build-result hash does not permit distributing its binary or replace source/license obligation assessment. The independent smoke test script is inventoried with `rights_review=pending` until it has been assessed for general source publication.

For a real OpenWrt rootfs, separately freeze the OpenWrt revision, all [feeds](../config/feeds.lock), package config, SDK/toolchain versions, package download checksums, device rootfs contents and reproducible build outputs. The [public MT6990 donor](OPENWRT-DONOR-SOURCE.md) uses LG6851F-specific image generation that must not be copied into an SBAT6 install path.

## Verified Private-runner execution (2026-10-27)

[Run #40498318443](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40498318443) completed **SUCCESS** on the already connected isolated archived-v2 runner, using exact source and test blobs byte-matched to this new repo. The completed log confirmed five static tests, the genuine BusyBox 1.36.1 AArch64 cross-compile, `BUSYBOX_ARM64_ELF_HEADER_PASS`, and `CLEAN_SOURCE_PINNED_ARM64_BUSYBOX_PASS`. The temporary ELF had **1,053,400 bytes** and SHA-256 `edac38e43eb54dbaa0ef95a213834d32379c71bcdfccb2b69230ecf91d391e87`. The runner discarded it without executing, installing, uploading or signing it.

The initial unmodified `defconfig` smoke failed compiling legacy BusyBox `networking/tc.c` against current Linux headers; disabling only `CONFIG_TC` resolved this one cross-build compatibility issue. This is an isolated smoke profile, not a tested OpenWrt BusyBox package configuration.

## Pinned native musl stage experiment (AP-first #74 / #21)

A separate **noninstallable** native AArch64 build job now exercises
[`scripts/build-arm64-musl-busybox-stage.sh`](../scripts/build-arm64-musl-busybox-stage.sh).
It obtains public musl 1.2.5 from `ifduyue/musl` at exact commit
`0784374d561435f7c787a555aeab8ede699ed298`, builds a temporary
musl toolchain wrapper without root privileges. It installs **Linux v6.18**
UAPI headers from exact upstream commit `7d0a66e4bb9081d75c82ec4957c50034cb0ea449`
into that temporary musl prefix, without using glibc host headers, then compiles the same
pinned BusyBox 1.36.1 with `CC=<temporary>/bin/musl-gcc` and
`CONFIG_STATIC=y`. The result is inspected as ELF64 AArch64 without
`PT_INTERP` and packaged into an ephemeral, deterministic tar.gz stage
with a `libc=musl-static` manifest. The original glibc-static path remains
available and distinct.

**Evidence gate:** claim `SBAT6_NATIVE_MUSL_STATIC_BUSYBOX_STAGE_PASS` only
after the hosted `arm64-musl-native` job actually completes successfully.
No binary is uploaded, installed, executed or distributed; the output is
deleted on job exit. The GitHub-hosted native musl wrapper is **not**
OpenWrt's pinned musl cross-toolchain or its package build infrastructure.
This stage still lacks a distinct SBAT6 OpenWrt target, procd, ubus, uci,
netifd, SSH, wpad, Wi-Fi firmware, package closure, ABI and hardware AP
acceptance. Musl and BusyBox source redistribution obligations and
rights reviews remain separate from a CI compile PASS.

**Next:** build a pinned OpenWrt musl toolchain/package closure in an
isolated SBAT6-specific profile, then generate a noninstallable rootfs
with procd/netifd before considering any boot or release step.

## Pinned OpenWrt libubox core build (AP-first #21, 2026-10-31)

The GitHub-hosted native ARM64 musl job now optionally compiles all 18
upstream `libubox` core C translation units from the exact public OpenWrt
commit `da2d205a5cf3e877c45a2eec488218cbaf452e7d` using the same
musl 1.2.5 compiler and Linux v6.18 UAPI headers as the BusyBox stage.
It archives real AArch64 objects to `libubox.a` and links a **non-executed**
static musl AArch64 event-loop smoke ELF. The job requires the explicit
`SBAT6_MUSL_LIBUBOX_CORE_OBJECTS_AND_STATIC_LINK_PASS` marker. Outputs are
temporary and never uploaded.

This is an **actual compiled dependency**, not a full OpenWrt package build.
The optional JSON-C/Lua frontends, ubus, procd, netifd, wpad, SBAT6 target
and rootfs remain missing. This compilation is not a device test or
redistribution-rights clearance; the source rights gate remains pending.

## Native musl ubusd daemon link (AP-first #21, 2026-10-31)

The opt-in hosted ARM64 job now fetches exact public **json-c 0.18** commit
`41a55cfcedb54d9c1874f2f0eb07b504091d7e37`, compiles static
`libjson-c.a` with the same temporary musl compiler, then compiles
`libubox/blobmsg_json.c` and all seven upstream `ubusd` core units
from the already pinned `openwrt/ubus` revision. It links the actual
`ubusd_main.c` into an ELF64 AArch64 static daemon, requiring
`SBAT6_MUSL_UBUSD_STATIC_DAEMON_LINK_PASS`. No host glibc/json-c
library is used. Artifacts are ephemeral, neither executed nor uploaded.

This proves a **daemon compile/link closure only** after the hosted job
succeeds. It does not prove the daemon starts, IPC/ACL correctness,
OpenWrt package compatibility, a procd/netifd rootfs, MT6990 kernel ABI,
AP boot, or redistribution rights. All upstream licenses and rights
remain subject to separate review; no installable firmware is produced.
