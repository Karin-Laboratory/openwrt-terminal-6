# Alpha 3 contributor entry kit / 開発参加ガイド

**Target:** SoftBank Air Terminal 6 (A775 / MediaTek MT6990). This is **source-only Developer Preview**, not an installable OpenWrt release. Start with the [single current status page](ALPHA3-DEVELOPER-PREVIEW-STATUS.md) and [existing contribution rules](../CONTRIBUTING.md).

**対象:** SoftBank Air ターミナル6（A775 / MT6990）。一般利用向けファームウェアではありません。最初に[開発状況の正本](ALPHA3-DEVELOPER-PREVIEW-STATUS.md)と[既存CONTRIBUTING](../CONTRIBUTING.md)をご確認ください。

## Choose a route / 参加の3つの入口

### A. Read-only reviewer / ソースレビュー（今すぐ参加可能）

Hardware not required. Pick one narrow, publicly visible file and comment on a reproducible issue: [Air6 DTS](../board/mt6990-air-terminal-6.dts), [DTS evidence](../board/DTS-RECONSTRUCTION-20261029.md), [NETSYS/SGMII1 candidate](NETSYS-SGMII1-BOOT-CANDIDATE.md), source patches, userspace or [build contract](BUILD-CONTRACT.md). Useful reviews include DT binding mismatches, assumptions about MT6990 clock/reset/PHY, incorrect service dependencies and source attribution. Mark hypotheses as hypotheses.

実機なしでOK。公開DTS、kernel patch、userspace、ビルド手順から小さな範囲を選び、具体的なファイル位置と根拠を共有してください。初心者はリンク切れ、用語、再現手順、ドキュメントの矛盾チェックから参加できます。

### B. QEMU / CI contributor / QEMU・自動テスト（今すぐ参加可能）

Use only publicly included files. Good entry-level work: check documentation links, run source-catalog validation, improve hardware-free tests, help maintain QEMU service-process assertions, or review the native build/PR logs. The [build contract](BUILD-CONTRACT.md) and [tests directory](../tests/) are the starting point. For example, from a normal clone on a developer-owned computer:

```sh
python3 tools/build/verify_source_catalog.py
```

This verifies tracked source **identity and schema only**; it is not a kernel compile, proof of C hardware boot, or permission to redistribute firmware. Read the command implementation and prerequisites first. Do not run private signers, Flash/A-B commands, proprietary SDK tools or workflows using privileged home/self-hosted runners. For native QEMU background see [merged PR #115](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/115) and [#116](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/116); report the actual commit, command and outcome, including failures, before claiming any PASS. Open Draft [#118](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/118) is a source build integration, not proof of Wi-Fi operation.

### C. Hardware owner / 機材所有者（既存・安全な情報共有から参加可能）

Useful today: **previously captured, redacted** publicly shareable boot/kernel-version facts, board topology observations, PHY/PCS linkage notes, and high-level result comparisons. Use [Discussions #50](https://github.com/Karin-Laboratory/openwrt-terminal-6/discussions/50) for introductions and general interest, while recognizing that the older thread discusses experimental installation: **it is not a general release promise or approval to flash**.

実機所有者は、既に採取済みの情報から、個体識別情報や通信契約情報を伏せた範囲を共有できます。新たなroot取得、flash、slot切替、UART送信、起動試験は参加条件ではありません。将来そうした操作が必要でも、対象機、危険性、復旧条件、所有者の明示承認を**別途**確認します。

## Issue or Discussion? / 投稿先

- **Issues:** one specific, reproducible public-source defect or tightly scoped request. Search existing [#4 native build](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4), [#20 Ethernet](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), [#21 userspace](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21), [#22 LTE](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22), [#74 AP-first](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74) first.
- **Discussions #50:** newcomer questions, non-sensitive historical device experiences and collaboration interests. Please avoid publicly uploading confidential logs or asking for prohibited firmware/material.
- **Pull Requests:** source/documentation/test changes with a narrow diff and actual reproducibility notes. Review [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md) first.

## Minimal bug report / 最小報告テンプレート

Copy these fields into a new Issue, omitting anything sensitive:

```text
Title / タイトル:
Scope / 対象: public source | generic QEMU | historical B observation
Commit or PR / コミット・PR:
File and line (if source bug) / ファイルと行:
Expected / 期待値:
Observed / 実際:
Reproduction command (host-only, safe) / 安全な再現コマンド:
Test outcome and date / テスト結果・日付:
Evidence level / 実証レベル: 1 / 2 / 3 / 4
Sensitive information removed? / 機密を除去したか: YES
Not tested / 未確認:
```

Do not classify a historical B success as current C hardware or a generic QEMU result as Air6 network traffic. An unexecuted test is **NOT RUN**, not PASS.

## Safe evidence / 安全な実機証拠

Before sharing, first record *what is already available*, when and on which controlled revision, and whether it came from B hardware, C offline bytes, generic QEMU or C hardware. Publish only non-sensitive aggregate counts, explicitly permission-cleared snippets, public source SHAs and test status. Do **not** publish MAC/serial/IMEI/IMSI, SIM/operator/customer identifiers, GPS/location, Wi-Fi credentials, keys, board-unique calibration/NV, original OEM partitions, private code, exploit sequences, home paths, remote network endpoints or full private UART/MMIO traces. Prefer a summary that another developer can critique without raw unique bytes. Disclose suspected vulnerabilities privately via [SECURITY.md](../SECURITY.md).

原本ファームウェア、個体特定情報、署名鍵、非公開取得方法、機密ログはGitHubに置かないでください。必要なら公開前に権利・安全性を確認し、独立した私有の証拠と公開集計を分離します。

## Roadmap / 今後の優先順位

1. **Now:** public review and hardware-free CI; repeatable source-only build inputs, native OpenWrt userspace/procd/ubus/netifd QEMU, upstream-friendly DTS/kernel work. [#4](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/4), [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21)
2. **Hardware research, separately approved:** actual C Linux→/init→procd evidence, then Linux/SGMII1/NETSYS/MT7531 Ethernet, SSH provisioning, 2.4/5 GHz AP and persistence/recovery. [#20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20), [#74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74)
3. **Later feature tracks:** independently rebuild historical LTE Stage10 and research NR/IPv6, 6 GHz, Wi-Fi 7, EasyMesh as separate optional milestones, not Alpha 3 acceptance prerequisites. [#22](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/22)
4. **Separate product gate:** limited authorized hardware alpha, then reproducible and safe Public Beta, only after [rights/security/recovery gates](RELEASE-GATES.md) pass.

**English summary:** Review source or QEMU today without buying hardware. Hardware owners can contribute safely redacted observations, but installation and signed binaries are not offered. Every result needs provenance and a clear evidence level. This is an independent community effort, not an official vendor release.
