# SoftBank Air Terminal 6 関連GitHubリポジトリ横断調査（2026-11-21）

> **調査日**: 2026-11-21 JST。公開GitHubリポジトリ名・説明・README・一部ソース、およびGitHub APIのリポジトリ/Fork情報を確認した机上調査。**第三者の実機動作を本プロジェクトが追試したものではない。** 数値・各リポジトリの状態は調査時点のスナップショットであり、時間経過で変わる。この記事は調査メモで、他者のコード・バイナリを本リポジトリへ取り込んだものではない。

## 検索方法・対象

- リポジトリ名/説明文のGitHub検索: `SBA6`, `SBA6D`, `SBAT6`, `air6`, `sbair6`, `sbair`, `softbank-air`, `SoftBank Air Terminal 6`, `SoftBank Air 6`, `Airターミナル6`, `terminal6`, `terminal-6`, `A775`, `RG620T`, `RG620T-SBK`, `MT6990`, `MT7990`, `T830`, `evb6990`, `KNOS`, `CVE-2026-101107` など。コード検索も併用した。
- 名前に `SBA6` を含む無関係な授業課題や、`Air602` など別製品は除外。**Forkは独立した開発元として数えない。** デフォルトブランチのコード検索に引っかからないプロジェクトや非公開リポジトリは網羅できない。
- 主要リポジトリのメタデータとREADMEを取得し、その時点のブランチ先頭のコミットSHAを控えた。**実際にビルド、署名、実機書込み、ネットワーク試験は実施していない。**

## 1. 主要な独立系リポジトリ

