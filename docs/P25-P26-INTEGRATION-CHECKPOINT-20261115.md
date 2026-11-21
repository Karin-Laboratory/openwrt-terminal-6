# 2026-11-15 unsigned P25/P26 integration checkpoint

## Source-built P26: proven in ephemeral CI

- Head: `759201d5be38ea18dee6652dc4fac262633c90ef` (PR #206).
- [Native Actions run #43667557039](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/43667557039), job `132670382147`, completed SUCCESS.
- The actual same-run OpenWrt `package/install` rootfs reported **37 installed packages**; `mksquashfs` and the private-directory p26 packer produced **134,217,728 bytes**.
- Full P26 SHA-256: `e8396df108c959b6d67d9a39e556b91a97c28133ed8d80f1fbc7827a6ac20415`.
- Independent unsquashfs/readback and producer-bound attestation emitted `P26_INDEPENDENT_READBACK_PASS`, `PUBLIC_P26_ATTESTED_SAME_RUN_READBACK_PASS` and `PUBLIC_MT6990_REAL_SOURCE_BUILT_P26_INDEPENDENT_READBACK_PASS` with matching SHA-256.
- Later exact head `afb204f1` changes staging hardlink verification; do **not** transfer this proof to later heads without their own tests.
- The P26 binary existed only in the ephemeral runner, was intentionally not uploaded or retained and was **not** device/LK tested. No firmware distribution authorization.

## P25 lane ported from existing public PR #133

Source and host tests are imported as byte-identical Git blobs from existing [PR #133](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/133), retaining MIT provenance/pending rights metadata. This integration does not import old P26 producer code or private OEM/template bytes. Host regression must complete on this exact head.

The Air6-specific P25 is **BLOCKED** pending independent validation of:
1. The exact public Image.gz/DTB and their boot-v2 load configuration for this board, including kernel-embedded first stage linked to the same-run P26 SHA.
2. The observed 64-byte DTB-section prefix: only an owner-controlled locally proven and lawfully usable source may supply the bytes. A guessed all-zero prefix or a generic Android-v2 profile is not Air6 acceptance.
3. Full 32 MiB unsigned P25 pack and independent full-image readback, plus same-run P25/P26 pairing receipt.

No LK acceptance, signing, flashing, RF transmission or release is claimed.

## Parallel safety review

Public source history scanner has nine older reachable-history findings, including examples in test/scanner code. Keep it enabled, triage actual exposure separately, and do not use its current FAIL as a stop-work condition for isolated unsigned engineering builds.

Build discipline: `REBUILD_SCOPE=A` for this source-only P25 integration; `REUSE_PROOF=none`; `CACHE_DECISION=no cross-run binary reuse`. New native builds are only justified for complete same-run P25/P26 manufacturing; successful prior logs are not retained output bytes.
