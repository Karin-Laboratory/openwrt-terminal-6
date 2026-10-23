# MT6990 OpenWrt subtarget: implementation and limits

Updated: 2026-10-23

## Implemented source

`integration/mt6990-target.patch` adds `mediatek/mt6990` to the pinned OpenWrt MediaTek target. It selects the generic AArch64 userspace/toolchain, Linux `Image`, `CONFIG_ARCH_MEDIATEK`, `CONFIG_DTC`, and `CONFIG_NET_MEDIATEK_SOC`. The MT7531 observation is represented by the upstream MT7530 DSA family and MediaTek tagger configuration for compile coverage; it does not prove SBAT6D switch wiring or runtime operation. The MediaTek Ethernet cleanup/requeue RFC patches are added after OpenWrt's existing 6.18 patch series.

The subtarget has no CPU microarchitecture selection, board profile, device-specific package set, production DTS, image recipe, partition layout, signing or installation output. `files-6.18` now carries an identity-only research DTS/DTSI, and `image/mt6990.mk` remains empty so Kconfig does not advertise an unsupported device. The generic compile profile explicitly disables unverified SoC-specific clock, pinctrl, external-interrupt and watchdog drivers; CI rejects accidental selection of these families. This is a source-build target for generic kernel and package/rootfs work, not a bootable MT6990 port.

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
toolchain_dir="$(find staging_dir -maxdepth 1 -type d -name 'toolchain-aarch64_generic_*' -print -quit)"
toolchain_bin="$PWD/$toolchain_dir/bin"
make -C "$tree" ARCH=arm64 \
  CC="$toolchain_bin/aarch64-openwrt-linux-musl-gcc" \
  CROSS_COMPILE="$toolchain_bin/aarch64-openwrt-linux-musl-" \
  HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++ \
  HOSTLD=/usr/bin/ld HOSTAS=/usr/bin/as olddefconfig
