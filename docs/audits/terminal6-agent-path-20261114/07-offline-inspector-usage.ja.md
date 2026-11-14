# P43/P44未分割個体向けオフライン証拠判定

`tools/qa/p43_unsplit_offline.py` は、**所有者がローカルで収集・匿名化したJSONのみ**を評価する準備段階の道具です。GPTを自力で読み出す工具でも、実機を直接検査する工具でも、分割インストーラでもありません。

## ホスト側の利用

```sh
python3 tools/qa/p43_unsplit_offline.py --input docs/audits/terminal6-agent-path-20261114/p43-synthetic.example.json
```

付属例は合成データであり、評価結果は`SIMULATED_ONLY`のためBLOCKEDです。実際のeMMCのデバイス番号、GUID、LBA、容量、縮小先などには絶対にコピーしないでください。

入力はdisk_sectors、logical_sector_bytes、GPT primary/backupの独立検証結果、P43のGPT start/end、ext4総/使用/最小ブロック数、journalの状態、mountの有無、P44有無、バックアップ・復旧検証、必要時のSSH保存先依存性を表します。値を得る工程も個体別に安全性と権限を確認する必要があります。真偽が分からない場合はtrueを入れず、値を未記入にしてBLOCKEDにしてください。

`INSPECT_ONLY_NO_DEVICE_PASS` は入力の自己整合に明らかな問題がないという意味に過ぎません。**S06、S07、S08の実機PASSは意味しません**。ツールはデバイスアクセス、shell実行、fsck、resize、GPT変更、再起動を行いません。

対象S03のLK移行は別途所有者の承認とファームウェア別の独立検証が必要です。生bootctrl値・固定アドレス・秘密情報を記載しないでください。

**更新:** `ssh_state_on_p43` は必須の真偽値で、情報が不明なら**キー欠落のままBLOCKED**にする。`last_usable_lba` は一次・二次GPTから確認した最終使用可能LBAであり、P43がそこを越える入力は拒否する。これらの値を適当に補完してはいけない。検査器が受け付ける値は証跡の正しさを保証せず、実機の読取り専用採取処理は別途必要。
