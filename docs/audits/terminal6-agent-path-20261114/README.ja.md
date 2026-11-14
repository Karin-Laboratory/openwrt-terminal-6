# Terminal 6 初見AI導線 完走可能性監査（オフライン）— 2026-11-14

**種別:** オフライン監査（机上・文書・実装読解）。**実機・UART・SSH・eMMC・ファームウェアへの操作は一切行っていない。** `--apply` の拒否は解除しておらず、書込みも実行していない。

## 最終判定

> # NOT READY
>
> **初見AIが `agent-entry.json` と公開資料だけで S08 まで完走することはできない。**
> ただし、**安全停止の設計は良好**（誤って書込みへ進む経路は見つからなかった）。

| 質問 | 回答 |
|---|---|
| 公開資料だけで到達できる最終工程 | **S02（LK識別）**。S03 は「識別基準」までは読めるが、そこへ入る手順がない |
| 最初に BLOCKED になる工程 | **S03（純正 slot B Emergency Shell への到達）** |
| 工程別判定 | S01 PARTIAL / S02 PARTIAL / S03 BLOCKED / S04 BLOCKED / S05 BLOCKED / S06 BLOCKED / S07 BLOCKED / S08 BLOCKED（**PASS はなし**） |
| 実機で証明済みの工程 | なし（公開側の根拠はすべて研究個体の部分観測・QEMU・文書） |

> 「安全に止まる」ことと「完走できる」ことは別である。入口JSONは前者を満たしているが、後者に必要な実装・手順が不足している。

## 監査対象（固定した版）

| 対象 | 版 |
|---|---|
| 公開 `Karin-Laboratory/openwrt-terminal-6` | main `168a05ba6b66d3d1053e358530ba6b2f76924637`（PR #186 マージ後） |
| 非公開 `SBAT6A-Offline-Archive`（照合用） | main `dbc0e7db…`、PR #150 ブランチ `39e4e350e6a6`、PR #155 の記載、Issue #116 と C号機 slot B 復旧ブランチ |

非公開資料は**監査の根拠としてのみ**使用した。初見エージェントがアクセスできる前提にはしていない。以降の文書は、公開してよい粒度（結論・判定・不足点）だけを記載している。

## 成果物

| # | ファイル | 内容 |
|---|---|---|
| 1 | [01-stage-audit-table.ja.md](01-stage-audit-table.ja.md) | S01〜S08 工程別監査表 |
| 2 | [02-novice-agent-simulation.ja.md](02-novice-agent-simulation.ja.md) | 初見AIの完走シミュレーション |
| 3 | [03-blockers-and-missing-assets.ja.md](03-blockers-and-missing-assets.ja.md) | BLOCKED要因と不足資料・実装の一覧 |
| 4 | [04-public-private-consistency.ja.md](04-public-private-consistency.ja.md) | 公開・非公開記録の整合性監査 |
| 5 | [05-improvement-roadmap.ja.md](05-improvement-roadmap.ja.md) | 改善ロードマップ（A/B/C/D分類） |
| — | [audit-result.json](audit-result.json) | 上記の機械可読サマリ |

## 特に重要な発見（上位5件）

1. **S03 に入る公開手順がない。** 識別基準（`bootslot=b`・PID1=`sh`・AArch64）はあるが、Emergency Shell へ入る手順と slot B へ安全に切り替える手順が公開側にない。非公開側の唯一の記録は、ブート制御領域への生書込みを伴う履歴であり、`success` フラグの誤設定で自動復帰が効かなくなった教訓が残っている。
2. **v0.4 r3 の preflight は未分割個体を拒否する設計。** 実装は P44 の存在と正確なセクタ数（P43=927680、P44=5242816）を要求し、未分割なら `P44_IDENTITY_UNKNOWN` で終了する。**未分割個体を読み取り専用で調べる実装はどこにもない**（S06 が実装上成立しない）。さらに非公開側の README はこの挙動を逆に記述している（→ 04 の X02）。
3. **v0.4 のランタイムは `resize2fs` と `sgdisk` しか含まない。** QEMU の分割アルゴリズムと preflight は `e2fsck`・`mkfs.ext4`・`blkid` も必要とするが、純正 Emergency Shell にそれらがあるかは未確認（ELF実行は NOT_TESTED）。
4. **純正SSHの永続化は2種類の個体固有手順が非公開にあるだけ。** 片方は P43 内にシードを置くため、**S05 の永続化と S07 の P43 縮小が衝突し得る**が、公開資料はこの依存に触れていない。もう片方は電源再投入後に回帰した履歴があり、原因は未確定。
5. **v0.4 r3 の公開状態に矛盾がある。** 入口JSONは「非公開候補」と述べる一方、非公開側のリリースメモには公開添付URLと公開 Discussion での告知が書かれている。権利（同梱 GPL バイナリの対応ソース・通知は未整理）に関わるため、所有者による確認が必要。

## 事実の区分（この監査の読み方）

| 区分 | 意味 |
|---|---|
| OBSERVED_PUBLIC | 公開リポジトリのファイル内容を直接読んで確認した |
| OBSERVED_PRIVATE | 非公開アーカイブの記録を直接読んで確認した（実機の再観測ではない） |
| VERIFIED_LOCAL | この監査で実際に実行して確認した（ホスト上の静的テストのみ） |
| DERIVED | 上記から計算・推論した値（実測ではない） |
| UNVERIFIED | 確認できなかった |

この監査で実行したのは、公開リポジトリの `tools/qa/test_onboarding_contract.py`（結果: `AGENT_ENTRY_OFFLINE_AUDIT_PASS` / `ONBOARDING_DOCS_JSON_CONSISTENCY_PASS`）のみ。**これは静的な文書整合の検査であり、デバイス動作の証明ではない。**

## 公開してはいけない情報について

この監査文書には、秘密鍵・認証情報・個体固有値（シリアル・MAC・IP・ホスト鍵・SIM情報）・OEM原本・内部LKコマンド手順・ブート制御の生書込み位置・初期アクセスの具体手段を**含めていない**。非公開側にそれらを必要とする手順がある場合は「存在する」ことと分類だけを示した。

## 監査後の是正（追記）

- [06 是正進捗](06-remediation-progress.ja.md): 公開・非公開の修正、未解決項目
- [07 オフラインP43判定器の使い方](07-offline-inspector-usage.ja.md)と[合成入力JSON](p43-synthetic.example.json): 実機を操作しない一次評価

監査時点の`audit-result.json`は**当初のNOT READY判定のスナップショット**として保持している。今回の是正で実機S03〜S08をPASSにしたわけではない。

- [08 外部AI監査の再評価・訂正](08-gemini-review-remediation.ja.md): 公式工程名への照合、A/B・FW差分の安全ゲートを追加

- [09 修正版の再監査](09-reaudit-20261114.ja.md): 修正版 head 28b0f479 を再監査。判定は NOT READY のまま（S02 まで到達、最初の BLOCKED は S03）
- [11 修正版の再監査（第2回）](11-reaudit2-20261114.ja.md): head 153b04f3。判定は NOT READY のまま（S02 まで到達、最初の BLOCKED は S03）

- [12 第3回再監査の是正](12-reaudit3-remediation.ja.md): CI checkout固定、バックアップGPT境界、証跡の型・必須条件を修正