make -j2 target/linux/compile V=s
# The target build workflow separately compiles the research-only DTB:
make -C "$tree" ARCH=arm64 mediatek/mt6990-sbat6d-incomplete.dtb
```

Then `package/compile`, `package/install`, and `target/install` can be tested on the same configuration. No image from this target is a valid SBAT6D boot artifact. Do not interpret a generic ARM64 build as MT6990 SoC or board support.

## Device Tree status

PR #1 splits the reported MT6990 root compatible into `board/mt6990-identity-only.dtsi`; `board/sbat6d-incomplete.dts` contains the research model string. The matching OpenWrt `files-6.18` sources are registered in Linux's MediaTek DTS Makefile, with no OpenWrt device profile. Linux 6.18.55 Kbuild generated this 181-byte identity-only DTB locally (SHA-256 `b6038335526da786e9fd83fd4f3d567b8aeff56fb755e37bbf50f3af78f35685`). It omits memory, CPUs, interrupt controller, clocks, resets, power domains, storage and board devices.

The [upstream Linux 6.18.55 MediaTek root binding](https://github.com/gregkh/linux/blob/v6.18.55/Documentation/devicetree/bindings/arm/mediatek.yaml) has no `mediatek,mt6990` entry; the repository has no verified board-specific compatible. `CHECK_DTBS=y DT_SCHEMA_FILES=mediatek.yaml` was attempted, but Kbuild stopped before DT validation because local `dt-doc-validate` is unavailable. Thus `dtbs_check` is **not passed**. Syntax and DTB generation do not establish binding compliance or bootability. Measured MAC1/SGMII1 observations remain isolated in the disabled overlay until their complete dependencies are resolved from a same-instance FDT.

## Evidence and blockers

- OpenWrt's existing `filogic` subtarget explicitly describes Filogic 8x0 / MT798x and sets Cortex-A53; those values were not reused.
- The upstream Linux/OpenWrt trees inspected for this work do not provide an MT6990 SoC DTS/clock/reset/power-domain implementation.
- The generic target can build code for ARM64 and compile the generic MediaTek Ethernet driver, but that does not provide MT6990 clocks, pin control, storage, PCIe, Wi-Fi, modem or startup support.
- A full device DTS and `dtbs_check` remain blocked on verified, redistributable same-device dependency information and suitable upstream bindings/drivers.
- No SBAT6D or LG6851F image definition is included. No device was connected or modified.

## Local build evidence (2026-10-23)

Using the pinned OpenWrt source above and the experimental `mt6990` subtarget:

- `make -j2 toolchain/install V=s`: PASS; AArch64 generic musl toolchain installed.
- Linux `target/linux/compile`: PASS with OpenWrt kernel 6.18.55 after resolving new Kconfig symbols through `make kernel_oldconfig`; unverified SoC-specific options were answered `n` and retained as explicit disables.
- `.config` confirms `CONFIG_ARCH_MEDIATEK=y`, `CONFIG_NET_MEDIATEK_SOC=y`, `CONFIG_NET_DSA=y`, `CONFIG_NET_DSA_MT7530=y`, `CONFIG_NET_DSA_MT7530_MDIO=y`, and `CONFIG_NET_DSA_TAG_MTK=y`. SoC-specific clock, pinctrl, external-interrupt and watchdog drivers remain disabled because MT6990 implementations were not verified.
- ARM64 `Image` SHA-256: `d47b3fb6e2b46f3d7a945aa138798cd186c5eb183236ec775f3c08b079492f83`.
- `drivers/net/ethernet/mediatek/mtk_eth_soc.o` SHA-256: `41318e85d298a924698342a746158a35a5b7a89244c8bae61cba3ebe377a47c8`.
- `make -j2 package/compile V=s`: PASS (77 package index entries produced).
- `make -j2 package/install V=s`: PASS.
- `make -j2 target/install V=s`: PASS; generic rootfs staging produced a 2,759,404-byte squashfs at `build_dir/target-aarch64_generic_musl/linux-mediatek_mt6990/root.squashfs` and a 3,468,211-byte tarball at `bin/targets/mediatek/mt6990/openwrt-mediatek-mt6990-default-rootfs.tar.gz`. Their SHA-256 values are `cc1f1b60776991d448c406905924603c19d7b2933b31479afcfdab3a69d51f29` and `7e3ec8ea1292d9c4c10303b2532f5555d813f34b11dacb3e8fba0080e8d003a2` respectively.
- Linux Kbuild DTB generation for the unbootable identity-only research DTS: PASS locally; source registration and both DTS files were staged in a temporary copy of the prepared kernel tree. DTB SHA-256: `b6038335526da786e9fd83fd4f3d567b8aeff56fb755e37bbf50f3af78f35685`.
- OpenWrt outer patch and nested DTB-registration patch: `git apply --check` and application PASS against the pinned OpenWrt baseline and the Linux 6.18.55 MediaTek Makefile. The hosted CI for the new integration is pending.
- `dtbs_check`: NOT PASSED / blocked as described above; no binding success is claimed.
- No SBAT6D device image, boot image, or flashable artifact was generated; `image/mt6990.mk` defines no device profiles.

## Hosted CI evidence

- GitHub Actions run [39943757295](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39943757295): PASS on source commit `019da51c79bc5859ab1980b0d1bda0911c5d984e`.
- The run completed the generic AArch64 toolchain, new Kconfig normalization, Linux 6.18.55 kernel and MediaTek Ethernet object compile, package compile/install, and generic rootfs staging.
- The heavy workflow has a `pull_request` path filter for `integration/mt6990-target.patch`, plus `workflow_dispatch`. Because this Draft PR already changes that path relative to `main`, GitHub may still start the heavy job on documentation-only follow-up commits until the PR is merged.
- This remains compile evidence only. It does not establish that the generated generic artifacts boot MT6990 or SBAT6D.

This proves a generic ARM64 Linux and Ethernet-driver compile against the selected OpenWrt source. It does not prove MT6990 boot support, DTS validity, switch topology, or device operation. The generated kernel is experimental and must not be installed on SBAT6D.
