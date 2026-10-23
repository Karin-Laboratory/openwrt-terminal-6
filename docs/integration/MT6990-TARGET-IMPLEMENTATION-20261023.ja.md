# MT6990 OpenWrt subtarget: implementation and limits

Updated: 2026-10-23

## Implemented source

`integration/mt6990-target.patch` adds `mediatek/mt6990` to the pinned OpenWrt MediaTek target. It selects the generic AArch64 userspace/toolchain, Linux `Image`, `CONFIG_ARCH_MEDIATEK`, `CONFIG_DTC`, and `CONFIG_NET_MEDIATEK_SOC`. The MT7531 observation is represented by the upstream MT7530 DSA family and MediaTek tagger configuration for compile coverage; it does not prove SBAT6D switch wiring or runtime operation. The MediaTek Ethernet cleanup/requeue RFC patches are added after OpenWrt's existing 6.18 patch series.

The subtarget has no CPU microarchitecture selection, board profile, device-specific package set, production DTS, image recipe, partition layout, signing or installation output. `files-6.18` now carries an independently authored partial SoC/board DTS: four observed Cortex-A55 CPU MPIDRs, PSCI SMC, GICv3 and architected timer. `image/mt6990.mk` remains empty so Kconfig does not advertise an unsupported device. The generic compile profile explicitly disables unverified SoC-specific clock, pinctrl, external-interrupt and watchdog drivers; CI rejects accidental selection of these families. This is a source-build target for generic kernel and package/rootfs work, not a bootable MT6990 port.

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
toolchain_bin="$PWD/$toolchain_dir/bin"
cc="$toolchain_bin/aarch64-openwrt-linux-musl-gcc"
cross="$toolchain_bin/aarch64-openwrt-linux-musl-"
make -C "$tree" ARCH=arm64 \
  CC="$toolchain_bin/aarch64-openwrt-linux-musl-gcc" \
  CROSS_COMPILE="$toolchain_bin/aarch64-openwrt-linux-musl-" \
  HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++ \
  HOSTLD=/usr/bin/ld HOSTAS=/usr/bin/as olddefconfig
make -j2 target/linux/compile KERNEL_CC="$cc" KERNEL_CROSS="$cross" V=s
# The target build workflow separately compiles the research-only DTB:
make -C "$tree" ARCH=arm64 mediatek/mt6990-sbat6d-incomplete.dtb
make -C "$tree" dt_binding_check \
  DT_SCHEMA_FILES=Documentation/devicetree/bindings/arm/mediatek.yaml
make -C "$tree" CHECK_DTBS=y \
  DT_SCHEMA_FILES=Documentation/devicetree/bindings/arm/mediatek.yaml \
  ARCH=arm64 mediatek/mt6990-sbat6d-incomplete.dtb
