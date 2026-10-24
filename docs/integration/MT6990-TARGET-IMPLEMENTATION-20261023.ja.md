# MT6990 OpenWrt subtarget: implementation and limits

Updated: 2026-10-24

## Implemented source

`integration/mt6990-target.patch` adds `mediatek/mt6990` to the pinned OpenWrt MediaTek target. It selects the generic AArch64 userspace/toolchain, Linux `Image`, `CONFIG_ARCH_MEDIATEK`, `CONFIG_DTC`, and `CONFIG_NET_MEDIATEK_SOC`. The MT7531 observation is represented by the upstream MT7530 DSA family and MediaTek tagger configuration for compile coverage; it does not prove SBAT6D switch wiring or runtime operation. The MediaTek Ethernet cleanup/requeue RFC patches are added after OpenWrt's existing 6.18 patch series.

The subtarget has no CPU microarchitecture selection, board profile, device-specific package set, production DTS, image recipe, partition layout, signing or installation output. `files-6.18` carries an independently authored partial SoC/board DTS: four observed Cortex-A55 CPU MPIDRs, PSCI SMC, GICv3 and architected timer, plus a sanitized boot_b observation inventory for UART0, eMMC, three PCIe roots/PHYs, NETSYS/MACs and SGMII resources. All peripheral and provider nodes are explicitly disabled; the conflicting RAM ranges and non-standard firmware SGMII relationship lists are omitted. `image/mt6990.mk` remains empty so Kconfig does not advertise an unsupported device. The generic compile profile explicitly disables unverified SoC-specific clock, pinctrl, external-interrupt and watchdog drivers; CI rejects accidental selection of these families. This is a source-build target for generic kernel and package/rootfs work, not a bootable MT6990 port.

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

PR #1 defines `board/mt6990.dtsi` with the observed four Cortex-A55 MPIDRs, PSCI SMC conduit, GICv3 distributor/redistributor ranges and maintenance PPI, plus architected timer PPIs and recorded counter frequency. `board/mt6990-observed-peripherals.dtsi` records same-FDT resource and provider references without enabling nodes. `board/sbat6d-incomplete.dts` provides the observed root compatible pair and an explicit research model. OpenWrt integration carries these sources, registers the DTB and adds the root compatible sequence to the MediaTek binding. The Linux 6.18.55 UART driver has a generic fallback match for `mediatek,mt6577-uart`, but its binding schema did not accept the observed `mediatek,mt6873-uart` first compatible. PR #1 now carries an enum-only schema patch for this observed identifier; the driver is unchanged and the UART observation node remains disabled. No OpenWrt device profile or image recipe exists.

Linux 6.18.55 Kbuild generated the expanded partial DTB (SHA-256 `82c8d70a7a89dc66cf04df80b1a72eb946e8391a390c530de99c55d6412241be`). Targeted `dt_binding_check` completed for the MediaTek root binding and UART alias. The earlier isolated validator run exposed that the unmodified UART schema rejected the observed compatible tuple; a minimal enum-only correction is now included in the Linux patch series and requires revalidation. `dtbs` with `CHECK_DTBS=y` completed with exit 0 but printed existing schema errors for unrelated MT7988 board trees; it is not a clean full-tree pass. No schema for the disabled MT6990 peripheral providers or consumers is claimed. Successful compilation/isolated validation does not establish bootability.

The same B-unit boot_b FDT contains conflicting root memory descriptions at base `0x80000000`; the DTS has no memory node. eMMC, PCIe and MAC/SGMII facts remain disabled because Linux 6.18.55 lacks verified MT6990 providers and complete clocks/resets/genpd/pinctrl/binding dependencies in this workstream. Proprietary SGMII/PHY/PLL relationship lists are retained as sanitized written observations only, not copied into the DTS. The raw FDT and unit-specific digest are not published.

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

The 2026-10-22 B-unit `boot_b` FDT record and its paired read-only capture were reviewed. PR #1 commit `d29b513746d914481b273e5ec286785ed1294f84` adds a sanitized inventory for UART0, eMMC, three PCIe controllers/PHYs, NETSYS/MAC0/MAC1, SGMII and shared-PLL resource references. All observation/provider nodes are disabled; the two conflicting RAM ranges remain omitted, and proprietary SGMII relationship properties are not encoded as unsupported phandle arrays. The raw FDT and per-unit digest remain local. Linux 6.18.55 Kbuild produced a non-bootable research DTB with SHA-256 `82c8d70a7a89dc66cf04df80b1a72eb946e8391a390c530de99c55d6412241be`; target-isolated validation returned no diagnostics. Full-tree MediaTek validation still reports existing unrelated board-schema errors.

