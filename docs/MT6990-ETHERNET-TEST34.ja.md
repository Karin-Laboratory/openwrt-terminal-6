# MT6990 Ethernet FE lifecycle: Test34 source-level research

Date: 2026-10-23. Status: **source review only, not a compiled or tested driver**.

This is an independently written summary of internal Test34 research. It contains no OEM images, signing materials, device identifiers, or copied kernel source code.

## Problem and intended fix

After transient FE/network recovery attempts, delayed work may race with driver teardown, repeated requests, or modem-side ownership of shared resources. Test34 proposes the following changes to a private MT6990 derivative of Linux `mtk_eth_soc.c` and `mtk_eth_soc.h`:

1. Gate request submission and shutdown transitions under a common spinlock, restricted to MT6990; preserve pre-existing paths for unrelated SoCs.
2. Distinguish ordinary and deferred requests so a stale delayed callback cannot submit a redundant FE reset after recovery.
3. Avoid resetting FE while modem-side ownership is busy. Defer and retry rather than force shared-resource disruption.
4. Use bounded backoff for FE failures (5, 10, 20, 40, 40 seconds), a single recheck after exhaustion, and suppression until reprobe if it fails.
5. Quiesce pending, retry and DMA-monitor work before device teardown; apply the same cleanup discipline on failed probe unwind paths.
6. Allow application only to an explicitly marked disposable copy whose two input file SHA-256 hashes match the expected private baseline.

These are **implementation claims from internal source review**, not proof that kernel workqueue races have been eliminated.

## Input and output identity for independent comparison

| Component | SHA-256 |
| --- | --- |
| Input `mtk_eth_soc.c` (Test32) | `0b8828e99c77249e39790af9f0cccf997d1e0b89b1c9b31634c7d0684ed20e44` |
| Input `mtk_eth_soc.h` (Test32) | `9cc916f920c0a0895ab6e0a954fb5df07d509cf3a5e94347cb0445529b180488` |
| Proposed output `mtk_eth_soc.c` (Test34) | `f03dd3e6d3ea1262a697776afa4df1ab637ed56e5c84b629cb73f96f7738a9ae` |
| Proposed output `mtk_eth_soc.h` (Test34) | `594bb9ed0aa795d05f1ef42e90e28a9fbd2ddb71b92c08e7b063a36b62d4c40c` |

SHA-256 values identify the private research inputs and outputs; they do **not** provide access to those files or establish their redistribution rights.

## Public read-only tool

A source identity checker is now available at [`tools/verify_test34_source.py`](../tools/verify_test34_source.py). It checks two **locally provided** source files against the reported Test32 or Test34 SHA-256 values and never downloads or modifies a kernel tree.

```sh
python3 tools/verify_test34_source.py --source-dir /path/to/local/sources --version test32
# or --version test34
```

A matching digest verifies only the identity of the two supplied files. It does not establish permission to redistribute, compilation success, device safety or completeness of the patch set. The corresponding files are **not** included in this repository.

## Local-only change size inspection

The public [`compare_test34_sources.py`](../tools/compare_test34_sources.py) can verify the pinned Test32/Test34 inputs and print only counts of changed lines; it does **not** emit any source lines or a distributable patch:

```sh
python3 tools/compare_test34_sources.py \\
  --before-dir /path/to/local/test32 \\
  --after-dir /path/to/local/test34
```

This is a preparation step for a separate per-hunk copyright/provenance review. The matching private source files are not supplied or fetched. No downstream user can build the driver from this metadata alone.

## Evidence and limitations

Private Test34 records report: script syntax validation, application to a hash-pinned disposable kernel-source copy, offline static checks and recorded output digests. Complete kernel compilation, KUnit, lockdep, KASAN, fault injection, race stress, and live device execution were **not** established for this candidate. A private source-check CI result also predated the final reviewed edits.

This public note is deliberately **not** a patch, installation guide, endorsement for flashing, or statement of third-party reproducibility.

## Review needed before publishing driver modifications

- Determine the upstream origin, copyright and license of each changed Linux source hunk; keep original license and notices.
- Separate independently authored MT6990 logic from vendor SDK-derived tables or protected binaries.
- Produce a minimal patch against a publicly pinned kernel/OpenWrt baseline, with a clean compile on MT6990 and unaffected other SoCs.
- Test concurrent request submission, modem ownership transitions, retry exhaustion, probe error unwind, driver removal and delayed-work cancellation under relevant debugging facilities.
- Publish sanitized logs with source commits and a truthful PASS/FAIL matrix.

For currently released, reproducible work see [BUILDING.md](../BUILDING.md) and [release readiness](../RELEASE-READINESS.md).
