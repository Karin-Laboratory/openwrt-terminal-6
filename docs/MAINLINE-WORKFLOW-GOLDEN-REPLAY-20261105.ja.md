# 公開本線 p25/p26：全履歴からの最小手戻り・自動再現手順

> **参照先の役割:** この文書（[PR #128](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/128)）は固定時点の公開Actions全履歴と最小再現手順の**正本**。最新の作業台帳、既知エラーと公開ドキュメントの入口は[PR #129](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/129)の[証拠・作業索引](https://github.com/Karin-Laboratory/openwrt-terminal-6/blob/docs/evidence-workflow-index-20261105/docs/EVIDENCE-WORKFLOW-INDEX-20261105.md)を参照する。履歴JSONの複製やcron変更は行わない。両PRは未マージの独立ブランチ。

更新: 2026-11-05 JST / 対象: PUBLIC Karin-Laboratory/openwrt-terminal-6
正規の完成条件: [MAINLINE-P25-P26-POLICY.md](MAINLINE-P25-P26-POLICY.md)。
**本記録は既存目標を変更しない履歴監査と実行設計。新しい完成イメージ、実機PASS、署名、公開配布を実行・承認した証拠ではない。**

## 0. 最終到達点（変更なし）

- **p25**: 適法に再配布できるソースから再現製造する、完成した**署名前 unsigned boot_a 32 MiB**。機器固有署名器・鍵・stock dumpを公開側へ持ち込まない。
- **p26**: 同じく公開可能ソース由来の**完成OpenWrt rootfs_a 128 MiB**。実パッケージ、内容、メタデータ、全量SHA、末尾ゼロパディングを別プロセスで検証する。
- **再現性**: source/config/patch/package closure/toolchainのrevisionを固定し、各入力・出力のハッシュとreadback receiptを残す。
- **到達と混同しない**: QEMU virt起動、host-onlyテスト、source-only CI、make defconfigだけ、実パッケージ一部のコンパイル、仮rootfs、FDTパーサだけのPASSは完成ではない。署名済み一般向けflashable releaseは別審査。

## 1. GitHub Actions全件履歴（固定時点）

[全実行の機械可読台帳](evidence/WORKFLOW-RUNS-SNAPSHOT-20261105.json)。
GitHub Actions APIで **2026-11-05 10:09:59 UTC（19:09:59 JST）までの648実行**を全ページ取得。run_id、workflow path、branch、head SHA、event、timestamp、conclusionを保存した。成功313、失敗281、取消54。

| workflow path | 実行 | 成功 | 失敗 | 取消 | 意味 |
| --- | ---: | ---: | ---: | ---: | --- |
| .github/workflows/source-only-ci.yml | 424 | 206 | 218 | 0 | host/事前検査。完成p25/p26の証明ではない |
| .github/workflows/arm64-image-build.yml | 111 | 57 | 10 | 44 | kernel Image、初期procd、DTB候補。boot-v2完成ではない |
| .github/workflows/mt6990-native-subtarget.yml | 77 | 27 | 50 | 0 | 上流OpenWrt/実パッケージ。完成p26受入は別 |
| .github/workflows/p26-packer-tests.yml | 26 | 23 | 3 | 0 | PR #127の合成pack/extract。main未マージ |
| .github/workflows/trusted-selfhost-build.yml | 10 | 0 | 0 | 10 | 成功の証拠なし。製造PASSとは認定しない |

ActionsのSUCCESSは実イメージ製造成功数ではない。runごとのソースYAMLは**各runのhead_shaで取得**し、現行mainのYAMLで過去runの契約を説明しない。

## 2. 既存コードを最優先で使う

- **ImageとDTB:** [arm64-image-build.yml](../.github/workflows/arm64-image-build.yml) と [mt6990-native-subtarget.yml](../.github/workflows/mt6990-native-subtarget.yml)。新しいkernel/rootfs製造器を立ち上げず、現在の成果物に対する差分だけを加える。
- **p26既存packer:** [PR #127](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/127) の tools/build/pack_p26_rootfs.py、tests/test_pack_p26_rootfs.py、docs/P26-ROOTFS-MANUFACTURE.md。現状はsynthetic PASS、**本物のp26は未製造**。
- **wpad:** [PR #118](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/118) は別HEAD。#127のnative CIのSUCCESSは#118の変更の実ビルド証明ではない。LAN-onlyを先に完成してもよいが、最終radio対応と混同しない。
- **p25先行ゲート:** [PR #120](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/120)〜[#126](https://github.com/Karin-Laboratory/openwrt-terminal-6/pull/126)のNETSYS/SGMII/PLL/DTB/FDT構造検証。必要なものだけ統合し、source-onlyテストを追加すること自体を最終成果としない。
- PRIVATE実験の成功はボード構成と挙動の**事実**として参照できる。しかしprivate原本、個体EEPROM、stock/vendorバイト、秘密鍵・署名器は公開のビルド入力に混入させない。

## 3. 最短の自動実行DAG（完成前に必ずSTOP条件を判定）

~~~text
Read main / active PRs / historic run-id + SHA / prior acceptance receipts
  -> choose ONE unblocked changed layer; preserve all verified unchanged bytes
  -> pin exact source, package list, config, compiler, tool version

P26 track                           P25 track
  same-run OpenWrt package/install    reuse native ARM64 Image + genuine Air6 DTB
  verify real stage and provenance    verify kernel/DTB/CPIO handoff
  build one 128MiB unsigned p26       use accepted p26 digest when available
  separate-process unsquashfs         pack one 32MiB unsigned boot-v2
  full metadata/padding/SHA check     independent header/FDT/marker/size/SHA
  -> p26 ACCEPTED or BLOCKED          -> p25 ACCEPTED or BLOCKED

  -> private or ephemeral immutable receipts; public sanitized facts only
  -> STOP: no signing, device/slot operation, firmware upload or distribution
~~~

**DAGは「今後接続する設計」であり、現行PR #127とp25が同一workflowで完走したという主張ではない。**

### 3-A. p26: 人間の成果物コピーをなくす

1. **一つのrun/checkout**から、上流OpenWrt commit、実際に利用したfeedsのSHA、最終config、make package/installログ、実パッケージ一覧、rootfs treeを生成する。別PRの緑のCIを混合しない。手書きの架空source receiptを拒否。
2. package/installが完了した**同じjob**で、source-built実rootfsのdirectoryを次のpackerへ渡す。現在の一時rootfs-stage.tar.gzは別runへ自動継承されない。さらにtarの --owner=0 --group=0 は元のnumeric UID/GIDを喪失し得るため、製造入力は元treeに直接つなぐか、所有権・リンク・xattrを保持する別の受入方式を実証して使う。
3. #127の既存packerを使用し**128 MiB = 134,217,728 bytes**のunsigned p26を一度だけ製造する。現実装の -no-xattrs と原本忠実性の不足は必要な最小修正とテストで解消する。binのActions artifact、Release、shared cacheアップロードは禁止。
4. producerとは**別プロセス**でunsquashfsし、全file/list/mode/numeric UID-GID/symlink/xattr/capability（必要な場合）と元のpackage treeを比較し、パディングと128MiB全量SHAを検証する。変更がない失敗runの再試行を繰り返さない。
5. 設定のないrootの安全性、公開鍵SSH初回導入、未設定無線の自動起動防止を維持する。LAN-onlyイメージができてもWi-Fiドライバ/firmwareまで完成とは主張しない。

### 3-B. p25: 既存Imageから32MiB完成体へ

1. 既存ARM64 Image、procd CPIO、Air6 DTB候補の**同一kernel config・toolchain**を固定。QEMU virtで動いたImageをAir6実起動の証明に転用しない。
2. #120〜#126から必要なreal DTB、NETSYS、MT7531、SGMII1、PCS1、clock/genpd/Kconfigだけを取り込む。FDT構造の修正ならp26再製造は不要。
3. 公開可能な仕様と独立の自作コードだけで、Android boot-v2形式の**unsigned 32MiB packer**と別プロセス検証を完成する。private署名済みboot image、OEM vendorセクション、署名領域のprivate内容をコピーしない。
4. p26 SHAを初期CPIOのmarkerへ格納する設計なら、新p26の**全量SHA確定後だけ**CPIO→Image→p25を再束縛する。p26の内容が不変ならp26は絶対に再packしない。新p26 SHAが未確定なら、p25を「完成ペア」と呼ばず独立にできる構造QAとコード実装だけ進める。
5. 最終の独立32MiB全量readback・section/FDT/marker照合が終わるまでP25_BUILD=BLOCKEDのまま。署名と実機操作は本線に含めない。

## 4. 差分ごとの最小再製造

| 変化 | 固定して再使用 | 再実行するもの |
| --- | --- | --- |
| docs / 権利説明だけ | Image, p25, p26の既存SHA | docs QAのみ |
| p26 package/config/UID-GIDのみ | kernel Image, genuine DTB | p26→独立検証→必要時だけCPIO/p25 marker |
| p25 kernel/DTB/headerのみ | 受入済みp26のfull SHA | p25だけ再製造と独立検証 |
| Wi-Fi modules | unchanged source-built base rootfs | 同一Kbuild ABI/Module.symvers/compiler/ELF CRCを検証し該当kmod/p26層だけ |
| CI失敗 | 不変の正本と成功receipt | 失敗したjobの最初の原因を修正。全workflow再起動禁止 |
| 新証拠のないBLOCKED | 全成功材料 | 同じpreflightを繰り返さず、欠落する実物1件を特定 |

## 5. 繰り返さない失敗パターン

- PR #118と#127の**cross-head混同**：単一run/checkout/manifestのSHAまで確認。
- hosted CIの**一時rootfs消失**：別runへの人手転送ではなく、同じjobで連続してpack/verify。
- **UID/GID・xattr・capability欠落**：見かけのtar/SquashFS成功を拒否、別プロセスで全tree確認。
- **source-only/QEMU緑**と実物PASSの混同：receiptに実行環境と検査範囲を記録。
- **不用意なkernel/driver再発明**、NR/6GHz/MLOへの拡張、追加の全体build、テスト件数の増殖。
- source catalogのrights_review=pendingを**通常のローカル開発すべての停止理由にはしない**。ただし公開コミット物および配布画像に適用される法令・OSS義務を守る。

## 6. 人間介入の最小境界

public側のソース実装、隔離ビルド、QA、unsigned画像の一時的製造、独立受入、sanitized receipt記録はCI/agentで連続実行する設計。TinyFish・ブラウザ手作業は不要。物理flash、slot変更、署名、秘密入力登録、一般配布は**別の権限と承認**が必要で、ここでは自動化しない。「人間ゼロ」は運用全体ではなく、入力が揃った後のエンジニアリングjob内の意味に限る。

## 7. 毎回の開発agentへの実行指示

main、PR #127/#118、p25関連#120〜#126、最新Actions、前回の未着手事項を先に確認する。未解決のP25/P26ゲート**1つだけ**を選び、既存PRでコード修正→必要テスト→commitまで行う。状況説明や同じ調査を目的に別PRを作らない。状態は次の形に限定する。

~~~text
TARGET: PUBLIC_P25 / PUBLIC_P26
PIN: exact source HEAD, config, toolchain, receipt
REUSED: unchanged byte digests
ONE_CHANGE: changed source file(s) and why
TEST: verified command, Actions run, conclusion / NOT_RUN
REAL_IMAGE: exact size, full SHA, independent readback / BLOCKED
ONE_BLOCKER: one concrete missing input or failed verification
~~~

「絶対に失敗しない」ことは保証できない。実行順・入力・結果を固定し、**最初の確定した欠落でfail closed、成功層は再実行しない**方式で失敗と手戻りを極小化する。

## 8. 2026-11-05 19:56 JST 追加実ジョブログ診断：リビルドせず台帳を直す

最新PR #127ブランチのActions [#42014814965](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42014814965) と [#42014814721](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42014814721) はFAIL。前者の job `127202567173`、後者の job `127202566372` の**生ログ**を個別取得して確認した。どちらも最初の停止原因は `python3 tools/build/verify_source_catalog.py` で、実ログは次の2点。

- `SOURCE CATALOG BLOCKED: input#43: source bytes differ from catalog identity`
- `SOURCE CATALOG BLOCKED: uncatalogued source/test: tools/build/verify_p26_partition.py`

この run の `native-defconfig` の10件の Python unit tests はPASSした後にcatalogで停止し、上流OpenWrt checkout/`make defconfig` の実行ステップは**SKIPPED**、続く native package-compile job も**SKIPPED**。公開source CIではEthernet/FDTなど既存host checksはPASSし、同じcatalogで停止した。一方 [#42014814904](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42014814904) のp26 synthetic packer testsはSUCCESS。**最新headの全3workflow PASSや実p26製造PASSとは報告しない。**

**最短の一手：** #127の現在HEADで、(1) input#43のパス・記録SHAと現行git blobを正確に照合し、(2) `verify_p26_partition.py` の出典・SPDX/権利を確認してcatalog/関連inventoryへ登録し、(3) **catalog verifier単独**で再実行してから該当するCIだけ通す。正当なソース変更を伴わない帳尻合わせや権利の架空承認は禁止。その後、同じjob内の実OpenWrt package/install → p26 packer → 別プロセスの全量検証へ進む。これは**新しい全kernel / 221 APK再製造の指示ではない**。

この診断は過去全件のmetadata索引とは別に、上記2失敗jobの実ログを精査した追補。最新runは凍結索引のcutoff後であるため、648件の確定総数に加算しない。失敗のない運用は保証できず、原因を1点ずつ固定して再実行範囲を最小化する。
