# Reproducible build contract / ビルド再現性

**Status: GENERIC MT6990 OPENWRT BUILD PASSED IN HOSTED CI; SBAT6D FIRMWARE NOT READY.** The experimental generic MT6990 target built Linux 6.18.55, MediaTek Ethernet, package installation and squashfs staging in [run #40091561598](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40091561598), on source commit `af6cb6ddc67b335c7c7da024eedae54f5dfb51b0`. This does **not** establish an installable SBAT6D image or independent third-party reproduction. See [Release readiness](RELEASE-READINESS.md) for exact scope and open gates.

A build guide may be marked *verified* only when a contributor on a clean environment can:

1. Check out an immutable commit of this repository and a pinned upstream OpenWrt commit/tag.
2. Fetch all legal, accessible inputs by documented URLs and verify checksums.
3. Apply the reviewed patch series with deterministic ordering.
4. Identify the toolchain, host packages, defconfig, build flags and firmware dependencies.
5. Build without private files, credentials, vendor keys, internal caches or unpublished artifacts.
6. Record build logs, output names, lengths and SHA-256 hashes.
7. Distinguish reproducible **compilation** from byte-for-byte reproducible **signed boot images** (the latter may not be feasible without nonpublic OEM materials).

## Generic target success evidence

The successful hosted generic target workflow is [`.github/workflows/mt6990-target-build.yml`](.github/workflows/mt6990-target-build.yml). It checks out pinned OpenWrt, applies the MT6990 target and kernel patch series, invokes the AArch64 cross-toolchain, builds Linux and MediaTek Ethernet, and stages generic package/rootfs output. Reported squashfs SHA-256: `10a3ed9981dd6ed9f078a9a9c6feb40ba5f0f20e436dd27dc7778c812af850a6` (reported build manifest; not separately recomputed here). The generated rootfs is **not a boot or flash image**; no complete RAM mapping, provider drivers, tested partition layout or recovery proof is supplied.

## Required future commands

Commands for a **flashable OpenWrt image** are still pending. The available, CI-backed Linux Ethernet **object compilation** commands are published in [Public source verification](docs/PUBLIC-SOURCE-VERIFICATION.md). **Do not use these object-build steps as instructions for flashing a device.**

## Evidence to include with every candidate

- Git revision: project and upstream hashes
- Host environment: OS, architecture, tool versions
- Inputs: permitted source URLs and digests
- Output manifest: path, byte length, SHA-256
- CI workflow run and log retention
- Hardware and boot-slot identity (sanitized)
- Test matrix references and known failures

Do not upload proprietary firmware or signing keys just to make a build pass. If privately acquired OEM input is required, document that limitation and provide a legal source-only workflow if possible.

日本語: **GitHub Actionsでの汎用MT6990 rootfsビルドは成功。第三者による独立再現とSBAT6D実機用ファームウェアは未完成です。** ソース一式、固定した依存関係、再現コマンド、成果物ハッシュと独立検証が揃うまで「再現可能」と宣言しません。

## GitHub-hosted offline checks

The public repository has a GitHub Actions workflow at
[.github/workflows/public-source-checks.yml](.github/workflows/public-source-checks.yml).
It uses GitHub-hosted `ubuntu-24.04` on `main` pushes, pull requests, and
manual workflow dispatch, running DTS overlay compilation, synthetic fixture
merging, provider references, and Python tests. It does **not** download
proprietary inputs or produce a bootable image.

**Scope:** this establishes a publicly runnable *source syntax and fixture*
gate only. The upstream Linux **v6.18 MediaTek Ethernet RFC1/RFC2** object build is a separately verified public CI gate ([run #39877158871](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158871)). This does **not** verify a Linux 6.18.44 board-specific PHY/PCS integration, full kernel or OpenWrt firmware. Do not describe the current workflow as the complete OpenWrt build.

## Manual Linux 6.18.44 donor PHY compilation probe

[mt6990-phy-compile-probe.yml](.github/workflows/mt6990-phy-compile-probe.yml)
is a separate **manual** GitHub-hosted `ubuntu-24.04` workflow.
It pins the previously audited donor commit and Git blob; obtains upstream
Linux `v6.18.44`, configures ARM64, and attempts to compile the donor's
`phy-mtk-mt6990-sgmii.o` directly. A failure is useful diagnostic evidence,
not authorization to skip a failing stage or silently change version.

Run it from **Actions > MT6990 PHY compile probe (public) > Run workflow**.
This is deliberately a first compatibility probe, **not** compilation of the
private Test25 derivative, the PCS patch chain, a full OpenWrt image or a
working hardware integration. Inspect its run logs before claiming PASS.