make package/compile KERNEL_CC="$cc" KERNEL_CROSS="$cross" V=s
make package/install KERNEL_CC="$cc" KERNEL_CROSS="$cross" V=s
make target/install KERNEL_CC="$cc" KERNEL_CROSS="$cross" V=s
```

The workflow also calls `dt-doc-validate` and direct `dt-validate` for the generated target DTB because the kernel Makefile treats schema diagnostics as non-fatal in its `CHECK_DTBS` recipe. The explicit validator step makes this target check fail closed. The package commands pass the same kernel compiler/cross prefix as the kernel build. No image from this target is a valid SBAT6D boot artifact. Do not interpret a generic ARM64 build as MT6990 SoC or board support.

## Device Tree status

PR #1 now defines `board/mt6990.dtsi` with the observed four Cortex-A55 MPIDRs, PSCI SMC conduit, GICv3 distributor/redistributor ranges and maintenance PPI, plus architected timer PPIs and recorded counter frequency. `board/sbat6d-incomplete.dts` provides the observed root compatible pair and an explicit research model. OpenWrt integration carries those sources and a Linux patch registering the DTB and adding the exact root compatible sequence to the MediaTek binding. No OpenWrt device profile or image recipe exists.

Linux 6.18.55 Kbuild generated the partial DTB (SHA-256 `6844e1ec2a9f5b27b5951e89f2bf12f1cde74efc11866208ee5dd1a8be254e2c`). `dt_binding_check`, `dt-doc-validate`, targeted `CHECK_DTBS=y` and isolated `dt-validate` passed. A whole-subtarget `dtbs_check` attempt emitted unrelated existing schema failures in other board DTBs and was stopped before completing the whole directory; it is not counted as a pass. The exact target tree passes validation, but this result does not establish bootability.

The same B-unit boot_b FDT contains conflicting root memory descriptions at base `0x80000000`; the DTS has no memory node. eMMC, PCIe and MAC/SGMII facts remain disabled because Linux 6.18.55 lacks verified MT6990 providers and complete clocks/resets/genpd/pinctrl/binding dependencies in this workstream. The raw FDT and unit-specific digest are not published.

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
- Linux 6.18.55 generated the partial, non-bootable research DTB. Targeted `dt_binding_check`, `dt-doc-validate` and `dt-validate`: PASS; whole-subtarget check is not claimed because other existing MediaTek DTBs emit unrelated errors. DTB SHA-256: `6844e1ec2a9f5b27b5951e89f2bf12f1cde74efc11866208ee5dd1a8be254e2c`.
- OpenWrt outer patch `git apply --check`: PASS against pinned baseline. Linux patch series contains both DTB registration and root-compatible binding update. Hosted CI for this revision remains pending.
- `dt_binding_check`, `dt-doc-validate`, and targeted DTB schema validation: PASS. Whole-subtarget validation: NOT PASS; the attempted run emitted unrelated upstream board/schema errors and was stopped before completion.
- No SBAT6D device image, boot image, or flashable artifact was generated; `image/mt6990.mk` defines no device profiles.

## Hosted CI evidence

- GitHub Actions run [39943757295](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39943757295): PASS on source commit `019da51c79bc5859ab1980b0d1bda0911c5d984e`.
- The run completed the generic AArch64 toolchain, new Kconfig normalization, Linux 6.18.55 kernel and MediaTek Ethernet object compile, package compile/install, and generic rootfs staging.
- The heavy workflow has a `pull_request` path filter for `integration/mt6990-target.patch`, plus `workflow_dispatch`. Because this Draft PR already changes that path relative to `main`, GitHub may still start the heavy job on documentation-only follow-up commits until the PR is merged.
- This remains compile evidence only. It does not establish that the generated generic artifacts boot MT6990 or SBAT6D.

This proves a generic ARM64 Linux and Ethernet-driver compile against the selected OpenWrt source. It does not prove MT6990 boot support, DTS validity, switch topology, or device operation. The generated kernel is experimental and must not be installed on SBAT6D.


## Stage 4 evidence-based DTS and rootfs follow-up

The B-unit `boot_b` runtime FDT capture was reviewed read-only. This public branch transcribes only CPU, PSCI, GICv3, timer and root-compatible facts; raw FDT and its unit-specific digest remain local. The FDT has two conflicting root memory descriptions at base `0x80000000`, so this DTS intentionally has no `memory` node. The observed eMMC, PCIe and MAC/SGMII facts are not enabled because matching MT6990 providers, clocks/resets/genpd/pinctrl and full bindings/drivers are not yet implemented. The resulting DTB is explicitly non-bootable.

The failed hosted run [39954594031](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39954594031) failed in the generic `gpio-button-hotplug.ko` package stage after the kernel and DTB steps. Its log reports a compiler mismatch warning followed by unresolved `__stack_chk_guard` in modpost. The workflow now passes the same explicit OpenWrt AArch64 `KERNEL_CC` and `KERNEL_CROSS` to `target/linux/compile`, `package/compile`, `package/install` and `target/install`; stack protection is retained. This is a targeted remediation hypothesis grounded in the compiler mismatch and symbol failure, pending the next hosted build.

The first stage-4 Hosted run [39969583956](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39969583956) compiled the kernel and DTB and completed `dt_binding_check`, `dt-doc-validate` and targeted `dt-validate`. It then failed at a stale shell assertion that expected the SoC compatible as a single-item property, while the observed correct root property contains both the firmware-reported platform string and `mediatek,mt6990`. The workflow assertion is corrected to match the two-string list. Package/rootfs was skipped in that run; the `KERNEL_CC` fix therefore remains awaiting Hosted verification.
