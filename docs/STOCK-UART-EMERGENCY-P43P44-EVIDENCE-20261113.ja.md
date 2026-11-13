# Air Terminal 6: UART / LK / 純正Linux / P43・P44 実測知見（2026-11-13）

> **目的:** 初見の所有者と、その所有者が選んだAIエージェントが、同じ調査を何度もやり直さなくて済むようにする。これは**動作保証や完成インストーラではない**。対象は所有・管理の正当な権限がある個体に限る。

## 0. 対象と情報の信頼度

対象は SoftBank Air Terminal 6（開発資料上 SBA6D）。非公開研究における複数の所有実機（A:純正基準、B:OpenWrt試験、C:OpenWrt/Debian試験）のうち、**個別の観測とQEMU実験から再利用できる部分のみ**を匿名化して記録した。

- **CONFIRMED_ON_UNIT**: 少なくとも記載の実機で直接観測。
- **CONFIRMED_IN_SIMULATION**: QEMU等でのみ確認。
- **EXPECTED_COMMON**: 同系統機で共通と思われるが全3台・全ファームウェアでの一致は確認していない。
- **NOT_VERIFIED**: 成功と主張しない。

**3台すべてで同一ファームウェア・同一GPT・同一SSH状態を測ったわけではない。** 仕様が一致するはずだという推測を、配布先の個体での検査の代わりにしないこと。

## 1. コンソールと権限は別の軸

| 見えているもの | 何か | どう識別するか | 注意 |
|---|---|---|---|
| `]` | LK Debug Console（bootloader） | 起動ログとLKのプロンプト | Linuxでも「LK root shell」でもない |
| `/ #` + PID1=`sh` | Stock Linux Emergency Shell（`init=/bin/sh`） | `uname -m`, `cat /proc/cmdline`, `cat /proc/1/comm` | 通常サービスの起動を期待しない |
| `#` 等 + PID1=`procd` | 純正通常起動のroot shell | カーネルと起動状態の組合せを確認 | SSH接続＝必ずroot権限、ではない |
| `/ #` | OpenWrt root shell | cmdline、PID1、/etc/os-releaseなどを複合確認 | プロンプトが同じでも環境は違う |

接続媒体 **UART / SSH** と権限 **root / 非root** は別概念。LK上でLinux用コマンドを試さない。Linux上では最初に現在のslotとPID1を確認する。

### 読み取り専用の最初の確認例（Linuxシェルでのみ実行）

```sh
uname -m
uname -r
cat /proc/cmdline
cat /proc/1/comm
cat /proc/mounts
ls /sys/class/block
```

機器識別文字列、シリアル番号、MAC、加入者データ、認証情報等を外部に共有する際はマスクする。

## 2. 物理UARTの共通知見

- 実測・既存開発経路の接続設定: **115200bps / 8 data / parity none / 1 stop / flow control none**。WindowsはTera Term、Linuxはpicocomなどで接続可能。
- 物理信号は**3.3V TTL**として扱い、RX/TX/GNDの結線は各個体の表示・配線を確認。USB-RS232の電圧や5V/VCCを直接接続しない。
- 起動時のCtrl+CがLK入力を止める契機になった**観測例**がある。割り込み可能なタイミング・ファームウェア差があるため、全個体で成功を保証しない。
- Tera Term/picocomと自動転送スクリプトで同じCOM/ttyを同時に開かない。UARTログ取得者を1つにする。
- UARTは小型RAM工具を搬入する経路にはなるが、P43全量約2.9GiBを送る経路としては不向き。P43の縮小処理は、適切なツールと条件で**端末内のeMMC上**で行う設計。

この資料は、非公開の認証情報、署名鍵、未公開の侵入経路や任意コード実行の詳細を転載するものではない。

## 3. 純正Linuxの実測環境

- **CONFIRMED_ON_UNIT**: 純正slot Bで Linux **5.4.238** / **AArch64** が観測された。
- **CONFIRMED_ON_UNIT**: `init=/bin/sh` で起動したEmergency ShellはPID1が`sh`、純正rootfsは読み取り専用squashfsとして観測。通常サービスは自動起動しない。
- **CONFIRMED_ON_UNIT**: このEmergency Shellで `devtmpfs` が使えない一方、`tmpfs` と `mknod` の使用が観測された。RAM上の `/tmp` や `/dev` を準備する際は、既存ファイルを隠す再マウントを避ける。
- **CONFIRMED_ON_UNIT**: 通常起動した純正slot BではPID1=`procd`、LANのARP/pingと**公開鍵によるroot SSH**の実測がある。
- **NOT_VERIFIED**: 初期状態の任意の中古機で、上記のSSHが最初から開いていること。Emergency Shellからの一時SSH開通、純正SSH永続化の一般化された導入手順。
- **CONFIRMED_ON_UNIT / LIMITATION**: 一部B号機で純正OSの無線health監視が再起動を要求する現象を観測。通常起動後の再起動を直ちにLinux panic、OpenWrt側異常、あるいはSSH設定不備と断定しない。設定変更の個別例を初見機に一括適用しない。

