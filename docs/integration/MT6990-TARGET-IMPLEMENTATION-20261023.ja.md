# MT6990 OpenWrt subtarget: implementation and limits

Updated: 2026-10-23

## Implemented source

`integration/mt6990-target.patch` adds `mediatek/mt6990` to the pinned OpenWrt MediaTek target. It selects the generic AArch64 userspace/toolchain, Linux `Image`, `CONFIG_ARCH_MEDIATEK`, `CONFIG_DTC`, and `CONFIG_NET_MEDIATEK_SOC`. The MT7531 observation is represented by the upstream MT7530 DSA family and MediaTek tagger configuration for compile coverage; it does not prove SBAT6D switch wiring or runtime operation. The MediaTek Ethernet cleanup/requeue RFC patches are added after OpenWrt's existing 6.18 patch series.

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
# The first Kconfig sync may need to resolve new upstream symbols using defaults.
tree="$(find build_dir -type d -path '*/linux-mediatek_mt6990/linux-6.18.55' -print -quit)"
toolchain_bin="$(find staging_dir -type d -path '*/toolchain-aarch64_generic_*/bin' -print -quit)"
PATH="$PWD/$toolchain_bin:$PATH" make -C "$tree" ARCH=arm64 \
  CROSS_COMPILE=aarch64-openwrt-linux-musl- \
  HOSTCC=gcc HOSTCXX=g++ HOSTLD=ld HOSTAS=as olddefconfig
make -j2 target/linux/compile V=s
```

Then `package/compile`, `package/install`, and `target/install` can be tested on the same configuration. No image from this target is a valid SBAT6D boot artifact. Do not interpret a generic ARM64 build as MT6990 SoC or board support.

## Device Tree status

PR #1 adds `board/sbat6d-incomplete.dts`, which contains only the reported MT6990 root compatibility and a model string. It omits memory, CPUs, interrupt controller, clocks, resets, power domains, storage, and board devices. `dtc` syntax success is not `dtbs_check` success and does not establish bootability. The measured MAC1/SGMII1 observations remain isolated in the existing disabled overlay until their complete dependencies are resolved from a same-instance FDT.

## Evidence and blockers

- OpenWrt's existing `filogic` subtarget explicitly describes Filogic 8x0 / MT798x and sets Cortex-A53; those values were not reused.
- The upstream Linux/OpenWrt trees inspected for this work do not provide an MT6990 SoC DTS/clock/reset/power-domain implementation.
- The generic target can build code for ARM64 and compile the generic MediaTek Ethernet driver, but that does not provide MT6990 clocks, pin control, storage, PCIe, Wi-Fi, modem or startup support.
- A full device DTS and `dtbs_check` remain blocked on verified, redistributable same-device dependency information and suitable upstream bindings/drivers.
- No SBAT6D or LG6851F image definition is included. No device was connected or modified.

## Local build evidence (2026-10-23)

Using the pinned OpenWrt source above and the experimental `mt6990` subtarget:

- `make -j2 toolchain/install V=s`: PASS; AArch64 generic musl toolchain installed.
- Linux `target/linux/compile`: PASS with OpenWrt kernel 6.18.55 after resolving new Kconfig defaults with `olddefconfig`.
- `.config` confirms `CONFIG_ARCH_MEDIATEK=y`, `CONFIG_NET_MEDIATEK_SOC=y`, `CONFIG_NET_DSA=y`, `CONFIG_NET_DSA_MT7530=y`, `CONFIG_NET_DSA_MT7530_MDIO=y`, and `CONFIG_NET_DSA_TAG_MTK=y`.
- ARM64 `Image` SHA-256: `88ee4f9d4478b1a55cfe50c30c4a9cfc886b9d8543e50efd8783a0cc0a157a9b`.
- `drivers/net/ethernet/mediatek/mtk_eth_soc.o` SHA-256: `699cc6dae14f72e6eb07009c6f20f606f5c4a91e7689cf39a52453fec7f610c4`.
- `make -j2 package/compile V=s`: PASS (77 package index entries produced).
- `make -j2 package/install V=s`: PASS.
- `make -j2 target/install V=s`: PASS; generic rootfs staging produced a 2.7 MiB squashfs and a 3.4 MiB tarball. The squashfs SHA-256 is `76d7e79f2bcc17356795820dc04ff477aae3e218cc922134212421d3e2ec9ef8`; the tarball SHA-256 is `f9e9ef2dd9351d117809509123b9fc97933ae4b847318d12cb1740da62830315`.
- No SBAT6D device image, boot image, or flashable artifact was generated; `image/mt6990.mk` defines no device profiles.

This proves a generic ARM64 Linux and Ethernet-driver compile against the selected OpenWrt source. It does not prove MT6990 boot support, DTS validity, switch topology, or device operation. The generated kernel is experimental and must not be installed on SBAT6D.
