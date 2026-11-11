# Air Terminal 6 内蔵GNSSの調査結果（2026-11-12）

> **公開用の観測事実と未確認事項の整理。** 対象は所有者管理下のSoftBank Air Terminal 6（開発識別名「B号機」）の**純正OS（stock slot B）**。**OpenWrt上でGNSSが動作したという報告ではない。** GNSSファームウェア、校正情報、位置座標、生ログ、純正ELF等は公開しない。

**English summary:** On an Air Terminal 6 running its stock OS, an internal-GNSS 3D position fix and navigation-message delivery were observed. Two captures (60 seconds and five minutes) yielded **4,609 navigation-message events** for GPS, GLONASS, BeiDou and Galileo, but **zero SBAS/SBS-type events**. QZSS L1Sb/SBAS tracking and L1S disaster-message reception remain **unverified**, not demonstrated unsupported. This is not an OpenWrt GNSS implementation or install guide.

## 1. 調査範囲と証拠レベル

目的はAir Terminal 6の**内蔵GNSS**による測位・航法データ取得と、「みちびき」のSBAS補強信号（L1Sb）および災害・危機管理通報（L1S）への対応可能性を調べること。外付け受信機は対象外。

- **実機確認:** 純正OSで測位結果や航法メッセージ配送を観測したこと。
- **静的解析:** GNSS関連プログラムに処理経路やAPIが存在すること。信号の実受信とは別。
- **オフライン検証:** 公開L1Sアーカイブの解読・CRC検証。端末による受信ではない。
- **UNKNOWN / 未確認:** 調査範囲で直接証拠を得られなかった状態。**非対応・受信不能という意味ではない。**

## 2. 純正OSでの3D測位

純正Linux 5.4.238でGNSS関連サービスが稼働し、測位キャッシュの複数回更新を確認した。キャッシュの測位フラグは`0x7ff`、同時期のログに`fix_mode:3`が存在し、3D測位が成立した。別のUCI状態欄は0のままだったため、測位キャッシュの実更新を重視した。

位置の自己申告精度は独立した実測誤差検証ではない。公開資料には座標、個体情報、測位時刻列を含めない。

## 3. 実機navigation message購読・取得

純正GNSSサービスの既存メッセージ配送経路を確認し、別の短時間クライアントへの**navigation message**配送を実機で観測した。航法メッセージは衛星の時刻・軌道等の測位用デジタル情報を含む。**4,609は配送イベント件数**であり、異なる4,609衛星・独立した4,609電文を意味しない。再配送や重複の有無も未評価。

| Android navigation-message type | 系統・信号 | 60秒 | 5分 | 合計 |
| --- | --- | ---: | ---: | ---: |
| `0x0101` | GPS L1 C/A | 73 | 338 | 411 |
| `0x0301` | GLONASS L1 C/A | 587 | 2,206 | 2,793 |
| `0x0502` | BeiDou D2 | 84 | 428 | 512 |
| `0x0601` | Galileo I/NAV | 104 | 789 | 893 |
| **`0x0201`** | **SBAS / SBS** | **0** | **0** | **0** |
| `0x0401` | QZSS L1 C/A | 0 | 0 | 0 |
| **合計** | **通常航法メッセージ** | **848** | **3,761** | **4,609** |

