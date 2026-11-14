# 外部監査（Gemini）指摘の再評価と是正（2026-11-14）

元の外部回答は実機操作・書込みを行わない静的監査であり、GitHub PRも作成していない。今回の修正は既存の [PR #193](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/193) に追加した。

## 監査の工程番号を正す

| 正規ID | 正規工程 | 外部監査表の記載 | 再判定 |
|---|---|---|---|
| S01 | serial_link（UART接続） | 入口JSON読込・エージェント初期化 | **別物**。JSON読込は事前準備 |
| S02 | lk_identify（LK識別） | UART物理接続とシェル識別 | 工程が混在。LK認定はS02 |
| S03 | stock_emergency_identify | 純正B到達 | 具体的なEmergency Shell到達手順欠落のためBLOCKED |
| S04 | stock_ssh_session | 純正B SSH | 一時SSH方法は一般化未完成、BLOCKED |
| S05 | stock_ssh_persistence | 再起動後SSH | 永続化未証明。**slot Bを永続的にデフォルト固定する工程ではない** |
| S06 | partition_readonly_assessment | P43縮小・P44作成 | **読取り専用調査**。書込みはS07 |
| S07 | partition_mutation | P44/ext4/GPT検証 | **承認後の変更工程**。既存P44なら検証してスキップ |
| S08 | final_reboot_acceptance | 最終統合確認 | 依存工程未達のためBLOCKED |

このため外部監査の「S04まで到達可能」「S05が最初のBLOCKED」は、**文書を読んで計画を描けることと実機で到達したことを混同**している。正規の初見公開資料の評価は引き続き「S01/S02 PARTIAL、S03最初のBLOCKED、S03〜S08 BLOCKED、全体 NOT READY」。

## 有効な指摘と今回の是正

1. **起動系統とフォールバック：** 既存 `docs/AB-FALLBACK-RESEARCH.md` に、純正Bへの到達・再起動観測・失敗時の読取り専用分類、承認ゲートを追加。LKとU-Bootを区別し、過去のbootctrl値を新規個体に流用しない。
2. **FW/ロット差：** `docs/TERMINAL6-FW-COMPATIBILITY.json` を追加。歴史的Linux 5.4.238は**観測値のみ**とし、適用可能な実機操作プロファイルは現時点でゼロ。未知情報は `BLOCKED_FW_OR_LAYOUT_UNKNOWN`。
3. **SSH永続化：** `S05`は再起動後の純正B SSH成功が条件。slot Bデフォルト固定の強制は採用しない。原因未確定のwatchdog/fallback現象を、既知の再現手順として記載しない。
4. **パーティション：** 前段の監査是正で、S06の観測項目、S07の個体固有容量・GPT・バックアップ条件、オフライン一次検査器、QEMU実験と実機書込みの分離を実装済み。`--apply`拒否は維持。
5. **初見エージェント：** `agent-entry.json` へ公式工程IDとFW互換性ゲートを明示し、外部監査が混同した採点を再発させないテストを追加。

## 未解決

検証済みS03到達操作、Stock SSHの一般化と永続化、ライブ未分割P43読取り専用取得、対応ランタイムの確認、電源断・復旧つきS07実機書込み、S08完走は**全て未完成**。ソースの公開・GPTバックアップの机上説明だけでは実機の安全性は保証できない。４号機を含む初入手実機のFW/ハード/slotを初期観測するまで書込み用の適用プロファイルを追加しない。

**総合判定：NOT READY（変わらず）。** この是正は資料の整合性・未知個体のSTOP判断を改善するもので、実機の成功証明ではない。