**SSHの2段階の判定**:
1. 現在のブートでLAN→認証済みSSH→リモートコマンド実行まで確認したか。
2. 電源再投入または正常再起動後、同じ純正slot Bでホスト鍵・接続方式・認証状態が保持されたか。

1のみで「永続化PASS」としない。既存のroot SSHが別の開発機で動いた事実を、新規個体の認証手順として転用しない。

## 4. eMMC / GPT / P43・P44

- **CONFIRMED_ON_UNIT**: 開発機のP43はext4データ領域として観測。純正起動状態によってはマウントされるため、縮小前にはmount状態とext4/journal整合性を検査する。
- **CONFIRMED_ON_UNIT**: 分割後の実測例はP43 GPT約**453MiB**、その中のext4約**440MiB**、P44約**2.5GiB**（rootfs_data）。**パーティションのサイズとファイルシステムのサイズは異なる**。
- **EXPECTED_COMMON**: `p43` と `p44` の番号・役割は対象系統で参考になる。ただし /dev/mmcblk0 と /dev/mmcblk1 のどちらになるか、GUID、開始LBA、末尾、パーティション名は**現物から取得**し、固定文字列の流用を禁止。
- **CONFIRMED_IN_SIMULATION**: QEMUでP43約2.94GiBからext4を440MiBへ縮小し、P43 GPTを約453MiBに変更、P44を新規ext4化。200MiB試験データのSHA一致、工程境界での停止と再開を確認。
- **NOT_VERIFIED**: 未分割の第三者実機での同工程の成功、データ完全保持、電源断復旧。QEMU固定の /dev/vda・GUID・LBAを実機へ適用してはならない。
- **CONFIRMED_ON_UNIT / LIMITATION**: 分割済み機体のP43に `e2fsck -fn` が不整合を報告した事例があり、journal未再生など原因を確定していない。読み取り専用検査の非ゼロ終了を無視して自動修復・縮小してはならない。

### 保全と検証の原則

1. `/proc/cmdline` と`/sys/class/block`等で**今のブート・対象eMMC・対象P43**を同定。
2. P43が未マウントで、バックアップと復旧経路が確認できるまでは変更しない。
3. ext4縮小を先に完了・検査したうえで、GPT上のP43終端を変更する。**GPTだけ先に短くしない**。
4. P44が既に存在したら新設処理を繰り返さない。対象のデータ消去・書込み範囲を事前に明示する。
5. GPT両ヘッダとCRC、P43の整合性・保持データ、P44のext4、純正slot Bでの起動を独立に再確認する。
6. 所有者の承認は、対象個体、対象領域、バックアップ、復旧方法、予測される損失を示した後に受ける。

## 5. 開発キットの既知の限界

**2026-11-13時点の非公開開発証拠（公開向けに要約）**:

- v0.3: QEMU用P43/P44分割実験は成功。**実機インストーラではない**。
- v0.4 r3: Stock Emergency Shell用RAM搬送・AArch64工具の候補。疑似UARTでの搬送等は検査済み。**実UART一気通貫は未検証**。
- v0.4 r4研究案: Windows COM搬送・未分割P43の読み取り専用検査を追加したが、未分割実機の分割手順は未完成。
- **書込み適用は未完成**。既存研究コードの `installer.sh --apply` は拒否する。文書を公開しても機能が解禁されるわけではない。

この公開資料には、再配布権限が未確定のOEMファームウェア、秘密鍵、署名済みイメージ、純正パーティションダンプ、個体固有の校正情報、認証情報、未公開の脆弱性・侵入経路の再現手順を含めない。

## 6. 次に調べる人・AIエージェントへの引き継ぎ

- OpenWrt用とDebian用の起動ファームウェアを**この調査工程では書き込まない**。今回の共通入口の目標は「純正環境のSSH永続化が実機で確認でき、P43/P44分割が完了した状態」。
- まず本書を読んで**既知の実測を再利用**する。足りない事実だけを所有機で読み取り専用で調べる。
- 調査のたびに `observed` / `inferred` / `not_tested` を別欄で記録する。別個体のオフセット・MAC・固定IPを無断で流用しない。
- 出力ログにシリアル・秘密鍵・ホスト鍵・SSID/PSK・SIM識別子・校正データが含まれる可能性があるため、原本は本人のローカル環境に保存。公開Issueには匿名化した結果のみ投稿。
- 一時SSHと永続SSH、読み取り専用監査PASSと実機パーティション分割PASSを別ゲートにする。未達の場合は「未確認」と報告し、完了と宣言しない。

関連する公開資料: [技術状況](STATUS.md)、[GNSSの匿名化事例](GNSS-RESEARCH-20261112.ja.md)、[公開・再配布ゲート](RELEASE-GATES.md)。

---

**出典の性格:** 所有者の非公開研究記録から、共有可能な機能・環境・失敗条件のみを人手で要約したもの。全3台の逐一照合表ではない。記載した観測値は他人の機体で自動使用する設定値ではない。
