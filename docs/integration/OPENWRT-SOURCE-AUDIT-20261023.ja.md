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

上記に対し、OpenWrtの準備済み6.18.55ソースからRFC #2を手作業で再生成し、次を加えた。

- `mtk_probe()`の実際の失敗goto/label構成に合わせてrebaseし、登録済みnetdevを追跡する。
- OpenWrtが追加した`mtk_mac_config()`の第三producerを、同じ停止フラグとspinlockを使う`mtk_queue_reset_work()`へ集約する。
- `scripts/apply-openwrt-prepared-rfc-series.sh`でC/headerの両方が上記blob IDに一致する場合だけRFC #1とOpenWrt向けRFC #2を順番に適用する。
- 3 producerの静的検査と、追加producerを検出するunit testを追加する。

2026-10-23のローカル準備済みツリーでsource fingerprint、fuzzなしpatch dry-run/apply、`check_mediatek_rfc_series.py`はPASSした。これはsource patchの適用と静的検査であり、まだCコンパイルや実行時安全性の証明ではない。新しいGitHub workflowも同じOpenWrt commitで準備・適用・静的監査を行う。

## ビルド状況

- `make defconfig`: 成功。既定プロファイルは`openwrt_one`。
- `make target/linux/prepare`: 成功。OpenWrtの6.18.55パッチ群を適用。
- 初回`make target/linux/compile`: OpenWrtクロスコンパイラ未生成で失敗。エラーは`aarch64-openwrt-linux-musl-gcc: No such file or directory`。
- `make tools/install toolchain/install`: 現在構築中。完了後に通常のFilogic参照カーネル/rootfsビルドを再試行する。

参照ターゲットのビルド成功をSBAT6DのSoC対応、ボードDTS、無線・Ethernet動作、起動可能なSBAT6Dイメージと混同しない。

## SBAT6D統合を保留する根拠

公開確認できるMAC1/SGMII1/MT7531の測定値だけでは、完全な起動用DTSに必要なSoCノード、clock/reset/power-domain ID、pinctrl、regulator、PHY/PCS参照を確定できない。MT6990用のOpenWrt subtarget、kernel config、起動・rootfsイメージ定義もこの公開ソースには存在しない。現時点で仮のphandleや電源IDを埋めたDTSまたは実機イメージ定義を追加しない。

次の必須入力は、再配布可能性を確認した同一実機のruntime FDTノード依存関係と、OpenWrt用に利用可能なMT6990 SoC/kernel supportのライセンス監査済みソースである。
