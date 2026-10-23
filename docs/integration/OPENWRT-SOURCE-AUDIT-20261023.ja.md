# OpenWrt 6.18統合調査（2026-10-23）

## 対象と範囲

- OpenWrt公開ソース: `openwrt/openwrt` commit `a25fb079b1463cd5d7d69c6d9a1c28d873291ebb`
- ターゲット: `mediatek/filogic`（既定プロファイル `openwrt_one`）
- OpenWrtのLinux設定: `KERNEL_PATCHVER=6.18`
- `target/linux/prepare`で展開された実ソース: Linux `6.18.55`
- この検証はOpenWrt One向け参照ビルドの調査であり、SBAT6D用ファームウェアを生成・検証したものではない。

## OpenWrtとRFCのソース差

OpenWrtの準備済みカーネルに含まれるMediaTek EthernetファイルのGit blob IDは次のとおり。

| ファイル | upstream v6.18期待値 | OpenWrt準備済みソース | 結果 |
| --- | --- | --- | --- |
| `mtk_eth_soc.c` | `e68997a29191b2a8ce0868873dcfe95c79e10e56` | `680f8adf2c7402a8b041966703358e3532b347de` | different |
| `mtk_eth_soc.h` | `0168e2fbc6197a6aa9fe159767166e86915accbc` | `accf4849979e4bf57ebefa9eb5199656fbee71b7` | different |

従って、既存の厳密なupstream blob gateはOpenWrtソースに対し正しくNO-GOとなる。OpenWrtのgeneric/mediatek 6.18パッチ群が同ドライバを変更しているため、バージョン番号だけでRFCの直接適用可能性を判断できない。

## 適用試験とOpenWrt向けrebase

- RFC #1の`git apply --check`はOpenWrt準備済みツリーで通る。
- RFC #2の`git apply --check`は`mtk_eth_soc.c`のprobe cleanup付近で失敗する。
- `patch`のfuzzを許して適用すると、probe失敗経路に存在しない`err_unreg_netdev`へのgotoが残る一方、そのlabelは除去される。従ってfuzz適用結果はコンパイル可能な統合とは見なせない。
- OpenWrt側の追加変更には`mtk_mac_finish()`からの3番目の`pending_work`投入箇所がある。RFC #2のupstream版だけではこれを止めるゲートに通さない。

上記に対し、OpenWrt準備済み6.18.55ソースへRFC #1とRFC #2を適用し、適用後ソースと基準ソースの差分からRFC #2を再生成した。実コンパイルで見つかった前方宣言不足も反映した。次を加えた。

- `mtk_probe()`の実際の失敗goto/label構成に合わせてrebaseし、登録済みnetdevを追跡する。
- OpenWrtが追加した`mtk_mac_config()`の第三producerを、同じ停止フラグとspinlockを使う`mtk_queue_reset_work()`へ集約する。
- `scripts/apply-openwrt-prepared-rfc-series.sh`でC/headerの両方が上記blob IDに一致する場合だけRFC #1とOpenWrt向けRFC #2を順番に適用する。
- 3 producerの静的検査と、追加producerを検出するunit testを追加する。

2026-10-23のローカル準備済みツリーでsource fingerprint、fuzzなしpatch dry-run/apply、`check_mediatek_rfc_series.py`はPASSした。最初のCコンパイルでは、OpenWrt追加producerの行がhelper定義より前にあるため、前方宣言がなく暗黙宣言エラーとなった。helperのstatic prototypeをファイル先頭に追加して差分を再生成し、fuzzなし再適用、静的検査、全51 unit testを再実行してPASSした。新しいGitHub workflowも同じOpenWrt commitで準備・適用・静的監査を行い、修正後commit `2cff1381af4df045e3f3896f50de41a274f4d691`でPASSした。

## ビルド状況

- `make defconfig`: 成功。既定プロファイルは`openwrt_one`。
- `make target/linux/prepare`: 成功。OpenWrtの6.18.55パッチ群を適用。
- 初回`make target/linux/compile`: クロスコンパイラ未生成で失敗。`make toolchain/install`でAArch64 GCC 14.4.0などを構築した。
- 最初の実コンパイルはRFC2の前方宣言不足を発見したため失敗。修正後、`make -j2 target/linux/compile V=s`は成功し、ARM64 `Image`、Filogic DTB群、modulesを生成。`.config`の`CONFIG_NET_MEDIATEK_SOC=y`で、`mtk_eth_soc.o`のコンパイルとvmlinuxリンクを確認した。
- `make -j2 package/compile V=s`: 成功。既定のOpenWrt One profileで選択された依存・パッケージ群をビルド。`make -j2 package/install V=s`: 133パッケージをrootfs stagingへインストール。
- `make -j2 target/install V=s`: 成功。OpenWrt One向けinitramfs ITBとsquashfs sysupgrade ITB、factory artifactsおよびmanifestを生成した。
- 代表成果物（ローカルのみ、GitHubへは未upload）:
  - `Image`: 15 MiB、SHA-256 `41499c23286cca81f55ef25d37617c9eb1e804fb02c3a81565f3024250e773e6`
  - `mtk_eth_soc.o`: 608 KiB、SHA-256 `98b6cf4538a0970e2860e8088d56e6b6b77c2a88cc90bbd8434fd987b42db3cd`
  - OpenWrt One `initramfs.itb`: 9 MiB、SHA-256 `322a19ac0e3dfaf07a585d7b027757d9ffd768a9983a9dd8b807a30d1400e21f`
  - OpenWrt One `squashfs-sysupgrade.itb`: 11 MiB、SHA-256 `5345178d261d9b877f3df5ddf88805e4f88b3dea88ecb4b30552b45da582617a`
- Disk free after build: approximately 11 GiB. Compile emitted upstream modpost `MODULE_DESCRIPTION()` warnings, but completed with exit status 0.

参照ターゲットのビルド成功をSBAT6DのSoC対応、ボードDTS、無線・Ethernet動作、起動可能なSBAT6Dイメージと混同しない。

## SBAT6D統合を保留する根拠

公開確認できるMAC1/SGMII1/MT7531の測定値だけでは、完全な起動用DTSに必要なSoCノード、clock/reset/power-domain ID、pinctrl、regulator、PHY/PCS参照を確定できない。MT6990用のOpenWrt subtarget、kernel config、起動・rootfsイメージ定義もこの公開ソースには存在しない。現時点で仮のphandleや電源IDを埋めたDTSまたは実機イメージ定義を追加しない。

次の必須入力は、再配布可能性を確認した同一実機のruntime FDTノード依存関係と、OpenWrt用に利用可能なMT6990 SoC/kernel supportのライセンス監査済みソースである。
