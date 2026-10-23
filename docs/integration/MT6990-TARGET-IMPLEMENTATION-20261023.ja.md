# MT6990 OpenWrt subtarget: implementation and limits

Updated: 2026-10-23

## Implemented source

`integration/mt6990-target.patch` adds `mediatek/mt6990` to the pinned OpenWrt MediaTek target. It selects the generic AArch64 userspace/toolchain, Linux `Image`, `CONFIG_ARCH_MEDIATEK`, `CONFIG_DTC`, and `CONFIG_NET_MEDIATEK_SOC`. The MediaTek Ethernet cleanup/requeue RFC patches are added after OpenWrt's existing 6.18 patch series.

The subtarget intentionally has no CPU microarchitecture selection, board profile, device-specific package set, DTS, image recipe, partition layout, signing or installation output. Its `image/mt6990.mk` is empty by design so that Kconfig does not advertise an unsupported device. This is a source-build target for generic kernel and package/rootfs work, not a bootable MT6990 port.

## Reproduction

From the pinned upstream checkout `a25fb079b1463cd5d7d69c6d9a1c28d873291ebb`:

```sh
git apply /path/to/openwrt-terminal-6/integration/mt6990-target.patch
cat > .config <<'EOF'
CONFIG_TARGET_mediatek=y
CONFIG_TARGET_mediatek_mt6990=y
CONFIG_TARGET_ROOTFS_SQUASHFS=y
CONFIG_TARGET_ROOTFS_TARGZ=y
CONFIG_PACKAGE_base-files=y
CONFIG_PACKAGE_busybox=y
EOF
make defconfig
make target/linux/prepare V=s
make -j2 toolchain/install V=s
make -j2 target/linux/compile V=s
```

Then `package/compile`, `package/install`, and `target/install` can be tested on the same configuration. No image from this target is a valid SBAT6D boot artifact.

## Device Tree status

PR #1 adds `board/sbat6d-incomplete.dts`, which contains only the reported MT6990 root compatibility and a model string. It omits memory, CPUs, interrupt controller, clocks, resets, power domains, storage, and board devices. `dtc` syntax success is not `dtbs_check` success and does not establish bootability. The measured MAC1/SGMII1 observations remain isolated in the existing disabled overlay until their complete dependencies are resolved from a same-instance FDT.

## Evidence and blockers

- OpenWrt's existing `filogic` subtarget explicitly describes Filogic 8x0 / MT798x and sets Cortex-A53; those values were not reused.
- The upstream Linux/OpenWrt trees inspected for this work do not provide an MT6990 SoC DTS/clock/reset/power-domain implementation.
- The generic target can build code for ARM64 and compile the generic MediaTek Ethernet driver, but that does not provide MT6990 clocks, pin control, storage, PCIe, Wi-Fi, modem or startup support.
- A full device DTS and `dtbs_check` remain blocked on verified, redistributable same-device dependency information and suitable upstream bindings/drivers.
- No SBAT6D or LG6851F image definition is included. No device was connected or modified.
