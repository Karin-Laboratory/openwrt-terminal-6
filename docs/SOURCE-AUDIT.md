# Source migration audit / 公開ソース移行監査

Updated: 2026-10-23. This is a **publication inventory**, not approval to copy any file.

## Provenance boundary

Private working archive: `Karin-Laboratory/SBAT6A-Offline-Archive`. Its README describes original manufacturer snapshots in `originals/`, project-owned work in `src/t6a/`, documentation in `docs/`, and collection/restore tooling in `scripts/`. It explicitly warns not to publish a mirror of proprietary OEM firmware.

**No private-archive implementation files have been approved for import in this audit.** Public original documentation, synthetic DTS, standalone checks and CI workflows already exist; their presence does not establish that any private-archive implementation is redistributable. Read-only inspection of the private repository README does not establish the rights, provenance or necessity of any individual implementation file.

## Candidate source categories

| Candidate | Current publication decision | Required review |
| --- | --- | --- |
| OpenWrt board target/DTS/defconfig patches | HOLD | Identify exact paths, git commits, authorship, upstream provenance, SPDX/license, and device-unique data |
| Ethernet / Wi-Fi / PCIe / 5G patches | HOLD | Technical origin, license notices, blob dependencies, interface IDs, test evidence |
| Existing public verification scripts and CI workflows | PUBLIC, provisional | Original public work already present; inspect authorship, explicit code license, embedded vendor content, signing dependency and internal paths before tagged release |\n| Private-archive build scripts proposed for import | HOLD | Confirm origins, license, secrets, private URLs, embedded vendor content, signing dependency or internal paths |
| Independent, redacted technical notes | HOLD | Remove device serials, IP credentials, extracted vendor code, sensitive partition data |
| OEM original snapshots / factory image / partitions | BLOCK | Proprietary redistribution rights not established |
| Private signing materials and device-specific calibration | BLOCK | Do not copy or make public |
| Privately signed boot images | BLOCK | Signed artifacts and embedded third-party materials require independent rights/safety review |

## Required review record for EACH proposed file

- Private origin path and immutable commit SHA
- Proposed public path and original author
- SHA-256 and content classification (source/patch/script/doc/blob)
- License evidence / required copyright attribution
- Secret, identity and proprietary-binary inspection
- Upstream/derivative code inspection
- External dependencies and build requirements
- Reviewer, decision (APPROVE/HOLD/BLOCK), date
- Public commit/PR and verified test evidence

## Verified public CI evidence\n\n- Publication safety gate run [#39841379271](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39841379271) passed on commit `cc938e99ea569e45ca6f8e400b568800b3e03a2a`. This verifies configured syntax, unit, synthetic-DTS, current-file and reachable-history heuristic checks **at that commit**, not per-file licensing or a distributable kernel.\n- Public repository includes original inspection scripts, tests, synthetic DTS samples and GitHub workflows. The repository-level `LICENSE` covers original documentation only; **MIT has been selected for rights-cleared original project code ([LICENSE-MIT](../LICENSE-MIT)); per-file authorship and derivative-code review still remain outstanding**. Do not assume CC BY 4.0 or GPL applies to those files.\n- No private-archive driver, SDK table, key, firmware or signed image is approved by this audit.\n\n## Findings from initial inspection

- The private README identifies the commercial device as *SoftBank Air Terminal 6 / SBA6D*, but does not prove whether `SBA6D` is the manufacturer's formal board ID.
- The private archive includes manufacturer-derived backups. The original rootfs, partition images and extracted firmware are not publication candidates by default.
- Code search did not yield a reviewable implementation list in this pass. Therefore **no target, DTS, driver, signing or build source has been approved for migration**.

## Next source review

Get a read-only inventory of paths and sizes from the current private development branch, select candidate text patches/scripts, inspect each complete file and license, redact or rewrite where needed, and submit them in small PRs with review evidence. Do not import private git history or use a wholesale mirror.

日本語: 研究用非公開リポジトリから**無審査の一括移管はしません**。公開候補は一件ずつ出所、権利、機密、再現性を審査し、公開履歴には承認済みファイルだけを加えます。
