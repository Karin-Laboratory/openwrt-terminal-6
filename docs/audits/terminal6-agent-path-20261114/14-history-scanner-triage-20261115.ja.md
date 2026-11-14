# 14. 公開履歴スキャナの9件とローカル診断の是正（2026-11-15）

対象: PR #193再監査 `13-reaudit3-20261115.ja.md`。GitHub Actionsの `Safe host tests` が `python3 tools/security/check_publication.py --history` で止まった事実を追跡する。**検査の無効化・無条件の例外登録・履歴の書き換えは行っていない。**

## CIで確認された内容

過去の実行で `Scanned=3136; findings=9`。見つかった9件は、次のファイルと検出種別である。

| ファイル | 種別 | 現時点の評価 |
|---|---|---|
| `config/sbat6-stage/usr/libexec/sba6d/rc14-management.sh` | private network endpoint | 実機管理用の非公開IPか例示値か要精査 |
| `docs/MAINLINE-P26-P44-EXPERIMENTAL-BOOTSTRAP.md` | private network endpoint | 歴史的記述の文脈と公開可否を要精査 |
| `tests/test_air6_first_stage_contract.py` | internal build directory | テスト用固定文字列か要精査 |
| `tests/test_public_rc14_management.py` | private network endpoint | テスト用IPか要精査 |
| `tests/test_publication_history.py` | device login endpoint | 合成履歴テストとして意図された可能性。履歴の該当版要確認 |
| `tests/test_publication_history.py` | private network endpoint | 同上 |
| `tools/air6-rescue-qemu-v0.3/n-unit-split-qemu.sh` | internal build directory | 現行の `/mnt/p43`, `/mnt/p44` はQEMUゲストのマウント先として使用されている。**歴史に残る他の版も確認が必要** |
| `tools/boot/air6_first_stage.sh` | internal build directory | 実行環境に依存する固定パスか要精査 |
| `tools/security/check_publication.py` | private network endpoint | 検査器自身がRFC1918の判定正規表現を保持。ソースそのものが誤検出を誘発する可能性 |

**注意:** 9件は「秘密が漏えいした確証」でも「無害の証明」でもない。履歴スキャンは削除済みファイル、過去のコミット、当時のブランチ上の内容も調べるため、現在のツリーからファイルを移動しても過去の検出は消えない。履歴を書き換えることは既存公開コミットの参照を破壊し得る。

## 是正

- `check_publication.py` の履歴監査例外を固定の非機密コードに分類。浅いクローンなら `SHALLOW_CLONE_FETCH_FULL_HISTORY`、非コミット参照なら `NON_COMMIT_REF_UNSUPPORTED`、replace refなら `REPLACE_REF_UNSUPPORTED` 等を返す。
- 経路・ref名・元の例外内容をそのまま表示しない。**ValueErrorをPASS扱いにするのではなく従来どおりexit 2でBLOCKED**。
- 検査のルール・対象コミット・対象リポジトリ・閾値は変更しない。既存の9件は検出され続ける想定。
- テストは合成履歴に対して分類コードと秘匿性を確認する。

## 9件の処理方針

1. 歴史内の該当コミット・ブロブとパターン部分だけを個別確認。秘密値はPR・Issue・CIログに転載しない。
2. 単なるテスト用構文であれば、**正規表現の構造上の誤検出**として診断を狭める。生きているIP/認証情報なら当該資格情報のローテーションやアクセス制限等を優先する。
3. 例外が不可避なら、**ファイルパスだけでなく内容ハッシュ・検出カテゴリ・適用理由を固定**し、将来の変更は再検査される設計を別途レビューする。今のPRでは例外を追加していない。
4. 公開履歴に既に含まれる内容は、後日の最新ファイル修正だけでは秘匿化できない。

## 判定

初見AIワークフロー自体は依然 **NOT READY（最初のBLOCKED S03）**。Onboarding Docs QAの結果と、公開履歴スキャナの全項目PASSを混同しない。実機・UART・eMMC操作は未実施。
