# OpenWrt integration workstream

This branch now carries an experimental `mediatek/mt6990` source-build target in `mt6990-target.patch`. It enables a generic AArch64 Linux build, the common MediaTek Ethernet driver, and upstream MT7530 DSA/tag support for compile coverage, and integrates the public cleanup/requeue patches into OpenWrt's 6.18 patch series. The DSA selection follows the observed MT7531 family but does not confirm board wiring or runtime support. It intentionally defines no board profile, Device Tree, boot image, flash layout or installable firmware.

The exact pinned OpenWrt base is `openwrt/openwrt` commit `a25fb079b1463cd5d7d69c6d9a1c28d873291ebb`; kernel preparation yields Linux 6.18.55. Do not silently apply the target patch to another OpenWrt revision or kernel patch set.

Local verification on 2026-10-23 completed the generic AArch64 toolchain, Linux 6.18.55 kernel build (including `mtk_eth_soc.o` with MT7530 DSA), package compile/install, and generic rootfs staging. This is generic compile evidence only. GitHub Actions for the updated Kconfig normalization and target build are still running; no SBAT6D image or bootability is claimed.

Remaining milestones: add licensed MT6990 clock/reset/power/PCIe/SoC support, complete an independently authored SBAT6D board DTS, produce a generic rootfs staging image without device packaging, then validate each subsystem separately. The LG6851F donor image definition must never be renamed to SBAT6D or flashed.

## Locate an OpenWrt prepared kernel tree

After a normal, **source-only** OpenWrt `target/linux/prepare` run, the unpacked kernel normally resides under `build_dir/target-*/linux-*/linux-*`. Confirm the selected kernel version before integration. The checker accepts the kernel tree, **not** the OpenWrt repository root:

```sh
python3 tools/check_openwrt_rfc_compat.py /path/to/openwrt/build_dir/target-.../linux-.../linux-...
```

Only if both Git blob IDs match the exact pinned upstream Linux v6.18 files should the RFC1→RFC2 sequence be tested. For other kernel versions, a separate rebase plus full driver compilation and source-review is required. No vendor image target, package definition, board DTS or firmware output is implied.

## Source metadata preflight

For a locally checked-out OpenWrt source tree, run `python3 tools/check_openwrt_kernel_version.py /path/to/openwrt/include/kernel-version.mk` first. This prints reported kernel versions but **never** confers direct patch applicability. Confirm the exact prepared kernel C/header blobs separately via `check_openwrt_rfc_compat.py`.
