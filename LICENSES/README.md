# Licensing and provenance policy / 権利監査

This project does **not** claim that all components of an OpenWrt firmware image share one license. OpenWrt, Linux kernel components, userland packages, scripts, firmware blobs and board data may have different licenses and attribution/source-offer obligations.

## License selection for original work

- **MIT**: original project-owned software authored for this repository (Python and shell verification tools, tests, independently authored CI and original experimental device-tree code), where contributors hold the right to license it. See [../LICENSE-MIT](../LICENSE-MIT). A source file may declare `SPDX-License-Identifier: MIT` after its origin and contributor rights are confirmed.
- **CC BY 4.0**: original project documentation under [../LICENSE](../LICENSE), unless otherwise identified.
- **Upstream / third-party / OEM code**: retains its own license and attribution. Importing a patch, Linux/OpenWrt code, vendor driver, SDK table, firmware or generated data does **not** place it under MIT. Review each separately before redistributing.
- **Unverified authorship or provenance**: HOLD. An MIT license file is not proof of rights to any material.

## Mandatory rules

- Record the origin, version, author/copyright notices, SPDX/license and redistribution conditions for every imported file or patch.
- Preserve copyright and license notices, required corresponding source and modification notes.
- Publish source or patches only when rights permit; otherwise provide an independently documented acquisition path, if lawful.
- **Never** include extracted OEM bootloader/kernel partitions, proprietary board calibration or modem firmware, keys, certificates, per-device credentials or identifiers without documented permission and necessity.
- Do not assert `GPL-2.0` for the whole repository before each file's provenance is checked. New original documentation is licensed as specified in [../LICENSE](../LICENSE); original project-owned software uses [MIT](../LICENSE-MIT), subject to rights confirmation; imported code requires explicit per-file/license review.
- Review binary distribution separately from source distribution. An image is blocked until every included binary and its obligations have been cleared.

## Provenance register

| Material | Origin/version | License | Redistribution approved? | Evidence |
| --- | --- | --- | --- | --- |
| Original project documentation | Project contributors | CC BY 4.0 (see LICENSE) | Yes, for original authored text | Commit history |\n| Original project-owned verification scripts, tests and CI | Project contributors, pending per-file authorship confirmation | MIT (LICENSE-MIT) upon confirmation | Conditional; original work only | Public file history and per-file review |\n| Independently authored experimental DTS examples | Project contributors, origin to be reviewed | MIT where original and rights-cleared; third-party snippets retain source licenses | Conditional | Per-file provenance review |
| OpenWrt tree | Not yet imported | Pending per-file review | Not applicable | Pending |
| Board support patches | Not yet imported | Pending author/origin review | Not applicable | Pending |
| Proprietary OEM binary/firmware | Excluded | Not reviewed | NO | Exclusion policy |
| OEM signing keys/certificates | Excluded | Not applicable | NO | Exclusion policy |

An SPDX/SBOM inventory and corresponding source offer should accompany any future release containing compiled code.

日本語: 元ファーム、署名鍵、証明書、個体固有データは無断公開しません。コード・ファームウェア・文書ごとにライセンスを確認し、改変表示・著作権表示・ソース提供などの義務を守ります。

日本語（2026-10-23）: **独自コードはMIT、独自文書はCC BY 4.0**。メーカー由来・OpenWrt/Linux由来のコードはMITへ一括変更せず、元の権利と出所を確認します。
