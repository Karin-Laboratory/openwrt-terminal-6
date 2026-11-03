# Alpha 3 Developer Preview Wave 2 / 告知下書き（未投稿）

**Draft for owner approval · 2026-11-03. NOT PUBLISHED to note or X.**  
For every technical claim, use the [single current status page](ALPHA3-DEVELOPER-PREVIEW-STATUS.md), not this marketing text. Link contributors to the [bilingual entry kit](ALPHA3-CONTRIBUTOR-START.md). Do not attach binaries, firmware links, private evidence or installer instructions.

## 1. Short GitHub announcement / GitHub向け説明

**Alpha 3 Developer Preview, Wave 2: help make SoftBank Air Terminal 6 (MT6990) OpenWrt support reproducible.** We share source, bounded evidence, public CI and three safe participation tracks: review code, improve isolated QEMU/CI, or contribute redacted hardware observations. Historical B-device networking results, private C offline checks, public QEMU and C hardware boot are separate evidence levels. **Alpha 3 RC1 is not a flashable release, and authentic C Linux/procd boot is not verified.**

Start: [status](ALPHA3-DEVELOPER-PREVIEW-STATUS.md) · [contribute](ALPHA3-CONTRIBUTOR-START.md) · [discussion](https://github.com/Karin-Laboratory/openwrt-terminal-6/discussions/50).

## 2. note向け日本語告知原稿（下書き）

### Airターミナル6のOpenWrt移植、いよいよ「参加できる開発」へ。Alpha 3 Developer Preview 第2波

カリンちゃんが進めているSoftBank Airターミナル6へのOpenWrt移植は、実機での実験を積み重ねながら、公開ソースを使って誰でも検証や改善に参加できる開発へ進んでいます。今回のAlpha 3 Developer Preview第2波では、成果を大きく見せることよりも、「いま何が確認できて、どこに協力できるか」を分かりやすくすることにしました。ファームウェアの配布発表ではなく、開発の入口を公開するお知らせです。

過去の開発機では、Linux 6.18.44の起動、有線LAN、SSH、2.4GHz・5GHz Wi-Fi、そしてLTE IPv4通信まで確認した実績があります。一方、新しい真正C号機のAlpha 3 RC1でLinux起動が成功したわけではありません。別の環境で確認したことや、QEMUのテストに通ったことを、実機で全部動いたという話に混ぜないようにしています。

公開リポジトリでは、Linux・Device Tree・OpenWrt userspaceを整え、QEMUでprocdやnetifdを検証する作業も進んでいます。ネットワークの実機再現、SGMII1やNETSYS、Wi-Fiのビルド統合など、未解決の課題もまだたくさんあります。ここからは「一人で全部完成させる」だけではなく、気になる部分を誰かが見つけて直せる形にしていきたいのです。

参加方法は三つあります。実機がなくても公開ソースのレビューはできますし、QEMUやCIのテスト改善ならハードウェア不要です。機材を持っている方は、秘密情報を伏せた既存の観察結果を共有するだけでも手がかりになります。初心者の方なら、ドキュメントのリンクや手順の分かりにくさを指摘するところからで十分です。

現段階はあくまで**Developer Preview、ソースのみ**。一般の方が書き込める完成ファームウェアや安全なインストール方法は公開していません。完成していないからこそ、技術的な根拠を区別しながら、協力者が迷わず参加できる場所を用意してみました。

公開リポジトリ：[openwrt-terminal-6](https://github.com/Karin-Laboratory/openwrt-terminal-6)  
[現在の技術状態](ALPHA3-DEVELOPER-PREVIEW-STATUS.md)（GitHub内）／[参加ガイド](ALPHA3-CONTRIBUTOR-START.md)（日英対応）  
[Discussions #50](https://github.com/Karin-Laboratory/openwrt-terminal-6/discussions/50)（相談・関心表明。配布保証ではありません）

## 3. X向け短い日本語告知（未投稿）

Airターミナル6へのOpenWrt移植、Alpha 3 Developer Preview第2波を準備しました。歴史的な実機成果と、公開ソース/QEMUの進捗を分けて整理。レビュー・CI・安全な情報共有で協力者募集中です。**source-only、一般向けflashable版ではありません。** https://github.com/Karin-Laboratory/openwrt-terminal-6

## 4. English outreach / 海外開発者向け

**SoftBank Air Terminal 6 / MT6990 OpenWrt: Alpha 3 Developer Preview, Wave 2.**

We're turning a collection of hardware research results into a more approachable, source-only collaboration. The public repository contains reviewable Device Tree and kernel work, build contracts, userspace research, and isolated QEMU tests. Historical B-device Linux/LAN/Wi-Fi and LTE IPv4 experiments are valuable but **do not prove that the new authentic C-unit Alpha 3 RC1 boots Linux**.

Three ways to help now: **(A)** review public DTS/kernel/userspace/build scripts, **(B)** reproduce or improve safe QEMU/CI tests without hardware, or **(C)** share previously captured, carefully redacted hardware observations. You do not need an unlocked unit, a signing key, a firmware download or an installation procedure.

[Project](https://github.com/Karin-Laboratory/openwrt-terminal-6) · [Evidence status](ALPHA3-DEVELOPER-PREVIEW-STATUS.md) · [Contributor guide](ALPHA3-CONTRIBUTOR-START.md) · [Discussion #50](https://github.com/Karin-Laboratory/openwrt-terminal-6/discussions/50). Independent community research, not an official vendor release. **Source-only, no flashable binary.**

## 5. Existing collaborators / 既存協力者への技術アップデート文案

### 日本語（DM/コメント向け、一人称は「私」）

いつも情報交換ありがとうございます。私のAirターミナル6 OpenWrt移植は、Alpha 3をsource-onlyのDeveloper Previewとして公開し、外部の開発者が参加できる入口を整えています。過去の実機で確認したLinux・Wi-Fi・LTE IPv4の成果と、現在の公開QEMU/CIの成果は分けて整理しました。真正C号機のAlpha 3 RC1はまだLinux起動成功を確認できていませんが、公開DTS・SGMII1/NETSYS・userspace・テストのレビューに関心があれば、ぜひご意見をいただけるとうれしいです。実機操作や機密ファイルの共有をお願いするものではありません。 https://github.com/Karin-Laboratory/openwrt-terminal-6

### English

Thank you for the previous technical discussions and contributions. I'm preparing Wave 2 of the Air Terminal 6 Alpha 3 Developer Preview as a **source-only** contributor entry point. Public DTS, MT6990 Ethernet/SGMII1, native OpenWrt userspace and QEMU/CI are particularly welcome review areas. Historical device results are separated from current C-device validation; we do **not** yet claim successful authentic C-unit Alpha 3 RC1 Linux boot. Feedback or narrowly scoped source/CI contributions would be appreciated, without requiring device modifications or sharing non-public materials. https://github.com/Karin-Laboratory/openwrt-terminal-6

---

**Owner publication checklist:** replace GitHub-relative Markdown links with absolute public URLs when posting to note/X; verify no stale test claim, no linked private root/flash/keys, preserve attribution/licensing, and obtain explicit publication approval. Do not auto-post, tag third parties, upload firmware or create a Release.
