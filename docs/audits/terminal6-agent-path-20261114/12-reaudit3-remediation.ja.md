# 第3回再監査への是正（2026-11-15）

対象: PR #193 / 監査報告 `11-reaudit2-20261114.ja.md`。実機、UART、SSH、eMMC、`--apply`は未操作。

| 指摘 | 是正結果 |
|---|---|
| N01 checkout未固定 | PR #192の`actions/checkout@11bd719...`固定を#193へ直接取り込み。#192はstacked PRとして別途整理 |
| N02バックアップGPT境界 | `gpt_partition_entry_sectors`必須化。一次/二次GPTヘッダ・エントリ配列の占有セクタを考慮して`last_usable_lba`とP43を判定。単純な`disk-1`は拒否 |
| N03出力形式の不統一 | 不正型/欠落/矛盾/予備判定のすべてに`device_success=false`と`writes_performed=false` |
| N04 r4診断情報 | 本公開PRのホスト側判定器に必要なフィールド・合成入力例を明記。ただしr4自体の実機診断収集・最小縮小量の抽出は依然未実装 |
| N05バックアップの自己申告 | `backup_evidence`と`recovery_evidence`（非公開受領書参照・確認方法・日時）を必須化。空欄は拒否。これでも**自己申告の真正性は検証できない**ので`evidence_attestation_only=true`として実機作業には別途独立確認を要求 |

- 固定値 `34` セクタを強制せずGPTエントリ配列のセクタ数を入力とする。ヘッダや配列情報自体の採取は別工程で、偽りの入力は受理され得るため`INSPECT_ONLY_NO_DEVICE_PASS`のまま。
- 受領書参照はローカル保管。秘密情報や個体固有識別子を公開しない。
- Appendix 4 C号機 `bio write`例は歴史記録として警告を維持し、一般化せず実行禁止。所有者の削除・公開範囲判断は未決。
- r3配布物の公開状況、非公開r4での`e2fsck`診断出力、S03以降の一般化・実機完走はいずれも未完成。

**総合判定は NOT READY / 最初のBLOCKED S03のまま**。CI最終結果は別途確認する。
