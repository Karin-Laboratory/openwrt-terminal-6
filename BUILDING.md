# Reproducible build contract / ビルド再現性

**Status: NOT YET REPRODUCIBLE FROM THIS PUBLIC REPOSITORY.** Do not interpret this document as a completed build guide. No verified public source manifest, patch series or clean-room build result has been published yet.

A build guide may be marked *verified* only when a contributor on a clean environment can:

1. Check out an immutable commit of this repository and a pinned upstream OpenWrt commit/tag.
2. Fetch all legal, accessible inputs by documented URLs and verify checksums.
3. Apply the reviewed patch series with deterministic ordering.
4. Identify the toolchain, host packages, defconfig, build flags and firmware dependencies.
5. Build without private files, credentials, vendor keys, internal caches or unpublished artifacts.
6. Record build logs, output names, lengths and SHA-256 hashes.
7. Distinguish reproducible **compilation** from byte-for-byte reproducible **signed boot images** (the latter may not be feasible without nonpublic OEM materials).

## Required future commands

The exact commands are **pending source publication and independent verification**. We will add tested commands, not speculative placeholders. Until then, **do not attempt to build a flashable image using this document**.

## Evidence to include with every candidate

- Git revision: project and upstream hashes
- Host environment: OS, architecture, tool versions
- Inputs: permitted source URLs and digests
- Output manifest: path, byte length, SHA-256
- CI workflow run and log retention
- Hardware and boot-slot identity (sanitized)
- Test matrix references and known failures

Do not upload proprietary firmware or signing keys just to make a build pass. If privately acquired OEM input is required, document that limitation and provide a legal source-only workflow if possible.

日本語: **公開リポジトリ単独での第三者再現ビルドは、まだ成立していません。** ソース一式、固定した依存関係、再現コマンド、成果物ハッシュと独立検証が揃うまで「再現可能」と宣言しません。

## GitHub-hosted offline checks

The public repository has a GitHub Actions workflow at
[.github/workflows/public-source-checks.yml](.github/workflows/public-source-checks.yml).
It uses GitHub-hosted `ubuntu-24.04` on `main` pushes, pull requests, and
manual workflow dispatch, running DTS overlay compilation, synthetic fixture
merging, provider references, and Python tests. It does **not** download
proprietary inputs or produce a bootable image.

**Scope:** this establishes a publicly runnable *source syntax and fixture*
gate only. Linux 6.18.44 PHY/PCS object compilation remains a separate,
unverified gate until the legal/public source inputs, immutable donor pin,
kernel revision, patch ordering, and ARM64 toolchain are assembled in public
CI. Do not describe the current workflow as the complete OpenWrt build.
