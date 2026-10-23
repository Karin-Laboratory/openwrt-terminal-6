# MediaTek Ethernet RFC第2弾：reset work再投入と終了処理の直列化

状態: **ソースRFC。v6.18への順次適用、静的検査、3段階ARM64 object buildはGitHub ActionsでPASS。実機未検証。**

対象はLinux `torvalds/linux` tag `v6.18`の次の公開ファイルである。

| ファイル | Git blob ID |
|---|---|
| `drivers/net/ethernet/mediatek/mtk_eth_soc.c` | `e68997a29191b2a8ce0868873dcfe95c79e10e56` |
| `drivers/net/ethernet/mediatek/mtk_eth_soc.h` | `0168e2fbc6197a6aa9fe159767166e86915accbc` |

RFC第2弾は[`0001` cleanup ordering](../patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch)の後に適用する差分である。今回、元ソースへ直接変更を加えて`git diff`で再生成し、hunk contextを含む通常のGit patch形式に直した。

## 変更内容

- `mtk_tx_timeout()`とDMA monitor callbackの両方からの`pending_work`投入を、同じ`reset_queue_lock`配下へ集約する。
- timeout callbackによるreset-status MMIO readも停止宣言と直列化する。送信watchdogはTX queue lockを保持してcallbackを呼ぶため、この状態lockは短時間だけ取り、RTNL取得・同期cancel・sleepは行わない。
- monitor delayed work自身の再予約も同じlockと`reset_queue_stopping` latchで保護する。
- removeとprobe unwindはlock下でlatchを立て、lockを解放してから`cancel_work_sync()`、`cancel_delayed_work_sync()`を呼ぶ。
- removeではworkをdrainしてからnetdev停止、WED終了、hardware deinitへ進む。
- probe unwindではreset資源解放前にworkをdrainする。登録済みnetdevだけをunregisterするため、登録途中の失敗と成功済みnetdevを区別するlocal bitmapを使う。
- `reset_queue_lock`とstop latchをprobe時に初期化する。driver dataは`devm_kzalloc`で割当て、monitor workとpending workはproducerを公開する前に初期化される。

## 競合とlock順序のレビュー

1. producerは`reset_queue_lock`取得中にstop latchを確認してqueueする。stop側も同じlock内でlatchを設定するため、stop宣言より後のpending work投入・monitor再予約は通らない。
2. stop側はspinlockを解放してから同期cancelする。cancel中にcallbackが同じlockを取る必要があっても循環待ちにならない。
3. pending reset workerは`rtnl_lock()`を取る。stop helperはRTNLを保持せずに同期cancelするため、worker完了を待てる。その後にprobe unwindの`unregister_netdev()`がRTNLを使う。
4. v6.18のnetdev watchdogは`tx_global_lock`を保持したまま`ndo_tx_timeout`を呼ぶ。timeoutはその内側で状態lockを短時間取得する。reset workerは状態lockを持たずにRTNLを取得し、stop helperも状態lockを解放してからcancelするため逆順取得はない。通常のplatform removeはdevice lock経由でRTNLを保持しないが、別の呼出し元からRTNLを保持してremoveへ入る構成は許容できず、対象kernelごとに確認が必要である。
5. monitor callbackがMMIOチェック中にstop宣言されても、`cancel_delayed_work_sync()`がcallback完了を待つためhardware teardownより後へ越境しない。timeout callbackの短いMMIO readは同じ状態lockに含め、stop宣言がread完了を待つ。

参照したLinux v6.18実装は[`mtk_tx_timeout()`とmonitor workを含むdriver source](https://github.com/torvalds/linux/blob/v6.18/drivers/net/ethernet/mediatek/mtk_eth_soc.c)、[driver core detach経路](https://github.com/torvalds/linux/blob/v6.18/drivers/base/dd.c)、[netdev watchdog callback呼出し](https://github.com/torvalds/linux/blob/v6.18/net/sched/sch_generic.c)である。

## 残る安全性の制約

- これはwork producerと同期停止の競合に限定したsource RFCであり、全netdev操作とdriver removeの完全なlifetime証明ではない。
- `mtk_remove()`が呼ばれる全経路でRTNLを保持していないことを、適用先kernel・vendor backportごとに確認する必要がある。
- reset workerがremove開始前に取得した各SoCのhardware resource/clockがworker完了まで有効であることは、コードコンパイルだけでは証明されない。
- `cancel_work_sync()`が待つ間にworker自身がnetdev操作を行うため、RTNL/close/resetの全経路はlockdepと実機または適切なfault-injectionで追加検証が必要。
- 他SoCへの影響はコンパイルとsource reviewでのみ評価している。hardware remove、watchdog timeout、probe partial failureの実機試験は未実施。
- RFC第1弾cleanup内には同期cancelが残る。第2弾のremove先頭stopで既にdrainした後の重複cancelとなるが、cleanupの独立な防御を残す目的で削除していない。
- コンパイル成功は実機Ethernet動作、安全なhot-unplug、MT6990対応完了を意味しない。

## 再現検証

[`tools/check_mediatek_rfc_series.py`](../tools/check_mediatek_rfc_series.py)は2パッチを実ソースへ適用した後、producer/stop順序、probe unwindのdrain位置、header状態を静的に検査する。GitHub Actionsはupstream source/header blob IDを検査し、`0001`→`0002`の順にapplyする。ARM64 workflowは同じ`.config`でbaseline、RFC1のみ、RFC1+RFC2の`mtk_eth_soc.o`を順にコンパイルし、各object SHA-256をsummaryへ出す。

### GitHub Actions結果（2026-10-23）

| 検証 | 結果 | 実行 |
|---|---|---|
| upstream v6.18 C/header blob照合、RFC1→RFC2順次適用、静的検査 | PASS | [RFC MediaTek patch apply check](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158897) |
| Public source checks | PASS | [run](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158855) |
| Publication safety gate | PASS | [run](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158860) |
| ARM64 baseline/RFC1/RFC1+RFC2 object compile | PASS | [RFC MediaTek kernel object compile](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158871) |

ビルドはLinux `v6.18`、`ARCH=arm64`、`CONFIG_COMPILE_TEST=y`、`CONFIG_NET_MEDIATEK_SOC=m`で同じ`.config`を使い、対象`mtk_eth_soc.o`を各段階で再生成した。結果のobject SHA-256:

| 状態 | `mtk_eth_soc.o` SHA-256 |
|---|---|
| upstream baseline | `a6dc88aed0f0dbb542a8e6a494135c1f9af69357cf1dff97d54113e78718288c` |
| RFC 0001 | `a9e9cda3fe5c235998d4cb9bdbd46474bff40aa0c5e8ca2229676f1dd781a0e5` |
| RFC 0001 + RFC 0002 | `01a28c7a14744f3993206eec3482c3aa24f3284ab1217445674b7152d2dd6bb1` |

この結果はdriver objectのARM64 compile成功を示す。kernel全体のbuild、実機起動、remove時のhot-unplug、watchdog発火、fault-injection、lockdepは検証しておらず、RFCの実行時安全性やMT6990対応を証明しない。
