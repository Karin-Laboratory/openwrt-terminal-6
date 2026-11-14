# 再監査R01〜R05への是正（2026-11-14）

## 修正済み
- **R01 CIカタログ件数:** 76入力・76件pendingに合わせて `docs/STATUS.md` / `docs/RELEASE-GATES.md` / `docs/RIGHTS-REVIEW-20261030.md` を変更。MIT independent-original は65。台帳の権利判定は**pendingのまま**。別PR #194の修正をPR #193へ直接取り込み、二重マージを避ける。
- **R02 fail-open:** `ssh_state_on_p43` を必須bool化。未記入、null、その他の曖昧な入力を `BLOCKED_STORAGE_EVIDENCE` に分類。例とテストにも欠落ケースを追加。
- **R03 GPT最終LBA:** `last_usable_lba` を必須化し、P43終端が最終使用可能領域を越える入力を拒否。これは受領値の矛盾検査であり、生GPTを直接読んだ証明ではない。
- **R04 証拠収集境界:** 判定器はホスト上で匿名化した入力の自己整合だけを確認する。入力を作る実機読取り専用ツールは未実装で、S06はBLOCKED。入力が不正な場合は`BLOCKED_STORAGE_EVIDENCE`、整合しない場合は`BLOCKED`、矛盾なしでも`INSPECT_ONLY_NO_DEVICE_PASS`。いずれも実機PASSではない。
- **R05 非公開v0.4 r4:** 非公開PR #156の `unsplit-preflight.sh` に必須コマンド(`blkid`, `e2fsck`, `tune2fs`)の明示チェックと`needs_recovery`チェックを追加。不在/未確定なら明確なSTOPを返し、`e2fsck -fn` rc=0でもjournalがクリーンとは断定しない。実機のライブラリ/ツール実行は未証明。

## Appendix 4 の取扱い
既存のC号機限定 `bio write` 記録は保持し、歴史的研究記録であって**初見AI向けコマンドではない**と節冒頭に注意を追加。削除・非公開化するかは所有者判断が必要。新規個体のS03はなおBLOCKED。

## 既知の未達
実機S03到達、stock SSH永続化、未分割個体の観測値自動採取、全量バックアップ/電源断復旧、S07適用、S08総合受入は未完成。v0.4 r3の公開状況・対応ソース/通知は未確定。

## 検証境界
ソースと静的テストをPR #193に保存。GitHub Actionsの最終結果はその実行結果が確定するまでPASSと記載しない。非公開r4への変更も、実機で`tune2fs`等が利用可能であることは保証しない。原本データ/認証情報/個体値は公開していない。

**総合判定: NOT READY / 最初のBLOCKED: S03。**