| 系列・固定コミット | 主題 | README等の主張・観測範囲 | 本調査での評価 |
| --- | --- | --- | --- |
| [rinrin-aismirin/sbair6-openwrt-builder](https://github.com/rinrin-aismirin/sbair6-openwrt-builder/tree/ba6eff830ec27b7db8287cc7cb6e8d16b4de7e9b) | OpenWrt SNAPSHOT構築、A/B運用、復旧 | READMEは**1台の実機**で両LAN 1Gbps、5/6GHzのMLO接続、USB3、LED、スロット復帰、設定保持更新、純正バックアップ/復元を試したと記載 | **最優先で技術比較**。報告の存在は確認、試験ログ・条件の独立追試は未実施 |
| [rinrin-aismirin/openwrt（air6ブランチ）](https://github.com/rinrin-aismirin/openwrt/tree/67934be6ac3ab0ad2013d9c840e5644afae04ac1) | 上記ビルダーの対応OpenWrtソース | OpenWrt本家からのFork。上記と別の独立した実機移植成功例として**重複計上しない** | ドライバ/DTS・MLOの実装差分を調べる対象 |
| [hchyhchyxh/openwrt-air6](https://github.com/hchyhchyxh/openwrt-air6/tree/7377abbb5106eeebefcfff6c38cdbff4e4b42af1) | MT6990/T830・MT7990対応OpenWrtソースと独自CPE管理画面 | READMEによればLinux 6.18.51系、China Telecom 5G n78接続の**非公開基準環境**の記録あり。一方、公開版から無線管理用 `mtwifi-cfg-tool`、署名関係等が除外され、公開縮小ツリー単独のクリーンビルド/実機適用は未検証 | 大規模な先行資産候補。ただし**公開ツリーと非公開基準環境の成果を混同しない** |
| [hchyhchyxh/air6-modem](https://github.com/hchyhchyxh/air6-modem/tree/4992c7280019c7b2b63aee3c02f2dfa822bd59ea) | P54モデムのバンドメタデータ研究 | LTE 12 + NR 13 = 25種類のバンド項目を目標。公開版は未署名の研究イメージ製造で、作者自身が実機未検証・CA非対応・署名/認可機構を含まないと明示 | モデムメタデータ・整合性検証の資料。実用バンド解放の証拠とはしない |
| [soralis0912/luci-app-sbair-modem](https://github.com/soralis0912/luci-app-sbair-modem/tree/ae25c3eee4de89f0167d510d69ba563a323e30fb) | 純正KNOS/OpenWrt 21.02系向けモデム管理LuCIアプリ | READMEは `/dev/adb_atci_socket`、Goバックエンド、eSIM・物理SIM、SIMロック、APN、SMS、電波状態・IMS等を説明 | モデム制御方式の設計資料。Debian/新OpenWrtへはAPI/ABIや権限を独立検証 |
| [soralis0912/SBA6D-OSS](https://github.com/soralis0912/SBA6D-OSS/tree/c7508cb46a6f51c9873604d6a94c94d5c433a8b6) | 純正系GPL/LGPLソース開示資料 | `README.txt` はOpenWrt 21.02.7、Linux 5.4.238、`gem6xxx/evb6990_cpe_mt7990_emmc`、KNOSパッチを列挙。372パッケージ中282が開示対象と記載。**ベンダー固有部分・署名材料は含まない** | 純正構造の調査材料。完全なSDK/実機再現用ソースとは扱わない |
| [code-raisan/CVE-2026-101107-PoC-SBA6RCE-SAFETY](https://github.com/code-raisan/CVE-2026-101107-PoC-SBA6RCE-SAFETY/tree/e3c565be586eba10ef5295812b773e01ef59ca9a) | [JVN#64740097](https://jvn.jp/jp/JVN64740097/) 関連の認証不要RCEの公開PoC | READMEはFW 1.01.52での認証不要の確認を主張、検証用の情報取得に限定 | **セキュリティ参考資料のみ**。本一覧では攻撃の再現手順や実行可能なペイロードを転載しない |
| [13179415360/openwrt-mt6990-lg6851f](https://github.com/13179415360/openwrt-mt6990-lg6851f/tree/a40df9a5afb46716dea799acea69f17480df4d82) | **別機種**FiberHome LG6851F向けMT6990 OpenWrtドナー | MT6990/6.18系のカーネル、DTS、PHY等の先行実装を記載。AIR6移植側も参照を明記 | 既存の[ドナー調査](OPENWRT-DONOR-SOURCE.md)が正本。別機種のイメージ/署名/DTSをAir6へ流用しない |

### 注目する相違点

1. **rinrin系**: READMEは通常のOpenWrtの `mt76` を使用し、初期状態でWi-Fiを無効化、規制適合は利用者責任と記載。開発機の**1台のみの試験**で、stockがslot Bから起動している状態での導入は未試験、両slotが起動不能な場合の復旧手段も確立していない。`Try` と `Keep` は別工程で、後者は純正slotを上書きし得る。**カリンちゃんの純正slot B維持/P44構成と安全条件が一致するとは限らない。**
2. **hchy系**: 自らREADMEで元のLG6851F/MT6990移植、OpenWrt、MediaTek等を出典として列挙する。未公開の無線管理ツール/署名材料がないため、展示画像や私有基準機での成功を公開物の再現性へ読み替えない。
3. **soralis系**: 純正OSの管理構造やモデムAPIの調査に向く。アップストリームの許諾・各ファイルのライセンス、デバイス固有情報・バイナリの扱いは取り込み前に精査する。
4. **脆弱性資料**: 11月20日付JVN更新は認証不要という評価を記載するが、このPoCの作者がJVN届出者か、修正差分の正確な実装位置は未確認。セキュリティ修正/stock root取得と、独立したOpenWrt/Debian移植とは区別する。

## 2. Forkの広がり（独立実装数ではない）

| 親リポジトリ | GitHub表示Fork数（調査時） |
| --- | ---: |
| hchyhchyxh/openwrt-air6 | 33 |
| hchyhchyxh/air6-modem | 34 |
| soralis0912/luci-app-sbair-modem | 11 |
| soralis0912/SBA6D-OSS | 7 |
| rinrin-aismirin/sbair6-openwrt-builder | 6 |
| 13179415360/openwrt-mt6990-lg6851f（別機種） | 16 |
| **単純合計** | **107** |

この107は**各リポジトリで表示されたFork数の合計**であり、ユニークな開発者数や独立した移植成功数ではない。Forkには未変更・空・実験中のものがある。

- `dotoroi/luci-app-sbair-modem` は `Floop3/luci-app-sbair-modem` を親に持つFork（soralis系の派生）。
- `Kounenri/sbair6-openwrt` は `rinrin-aismirin/openwrt` のFork。
- `fun200/openwrt-SoftBankAir6` は `hchyhchyxh/openwrt-air6` のFork。
- `ERDF59/sbair6-openwrt-builder` は `rinrin-aismirin/sbair6-openwrt-builder` のFork。
- `baiyunquan/openwrt-terminal-6` 等は別のFork系統。**同じ名前やForkがあることは、その中身の実機検証を意味しない。**

## 3. このプロジェクトでの調査優先順位

| 優先 | 調査対象 | 確認すべき具体的なゲート |
| --- | --- | --- |
| 高 | rinrin系 MLO/Wi-Fi | 対応OpenWrtコミット、mt76/wpad/hostapd差分、2帯域同時接続の証拠、技適・国別regdbの適用条件 |
| 高 | rinrin系 A/B復旧 | slot操作の書込み対象、失敗時タイマー/ブート回数、stock B保持、P43/P44使用の有無、個体差 |
| 高 | hchy系のカーネル/DTS/無線 | コードの出自、配布可否、公開物だけでビルドできる範囲、既存MT6990ドナーとの差分 |
| 中 | soralis系モデムUI | `adb_atci_socket` の仕様、AT通信の責任分界、stock依存と新カーネルへの移植条件 |
| 中 | hchy系P54メタデータ | 自己検証スクリプト、署名/実機試験の未達、RF・規制・CAの制約 |
| 参考 | 公開RCE PoC | 修正/影響条件の文献的追跡のみ。本体の移植ビルドと混同しない |

**採用判断の共通条件:** 先行実装が存在することと、安全かつ合法に本プロジェクトへ取り込めることは別。上流URLと**固定コミット**、変更単位、SPDX/ライセンス、独立テスト、再現性、実機の復旧条件を確認する。未検証の成功報告は「作者の報告」と明記する。署名鍵、校正情報、固有識別子、バイナリを公開リポジトリに取り込まない。

## 4. 発見範囲の限界と次回調査

- 検索順位・インデックス更新・検索最大件数に制約がある。「すべてのリポジトリを発見した」とは主張しない。
- 参照先で言及される `soralis0912/sbair6-rs` は調査時にGitHub APIで404となり、内容を読めなかった。削除/非公開/改名のいずれかは未確認。
- 新しいForkやブランチ、readme中の関連リンク、非GitHubの公開ソースは別途追加調査が必要。
- 調査は**2026-11-21のソース・メタデータ確認のみ**。第三者の公開版ファームウェアの再現ビルド、起動、通信、MLO試験は未実施。

---
関連する本プロジェクト内資料: [ドナーソースの権利と互換性](OPENWRT-DONOR-SOURCE.md)、[出自と証拠の境界](PROVENANCE.md)、[主開発方針](MAINLINE-P25-P26-POLICY.md)、[技術状況](STATUS.md)。