Hosted runs [39978733621](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39978733621) and [39969583956](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39969583956) reached the generic `gpio-button-hotplug.ko` package stage after kernel and targeted DTB/schema validation, then failed with an unresolved `__stack_chk_guard` in modpost. The compiler was already the same OpenWrt AArch64 compiler in the later run, so compiler identity alone did not fix it. The kernel config uses `CONFIG_STACKPROTECTOR_PER_TASK=y`; arm64 then expects modules to read the canary from `sp_el0` at `TSK_STACK_CANARY`, and does not export the global `__stack_chk_guard`. The package step now derives that offset from the prepared kernel's generated `asm-offsets.h` and passes the matching `-mstack-protector-guard=sysreg`, register and offset flags through OpenWrt's `CONFIG_KERNEL_CFLAGS` for package and rootfs stages. A local Linux 6.18.55 arm64 control build of `gpio-button-hotplug.ko` with the same per-task canary ABI completed successfully; hosted MT6990-target verification is still required.

Run [39969583956](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39969583956) compiled the kernel and DTB and completed `dt_binding_check`, `dt-doc-validate` and targeted `dt-validate`, then failed at a stale shell assertion that expected the SoC compatible as a single-item property. The observed root property correctly contains both the firmware-reported platform string and `mediatek,mt6990`; the assertion was corrected. Package/rootfs was skipped in that run. The subsequent run [39978733621](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39978733621) passed that assertion but exposed the per-task canary ABI issue described above. The new dynamically derived module flags were included in run [39988538097](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39988538097); as of this document update, its generic AArch64 toolchain job is still running. That run uses the earlier, CPU-only research DTS; a new run is required after the current integration patch update.

### Stage 5 CI guard correction (2026-10-24)

Run [39993560027](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39993560027) passed the generic toolchain, Linux 6.18.55 preparation, kernel/MediaTek Ethernet compile, DTB generation and targeted schema checks. Its package/rootfs step exited before the first `make package/compile` command. The job log shows the compiler was found and reports GCC 14.4.0, then stops at the silent `grep -qx CONFIG_STACKPROTECTOR_PER_TASK=y` assertion. It does **not** show a package failure or a repeated `__stack_chk_guard` modpost error. The following `TSK_STACK_CANARY` extraction was not reached.

The prior workflow assertion was the failure point: the target config did not retain `CONFIG_STACKPROTECTOR_PER_TASK=y`. The MT6990 Linux config now explicitly selects this arm64 per-task canary ABI. CI now prints effective settings, reruns kernel `prepare` with the same AArch64 compiler to refresh generated offsets, and emits actionable errors if configuration or offset is absent. A fresh pinned-source `target/linux/prepare` reproduced the setting and offset. The next Hosted run must prove package compile/install and generic rootfs staging pass with these flags.


### Stage 5 ABI-matched external module flags (2026-10-24)

Hosted run [40014932523](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40014932523) passed toolchain, Linux 6.18.55 kernel/Ethernet and research DTB compilation. The patched UART binding was included. Its package step again stopped before package/compile: the effective kernel config had CONFIG_STACKPROTECTOR=y but CONFIG_STACKPROTECTOR_PER_TASK absent, so the prior per-task-only assertion was not valid for this generated configuration. No module build was attempted in that run.

The workflow now preserves stack protection and matches module code generation to the final kernel ABI. Per-task mode derives TSK_STACK_CANARY and selects the sp_el0 guard; global mode requires an exported __stack_chk_guard in Module.symvers and explicitly selects the global guard. The MT6990 fragment no longer forces Kconfig-generated compiler capability or per-task symbols. Local workflow tests cover both ABI branches; a new Hosted run is required to verify package compile/install and rootfs staging.

### Stage 6 package-stage preflight failure and ABI correction (2026-10-24)

Runs [40023669994](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40023669994) (`6457c3b`) and [40030050970](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40030050970) (`6222e37`) fail identically. Toolchain, Linux preparation, Kconfig normalization, kernel, MediaTek Ethernet and DTB/schema steps pass. The package/rootfs workflow step exits at its ABI preflight with `CONFIG_STACKPROTECTOR=y` but no `CONFIG_STACKPROTECTOR_PER_TASK`; `Module.symvers` has no exported `__stack_chk_guard`. The first `make package/compile` command is not reached. Therefore these two runs do not demonstrate a package compiler or rootfs construction failure, and they do not test `gpio-button-hotplug.ko`.

The target config now requests `CONFIG_STACKPROTECTOR_PER_TASK=y`, while retaining `CONFIG_STACKPROTECTOR=y`. Kernel Kconfig must still confirm `CONFIG_CC_HAVE_STACKPROTECTOR_SYSREG=y`; the workflow fails closed with compiler diagnostics if that dependency is unavailable. External-module flags remain derived from the resulting effective config and `TSK_STACK_CANARY` offset. The local AArch64 GCC 14.2 probe emitted an `mrs ..., sp_el0` canary access; this is not a substitute for the pinned OpenWrt GCC 14.4 toolchain check. Linux v6.18.55 defines per-task mode behind the compiler capability and exports the global guard only in the non-per-task configuration ([arm64 Kconfig](https://github.com/gregkh/linux/blob/v6.18.55/arch/arm64/Kconfig), [process.c](https://github.com/gregkh/linux/blob/v6.18.55/arch/arm64/kernel/process.c), [arm64 Makefile](https://github.com/gregkh/linux/blob/v6.18.55/arch/arm64/Makefile)). The next hosted run must pass this gate and complete package compile/install and generic rootfs staging before the fix is considered verified.
