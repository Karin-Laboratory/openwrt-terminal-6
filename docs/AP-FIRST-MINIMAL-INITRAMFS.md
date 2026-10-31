# AP-first milestone: standalone unsigned AArch64 PID1 initramfs

**Scope: real, non-installable ARM64 initramfs construction, not an OpenWrt rootfs, Air6 kernel Image, Air6 DTB, AP or hardware boot.** Tracks #74 / #21 / #4.

`python3 scripts/build-minimal-arm64-initramfs.py /path/to/new-empty-output-directory` compiles the independently authored `scripts/air6-diagnostic-init.c` as a **static AArch64 ELF64 ET_EXEC** using native `gcc`/`ld` on the public GitHub-hosted `ubuntu-24.04-arm` runner (or preinstalled `clang`/`ld.lld` for an optional local cross-build), with no libc or dynamic loader. It creates a deterministic Linux `newc` archive with `/init` (PID1), `/dev/console` (5:1), `/dev/null` (1:3), `/proc` and `/sys`. PID1 writes a diagnostic banner and sleeps forever. It does not mount, configure networking, expose SSH, alter partitions or perform recovery. The archive is compressed with gzip mtime=0.

The output directory must not exist beforehand; privileged execution is refused. The x86_64 GitHub-hosted runner lacks a preinstalled complete Clang/LLD cross-toolchain, so the native ARM64 job is deliberately separate from the source-only x86_64 host-test job. The tool never downloads, signs, flashes, executes the cross-built binary, or uploads artifacts. `manifest.json` records the compiler/linker versions, source SHA-256, ELF SHA-256 and compressed initramfs SHA-256. GitHub-hosted ARM64 CI **actually compiles and archives** this object in an ephemeral directory and deletes it after verification. No binary is committed or distributed. For reproducibility across machines, pin the compiler/linker version and verify the manifest: gzip timestamp normalization alone does not make cross-toolchain outputs universally byte-identical.

**Next required integration:** independently rights-cleared Linux 6.18 MT6990 kernel configuration, matching Air6 board DTS/SoC DTSI and providers, actual `Image` plus DTB build and `dtbs_check`; then boot the combined Image/DTB/initramfs offline in a suitable isolated emulator if supported. This tiny diagnostic PID1 is intentionally not OpenWrt `procd` and contains no AP stack. Separately build a native SBAT6 OpenWrt rootfs and integrate Ethernet/2.4+5 GHz radio inputs with rights review. Historic private 6.18.44 LAN/SSH/AP successes are valid historical observations, not proof for this new public source.

**Safety and legal gates:** all new source-catalog entries remain `rights_review=pending`. This work neither proves source redistribution clearance nor authorizes an installable image, LK/Preloader modification, boot-slot write, signing, private firmware, calibration/EEPROM import or any device action.

## Upstream ARM64 Image + embedded PID1 integration experiment

The public hosted CI job `arm64-image-with-initramfs` builds a **real Linux ARM64 Image** from official Linux v6.18 commit `7d0a66e4bb9081d75c82ec4957c50034cb0ea449`, with the above independently built diagnostic initramfs selected via `CONFIG_INITRAMFS_SOURCE`. The job verifies the Linux v6.18 `__initramfs_size` symbol, checks that `usr/initramfs_inc_data` exactly matches the generated compressed archive, and confirms `usr/initramfs_data.o` was compiled, and logs Image/archive SHA-256 and byte lengths. Inputs and compiler run on a non-root GitHub-hosted native ARM64 runner; the generated kernel and archive are ephemeral and are **not uploaded or distributed**.

**Precise boundary:** This is an upstream **generic** ARM64 Image with an embedded PID1, **not an MT6990/Air6-capable kernel**. No donor/vendor MT6990 drivers, unresolved-rights SoC DTSI, device-specific DTB, wireless firmware or proprietary files are used in this Image build. Existing independent Air6 DT syntax checks are separate and do not make the kernel/DTB pair compatible. No runtime boot test is performed. Successful compilation alone does not establish rights clearance for distribution.

**Next integration gate (#20):** identify a lawful and version-matched MT6990 kernel driver + clock/reset/genpd + SoC DTSI baseline, then compile the Air6 DTB with the **same** kernel tree/config and validate `dtbs_check`. Only after that can the integrated unsigned Image/DTB/initramfs be evaluated as a board-targeted candidate. Keep #74/#20/#21/#4 open.


## Static BusyBox PID1 in the same Image build (2026-10-31, PR pending)

The existing native AArch64 BusyBox 1.36.1 **glibc-static** source build can now
construct a deterministic Linux `newc` gzip initramfs using
`scripts/package-arm64-busybox-initramfs.py`. Its `/init` is a tiny shell
script interpreted by the included static `/bin/busybox` through
`/bin/sh`. It writes a diagnostic banner to `/dev/console` and sleeps;
there is **no interactive login, networking, password, persistent setting,
SSH or AP service**. The packager validates the AArch64 ELF has no
`PT_INTERP`, round-trips all cpio entries and checks their exact payloads.

The hosted `.github/workflows/arm64-image-build.yml` job now embeds this
BusyBox PID1 archive in the **same** Linux v6.18 ARM64 `Image` build as the
upstream Ethernet/DSA/PCS components, the MT6990 analog PHY and IFRAO clock
object, and the base/opt-in Air6 candidate DTBs. It checks byte equality
with `usr/initramfs_inc_data` and `usr/initramfs_data.o`. This is a
**material kernel/userspace compile integration**, not an OpenWrt musl rootfs,
procd/netifd/wpad build, completed MT6990 NETSYS/clock/reset/genpd
integration, validated hardware boot, rights approval or installable image.

The earlier freestanding C diagnostic PID1 builder and its separate
source-only CI test remain available for comparison. The original static
BusyBox tar rootfs-stage job also remains independent. All generated
binaries are ephemeral and discarded, never uploaded or distributed.

## Native musl-static PID1 integrated into Image (AP-first #74/#21)

The hosted ARM64 Image workflow now compiles pinned musl 1.2.5, Linux v6.18
UAPI and BusyBox 1.36.1 to produce a real static AArch64 `/init` archive.
It checks the `libc=musl-static` manifest and embeds identical archive bytes
in the same upstream Linux v6.18 Image as the existing Ethernet/PHY/PCS/IFRAO
objects and candidate Air6 DTBs. The previous glibc-static builder remains
available separately. All build outputs are ephemeral and not uploaded.

This is NOT an OpenWrt-built toolchain, independent SBAT6 target, procd/netifd
rootfs, matching NETSYS/TOPCK/genpd integration, boot-tested AP or release.
Rights review remains pending; hosted CI must pass before claiming success.
