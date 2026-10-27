# Verified isolated build and host-test results (2026-10-27)

All links below are authenticated GitHub Actions job records from the retained **Private v2 archive**, executed on a trusted runner. The archival **main** and the clean public-candidate history are not merged with one another. These records are independent host-side evidence, **not** a firmware release approval.

## Completed: reproducible source-equivalent Ethernet object builds

- [Run #40443738043](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40443738043) conclusion **SUCCESS**.
- Verified clean-source Ethernet RFC blobs before compilation: `3fc960a3ea7e5580fae46a463d95e619e8a0ecdf` and `5514a6868ae03acca08c49a4b92c42da88c4ce5a`.
- The v6.18 Linux `mtk_eth_soc.o` cross-compilation succeeded for upstream baseline, RFC #1, and RFC #1+#2, with source checks and a final success log marker.
- No MT6990 board Device Tree, generated boot partition, installed firmware, signed kernel or live device traffic was produced.

## Completed: upstream generic Linux ARM64 kernel Image

- [Run #40444627122](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40444627122) conclusion **SUCCESS**; the compiler step and every job step concluded success.
- The log explicitly emitted `GENERIC_UPSTREAM_ARM64_IMAGE_BUILD_PASS`.
- Source was pinned to upstream Linux v6.18 commit `7d0a66e4bb9081d75c82ec4957c50034cb0ea449`. The original build step records kernel object identities and Image hash/size in the GitHub Actions summary, not a publicly distributed image.
- **Critical limitation:** Upstream `defconfig` ARM64 Image, not a rights-cleared SBAT6 MT6990 kernel + board DTS + OpenWrt rootfs. It does not boot the device or establish Wi-Fi/modem support.

## Completed: exact-source clean repository synthetic regression tests

- [Run #40445484403](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40445484403) conclusion **SUCCESS**. Compared 19 Git blobs directly with the clean source and passed **54** standalone synthetic tests.
- [Run #40472660074](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40472660074) conclusion **SUCCESS**. Extended the whitelist to 25 clean-repo blobs (including disabled-only SGMII Overlay, metadata, source-only OpenWrt donor fetch and two additional test modules); log showed `VERIFIED_CLEAN_SOURCE_WHITELIST_25_BLOBS` and `CLEAN_SOURCE_25_BLOB_BOARD_DONOR_REGRESSION_PASS`.
- The last run passed **62 standalone synthetic tests** across 11 test scripts, plus the offline SGMII source-level safety command. These do not substitute for tests of a live device or full new-repository CI.
- [Run #40472960531](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40472960531) conclusion **SUCCESS** for the same 25-blob/62-test gate, but its optional `dtc` step printed `DTC_UNAVAILABLE_NOT_VERIFIED`. The optional step was skipped, so **syntax compilation was not established by that run**.
- A follow-on [run #40473252747](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40473252747) added an isolated pinned-Linux v6.18 host `scripts_dtc` build with a disabled-only SGMII Overlay compile/roundtrip check. It concluded **SUCCESS**. The completed job log emitted `PINNED_LINUX_DTC_DISABLED_SGMII_OVERLAY_SYNTAX_PASS` after compiling host dtc from pinned Linux v6.18, compiling SGMII1 DTSo to a disposable DTBO, and checking that both fragments stayed disabled after DTB roundtrip. This is **syntax success only**, not `dtbs_check`, validated power/clock providers or a bootable board DTS.

## What remains unproven

- New clean repository's own hosted-only CI still fails *before* executing test steps due to environment/entitlement unknown; main-only self-host jobs remain queued due to runner registration to the new repository. Archive Private runner passing does not clear new-repo CI.
- A full source reproducible board-kernel build and independently pinned OpenWrt userspace/rootfs do not exist here.
- Stage9B/10 historical LTE IPv4 success is evidence but cannot currently be reproduced with a complete publicly redistributable RIL/modem runtime from the new clean repository. 5G NR and IPv6 remain separate unverified features.
- A/B LK retry semantics, independent rescue, signing/legal rights, radio firmware/calibration, all-history/CI-log safety and all 32 source-catalog rights approvals are still incomplete.

**Publication: Private, NO-GO.** **Firmware distribution: NO-GO.** A successful host smoke test cannot authorize either transition by itself.

## Completed: independently pinned AArch64 BusyBox userspace smoke

[Private runner #40498318443](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40498318443) **SUCCESS**: BusyBox v1.36.1 pinned commit `1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4`, Makefile blob `fa8cb761443388730372eaf260e7ca1a0235bc43`, 5 synthetic security tests, ARM64 BusyBox cross compile, and ELF header architecture check. Ephemeral ELF size: 1,053,400 bytes, SHA-256 `edac38e43eb54dbaa0ef95a213834d32379c71bcdfccb2b69230ecf91d391e87`. Compile excludes obsolete `CONFIG_TC` applet incompatible with the available new kernel headers; no source patch was applied. This is **not a complete OpenWrt rootfs**, deployable binary package, or actual network-driver or modem test.