型の解釈は[Android公式GNSS Navigation Message定義](https://android.googlesource.com/platform/hardware/interfaces/+/2944bac9613e52768ed71e4a5585c72247b57d86/gnss/aidl/android/hardware/gnss/IGnssNavigationMessageCallback.aidl)と照合した。実受信の本文や生パケットは非公開とし、この集計のみ共有する。

試験後、既存GNSSサービスのPIDと測位キャッシュ更新、管理接続が維持された。ただし、購読解除コマンド送信の成功は、デーモン側での解除完了ACKや他の購読者への完全な無影響を保証しない。

**時計上の制約:** 端末壁時計は実時刻より約11日遅れており、端末時刻を検証済みUTC受信時刻と扱っていない。

## 4. SBAS/L1SbとL1Sは別信号

- **L1Sb（SBAS）:** 衛星航法の補強等を行う信号。調査対象はQZS03のPRN 137とQZS06のPRN 129。公式の運用表示は端末での受信を示さない。
- **L1S（災害・危機管理通報など）:** L1Sbとは別の信号。調査対象のL1S PRN例は184、185、186、189。測位用L1信号の受信成功はL1S専用のPRN捕捉・復調能力の証明ではない。
- **今回実証したもの:** GPS、GLONASS、BeiDou、Galileoの通常航法メッセージの**Linuxユーザー空間への配送**。SBAS本文またはL1Sの実受信ではない。

参照：[QZSS衛星運用情報](https://sys.qzss.go.jp/dod/constellation.html)／[L1S信号](https://qzss.go.jp/technical/system/l1s.html)／[技術仕様](https://qzss.go.jp/technical/download/ps-is-qzss.html)。

## 5. 純正ユーザー空間の静的解析

1. **SV status経路:** 衛星別SVID・衛星系統・C/N0・状態フラグを扱う内部配送処理を特定した。しかし、稼働中B号機から値を受動的に抽出する口は見つからず、PRN 137/129の捕捉・追尾は**未確認**。
2. **旧SBAS getter:** 取得APIが存在するものの、実際にバッファへ書き込むproducerや純正GNSSファームウェアとの結線は**未確認**。記録されたバッファ間隔と本文コピー長も、独立した固定長レコードとしては整合しない。推測による実機バッファ読み取りは行わなかった。
3. **SBAS別出力:** 調査したGNSS関連純正プログラムと通常ファイルの範囲では、SBAS専用の本文出力経路を**確認できなかった**。既知の通常航法メッセージ巡回はGPS、GLONASS、BeiDou、Galileoの4系統。未知のファームウェア内部経路が存在しないという証明ではない。

## 6. 公開アーカイブによるL1Sオフライン解析

2026-11-10のQZSS公開L1Sアーカイブ（1日分）を独立したオフラインデコーダで解析し、250-bit形式、プリアンブル、CRC-24Q、連続するTOWを検証した。**86,400フレーム**がCRC検証を通り、災危通報形式（MT43/MT44）等の分類をテストした。

これは**公式アーカイブのPC上での解析結果**であって、Air Terminal 6によるL1S受信ではない。災害警報用途の運用品質やメッセージ意味解釈の完全性も主張しない。

## 7. 最終判定（2026-11-12）

| 調査項目 | 結論 |
| --- | --- |
| 純正OSでの内蔵GNSS 3D測位 | **PASS（実機）** |
| 通常navigation message配送 | **PASS（実機、計4,609イベント）** |
| SBAS PRN 137/129追尾 | **UNKNOWN** |
| 旧SBAS取得APIのデータ供給元 | **UNKNOWN** |
| 別のSBAS本文出力経路 | **調査範囲内では未発見** |
| SBAS/L1Sb本文の実受信 | **NOT_OBSERVED（当該購読経路で0件）** |
| L1S災危通報の実受信・対応可否 | **UNKNOWN** |
| OpenWrt上のGNSS動作 | **本調査の検証対象外** |

**結論：内蔵GNSSによる3D測位と通常航法メッセージ取得までは実機確認済み。SBAS/L1SbおよびL1S災危通報の受信は未確認で、非対応と断定はできない。調査はここで一区切りとする。**

## 8. 共有・再開条件

追加調査に必要なのは、(a)衛星別SV statusの非干渉な観測経路でPRN 137/129を直接確認する証拠、または(b)稼働中純正GNSSファームウェアからSBAS取得APIへ至るproducerを示す確実な資料など。通常navigation購読の単なる延長だけでは十分でない。

**非公開のまま保持するもの:** 生ログ、位置、個体識別子、認証情報、固有接続経路、純正実行ファイル・ファームウェア、キャリブレーション情報。本公開資料はGNSSの有効化方法、ファームウェア配布、OpenWrt移植の完成報告ではない。
