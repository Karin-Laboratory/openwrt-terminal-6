# AP-first next gates: reproducible OpenWrt packages and isolated wireless smoke

**2026-11-01 design/triage only.** The evidence hierarchy is documented in [STATUS](STATUS.md) and the acceptance criteria in [Issue #74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74). No test in this document has been run by adding this file.

## 1. Native OpenWrt buildroot is the next implementation track

- [PR #107](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/107) separately adds an independently checkable **source-only** `mediatek/mt6990` subtarget skeleton in a pinned OpenWrt full tree, and has an upstream `make defconfig` CI. Do not replicate its scripts in a second competing pipeline or infer it is a flashable SBAT6 target.
- After #107 is merged with required checks, extend its exact locked OpenWrt revision/feeds/profile incrementally: first actual `base-files`, `procd`, `ubus`, `uci`, `netifd`, `dropbear` packages; then board-specific Ethernet, `mac80211`, `wpad` with legally usable firmware and rights review.
- Record OpenWrt `package/Makefile` patches and configure differences versus the existing synthetic/direct-musl smoke stage. The direct-musl stage remains an independent fast test, **not** the full distribution build. SDK can build packages for existing targets, but it is not a substitute for defining an independent SBAT6 target and building the full OpenWrt tree.
- Gate every later actual `Image`, `dtb`, `rootfs` and noninstallable board recipe on source/tree/config/feeds hashes, source ownership and valid dependency closure. Do not ship donor LG6851F Device profiles, OEM binary/EEPROM data, signing tools or keys.

## 2. Finish QEMU network IPC before wireless HWSIM

- [PR #103](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/103) proved `/init → procd → ubus service add` in a real QEMU `virt` guest; [PR #104](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/104) proved the same netifd PID persists for over one second.
- [PR #106](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/106) extends that runtime to create an **empty** Linux bridge via UCI + `ubus call network reload`, verified through `/sys/class/net`. As of the drafting snapshot, the PR is open; inspect its **final** checks before treating it as a merged baseline.
- Follow-up after #106: in the *same no-NIC* QEMU virt guest, exercise `ubus list`/network interface or device objects and `ubus call network.interface.loopback status` (or the exact source-version-supported object). Require machine-parsed `up: true` only when the runtime configuration/protocol actually supports that claim; failures must not be converted into markers by shell echo.
- The guest is an isolated **generic** ARM64 `virt` target. It neither enumerates the Air6 MT6990 SoC nor proves PCIe/Wi-Fi/MT7531 hardware operations.

## 3. Later virtual AP/STA test, separate from physical Air6

Proceed only after the native OpenWrt package and kernel configuration is reproducible. In a dedicated, ephemeral isolated VM/kernel that genuinely supports `CONFIG_CFG80211`, `CONFIG_MAC80211`, `CONFIG_MAC80211_HWSIM`, `wpad/hostapd` and a STA client (`wpa_supplicant`), test:
1. Build and validate authentic OpenWrt wireless config generation using the version-pinned packages and scripts, without private radio firmware, EEPROM or regulatory overrides.
2. Instantiate virtual radios inside the isolated guest; bring up an AP and a separate STA, assert WPA2/WPA3 handshake and L2 connectivity within that guest. Capture hostapd and wpa_supplicant evidence, radio enumeration and security version. Make a specific minimal mode assertion before adding more radios.
3. Do not use a privileged home runner or host HWSIM devices from untrusted PRs. If the available hosted runner cannot safely isolate a kernel/HWSIM VM, record the blocker and use a separately approved trusted CI design rather than granting host networking privileges.
4. Keep the Air6-specific `mt7996e`/PCIe/firmware/EEPROM/2.4+5GHz acceptance separate; **HWSIM success never means Air6 AP success**.

## 4. MT6990 kernel blockers and collaboration

For [Issue #20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), produce a **source-only, isolated** provider dependency matrix with each required compatible/binding and source revision for NETSYS/PCS1/SGMII1, clock/reset/genpd, MT7531, PCIe and Wi-Fi. Apply candidate donor source to a disposable pinned Linux v6.18 tree for targeted Kbuild/`dtbs_check` **only after source and license review**. A blanket donor overlay that crosses hardware or rights boundaries is not a prerequisite.

Share narrowly reproducible fixes for donor PHY patches 0002/0003 with their author through the author's public contribution channels, without uploading private Test25/Stage10 material or security-sensitive root/firmware information. Seek provenance/redistribution permission separately from the technical patch submission.

## Completion boundaries

| Check | Minimum evidence | Still unproven |
| --- | --- | --- |
| Public QEMU netifd | Actual guest log, procd/ubus IPC, loopback/empty bridge, paired CI URL | Air6 NIC/AP |
| Official OpenWrt buildroot | Pinned full tree, successful native target selection and package builds | Board boot/p25/p26 |
| Virtual HWSIM AP | Isolated kernel/hostapd+STA handshake and L2 packet traces | MT7996/EEPROM/regulatory/hardware AP |
| Hardware AP | Independently approved Air6 cold-boot and Ethernet+2.4/5 GHz client traffic | Public release until rights/safety review |

**Priority order:** finish #106 evidence → develop official package closure following #107 → extend QEMU IPC → isolated HWSIM → separate Air6 hardware acceptance. Maintain the missing MT6990 provider tree in parallel. No auto-signing or flashing.
