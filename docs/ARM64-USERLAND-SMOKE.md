# Isolated ARM64 BusyBox source compile smoke

**Research scope: one upstream userland executable built from public source; not an OpenWrt rootfs, Linux kernel, signed image or deployable SBAT6 firmware.**

## Reproducibility inputs

- Public [BusyBox](https://github.com/mirror/busybox) version **1.36.1** at exact commit `1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4` (tag `1_36_1`).
- Expected upstream `Makefile` Git blob `fa8cb761443388730372eaf260e7ca1a0235bc43`.
- Only independently authored [build script](../scripts/build-arm64-busybox-smoke.sh) and [security tests](../tests/test_busybox_source_smoke.py) are retained in this new repo. BusyBox upstream sources/binaries are **not** redistributed.
- Runner must have an already installed non-root AArch64 cross-compiler; e.g., `aarch64-openwrt-linux-musl-gcc`. No package installation is performed inside the test.
- Cross compilation is performed entirely in a temporary disposable directory, and the emitted ELF is examined without execution. A reported SHA-256 is a build-result identity, not an authenticated release signature.

## What success means

An ARM64 BusyBox ELF can be cross compiled from independently pinned source using the retained test compiler. This proves a small part of the userland toolchain path. It does **not** prove:
- the kernel/userspace ABI, package feed compatibility, netifd/procd, startup policy or actual root filesystem;
- board-specific DT/flash layout, a secure first-login policy, A/B rollback or signing rights;
- Ethernet cold boot, Wi-Fi 7 EHT/MLO, LTE reproduction or 5G NR support.

**Licensing:** BusyBox is GPL-2.0-only; a build-result hash does not permit distributing its binary or replace source/license obligation assessment. The independent smoke test script is inventoried with `rights_review=pending` until it has been assessed for general source publication.

For a real OpenWrt rootfs, separately freeze the OpenWrt revision, all [feeds](../config/feeds.lock), package config, SDK/toolchain versions, package download checksums, device rootfs contents and reproducible build outputs. The [public MT6990 donor](OPENWRT-DONOR-SOURCE.md) uses LG6851F-specific image generation that must not be copied into an SBAT6 install path.
